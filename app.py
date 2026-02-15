import streamlit as st
import anthropic
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import time
from urllib.parse import urljoin, urlparse

# Import our new modules
from gsc_fetcher import GSCFetcher
from ga4_fetcher import GA4Fetcher
from email_sender import EmailSender

load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=api_key)

st.set_page_config(page_title="AI SEO Audit Tool", page_icon="🔍", layout="wide")

# Service account email for instructions
SERVICE_ACCOUNT_EMAIL = st.secrets["gcp_service_account"]["client_email"]

def save_to_sheets(name, email, company, url, gsc_property, ga4_property_id):
    """Save lead data to Google Sheets"""
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key('1eilZ_xDiOukzIRRf-f_MHWHfUCA2Btrf16qEgT8jPEE').sheet1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, name, email, company, url, gsc_property, ga4_property_id])
        return True
    except Exception as e:
        st.error(f"Error saving lead: {e}")
        return False

def fetch_page_with_timing(url):
    """Fetch page content with timing"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=15)
        load_time = time.time() - start_time
        return response.text, load_time, len(response.content)
    except Exception as e:
        return None, 0, 0

def check_technical_elements(base_url):
    """Check robots.txt and sitemap.xml"""
    domain = urlparse(base_url).scheme + "://" + urlparse(base_url).netloc
    findings = {}
    
    # Check robots.txt
    try:
        robots_response = requests.get(f"{domain}/robots.txt", timeout=5)
        findings['has_robots_txt'] = robots_response.status_code == 200 and len(robots_response.text) > 10
    except:
        findings['has_robots_txt'] = False
    
    # Check sitemap.xml
    try:
        sitemap_response = requests.get(f"{domain}/sitemap.xml", timeout=5)
        findings['has_sitemap'] = sitemap_response.status_code == 200 and 'xml' in sitemap_response.text[:100].lower()
    except:
        findings['has_sitemap'] = False
    
    return findings

def find_internal_links(soup, base_url):
    """Find important internal pages"""
    links = []
    domain = urlparse(base_url).netloc
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        if urlparse(full_url).netloc == domain:
            links.append(full_url)
    
    important_keywords = ['about', 'contact', 'product', 'service', 'shop', 'store', 'collection', 'blog']
    important_pages = []
    
    for link in links:
        link_lower = link.lower()
        if any(keyword in link_lower for keyword in important_keywords):
            if link not in important_pages and len(important_pages) < 4:
                important_pages.append(link)
    
    has_blog = any('blog' in link.lower() for link in links)
    
    return important_pages[:3], has_blog

def detect_schemas(soup):
    """Detect schema markup"""
    schemas_found = []
    
    # JSON-LD
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        try:
            schema_data = json.loads(script.string)
            if isinstance(schema_data, dict) and '@type' in schema_data:
                schemas_found.append(schema_data['@type'])
            elif isinstance(schema_data, list):
                for item in schema_data:
                    if isinstance(item, dict) and '@type' in item:
                        schemas_found.append(item['@type'])
        except:
            pass
    
    # Microdata
    microdata = soup.find_all(attrs={'itemtype': True})
    for item in microdata:
        schema_type = item['itemtype'].split('/')[-1]
        schemas_found.append(schema_type)
    
    return list(set(schemas_found))

def check_page_elements(soup):
    """Check for important page elements"""
    elements = {}
    
    canonical = soup.find('link', rel='canonical')
    elements['has_canonical'] = canonical is not None
    
    meta_robots = soup.find('meta', attrs={'name': 'robots'})
    elements['meta_robots'] = meta_robots['content'] if meta_robots else None
    
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    og_image = soup.find('meta', property='og:image')
    elements['has_opengraph'] = all([og_title, og_desc, og_image])
    
    twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
    elements['has_twitter_card'] = twitter_card is not None
    
    elements['has_json_ld'] = len(soup.find_all('script', type='application/ld+json')) > 0
    
    gsc_meta = soup.find('meta', attrs={'name': 'google-site-verification'})
    elements['has_gsc_verification'] = gsc_meta is not None
    
    hreflang = soup.find_all('link', rel='alternate', hreflang=True)
    elements['has_hreflang'] = len(hreflang) > 0
    
    return elements

def analyze_page_resources(soup):
    """Analyze images and resources"""
    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt') or len(img.get('alt', '').strip()) == 0]
    
    scripts = soup.find_all('script', src=True)
    stylesheets = soup.find_all('link', rel='stylesheet')
    internal_links = soup.find_all('a', href=True)
    
    return {
        'total_images': len(images),
        'images_without_alt': len(images_without_alt),
        'external_scripts': len(scripts),
        'stylesheets': len(stylesheets),
        'internal_links': len(internal_links)
    }

def analyze_single_page(url, page_name="Page"):
    """Analyze a single page"""
    html, load_time, page_size = fetch_page_with_timing(url)
    
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    title = soup.find('title')
    title_text = title.text.strip() if title else "No title found"
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_desc_text = meta_desc['content'] if meta_desc else "No meta description"
    
    h1_tags = soup.find_all('h1')
    h1_count = len(h1_tags)
    h1_texts = [h1.text.strip() for h1 in h1_tags[:3]]
    
    schemas = detect_schemas(soup)
    page_elements = check_page_elements(soup)
    resources = analyze_page_resources(soup)
    
    return {
        'url': url,
        'page_name': page_name,
        'title': title_text,
        'title_length': len(title_text),
        'meta_description': meta_desc_text,
        'meta_length': len(meta_desc_text),
        'h1_count': h1_count,
        'h1_texts': h1_texts,
        'load_time': round(load_time, 2),
        'page_size_kb': round(page_size / 1024, 2),
        'schemas': schemas,
        'page_elements': page_elements,
        'resources': resources
    }

def comprehensive_audit(url, gsc_property=None, ga4_property_id=None):
    """Perform comprehensive audit"""
    st.info("🔍 Starting comprehensive audit...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Technical checks
    status_text.text("Checking technical infrastructure...")
    technical_findings = check_technical_elements(url)
    progress_bar.progress(10)
    
    # GSC data
    gsc_data = None
    if gsc_property:
        status_text.text("Fetching Google Search Console data...")
        gsc_fetcher = GSCFetcher()
        gsc_data = gsc_fetcher.get_search_analytics(gsc_property, days=28)
        progress_bar.progress(20)
    
    # GA4 data
    ga4_data = None
    if ga4_property_id:
        status_text.text("Fetching Google Analytics data...")
        ga4_fetcher = GA4Fetcher()
        ga4_data = ga4_fetcher.get_analytics_data(ga4_property_id, days=28)
        progress_bar.progress(30)
    
    # Analyze homepage
    status_text.text("Analyzing homepage...")
    homepage_data = analyze_single_page(url, "Homepage")
    
    if not homepage_data:
        st.error("Could not fetch the website.")
        return None, None, None, None, None
    
    progress_bar.progress(40)
    
    # Find additional pages
    html, _, _ = fetch_page_with_timing(url)
    soup = BeautifulSoup(html, 'html.parser')
    additional_urls, has_blog = find_internal_links(soup, url)
    
    all_pages_data = [homepage_data]
    
    for idx, add_url in enumerate(additional_urls[:3]):
        status_text.text(f"Analyzing page {idx + 2}...")
        page_data = analyze_single_page(add_url, f"Page {idx + 2}")
        if page_data:
            all_pages_data.append(page_data)
        progress_bar.progress(40 + (idx + 1) * 15)
    
    progress_bar.progress(100)
    status_text.text("✅ Audit complete!")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    return all_pages_data, technical_findings, has_blog, gsc_data, ga4_data

def display_gsc_insights(gsc_data):
    """Display GSC data"""
    if not gsc_data or not gsc_data.get('success'):
        st.warning("⚠️ Could not fetch GSC data. " + gsc_data.get('message', '') if gsc_data else '')
        return
    
    st.subheader("🔍 Google Search Console Insights")
    
    summary = gsc_data['summary']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Clicks", f"{summary['total_clicks']:,}")
    with col2:
        st.metric("Impressions", f"{summary['total_impressions']:,}")
    with col3:
        st.metric("Avg CTR", f"{summary['avg_ctr']}%")
    with col4:
        st.metric("Avg Position", f"{summary['avg_position']}")
    
    st.caption(f"Data from: {summary['date_range']}")
    
    # Top queries
    with st.expander("🔎 Top Search Queries", expanded=True):
        queries = gsc_data['queries'][:10]
        for q in queries:
            st.write(f"**{q['keys'][0]}**")
            cols = st.columns(4)
            cols[0].caption(f"Clicks: {q.get('clicks', 0)}")
            cols[1].caption(f"Impressions: {q.get('impressions', 0)}")
            cols[2].caption(f"CTR: {round(q.get('ctr', 0) * 100, 2)}%")
            cols[3].caption(f"Position: {round(q.get('position', 0), 1)}")
    
    # Top pages
    with st.expander("📄 Top Performing Pages"):
        pages = gsc_data['pages'][:10]
        for p in pages:
            st.write(f"**{p['keys'][0]}**")
            cols = st.columns(4)
            cols[0].caption(f"Clicks: {p.get('clicks', 0)}")
            cols[1].caption(f"Impressions: {p.get('impressions', 0)}")
            cols[2].caption(f"CTR: {round(p.get('ctr', 0) * 100, 2)}%")
            cols[3].caption(f"Position: {round(p.get('position', 0), 1)}")

def display_ga4_insights(ga4_data):
    """Display GA4 data"""
    if not ga4_data or not ga4_data.get('success'):
        st.warning("⚠️ Could not fetch GA4 data. " + ga4_data.get('message', '') if ga4_data else '')
        return
    
    st.subheader("📊 Google Analytics Insights")
    
    overall = ga4_data.get('overall')
    if overall:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Sessions", f"{overall['sessions']:,}")
        with col2:
            st.metric("Users", f"{overall['users']:,}")
        with col3:
            st.metric("Pageviews", f"{overall['pageviews']:,}")
        with col4:
            st.metric("Bounce Rate", f"{overall['bounce_rate']}%")
        with col5:
            st.metric("Avg Duration", f"{int(overall['avg_session_duration'])}s")
        
        st.caption(f"Data from: {ga4_data['date_range']}")
    
    # Top pages
    with st.expander("📈 Top Pages by Traffic", expanded=True):
        for page in ga4_data['top_pages'][:10]:
            st.write(f"**{page['page']}**")
            cols = st.columns(2)
            cols[0].caption(f"Pageviews: {page['pageviews']:,}")
            cols[1].caption(f"Sessions: {page['sessions']:,}")
    
    # Traffic sources
    with st.expander("🌐 Traffic Sources"):
        for source in ga4_data['traffic_sources'][:10]:
            st.write(f"**{source['source']}**")
            st.caption(f"Sessions: {source['sessions']:,}")

def display_page_results(page_data):
    """Display page analysis"""
    st.markdown(f"### 📄 {page_data['page_name']}")
    st.caption(page_data['url'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Title Length", f"{page_data['title_length']} chars",
                 delta="✓" if 50 <= page_data['title_length'] <= 60 else "⚠")
    
    with col2:
        st.metric("Meta Desc Length", f"{page_data['meta_length']} chars",
                 delta="✓" if 120 <= page_data['meta_length'] <= 160 else "⚠")
    
    with col3:
        st.metric("Load Time", f"{page_data['load_time']}s",
                 delta="✓" if page_data['load_time'] < 3 else "⚠")
    
    with col4:
        st.metric("Page Size", f"{page_data['page_size_kb']} KB",
                 delta="✓" if page_data['page_size_kb'] < 1000 else "⚠")
    
    with st.expander("📋 View Details", expanded=False):
        st.write(f"**Title:** {page_data['title']}")
        st.write(f"**Meta Description:** {page_data['meta_description']}")
        st.write(f"**H1 Count:** {page_data['h1_count']} - {', '.join(page_data['h1_texts'][:2])}")
        
        if page_data['schemas']:
            st.write(f"**Schema Markup:** {', '.join(page_data['schemas'])}")
        else:
            st.write(f"**Schema Markup:** ❌ None detected")
        
        elements = page_data['page_elements']
        st.write(f"**Canonical Tag:** {'✅ Present' if elements['has_canonical'] else '❌ Missing'}")
        st.write(f"**OpenGraph Tags:** {'✅ Complete' if elements['has_opengraph'] else '⚠️ Incomplete'}")
        st.write(f"**GSC Verification:** {'✅ Detected' if elements['has_gsc_verification'] else '❓ Not detected'}")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Total Images:** {page_data['resources']['total_images']}")
            st.write(f"**Images without ALT:** {page_data['resources']['images_without_alt']}")
        with col_b:
            st.write(f"**Internal Links:** {page_data['resources']['internal_links']}")
            st.write(f"**External Scripts:** {page_data['resources']['external_scripts']}")
    
    st.markdown("---")

def generate_ai_recommendations(all_pages_data, technical_findings, has_blog, gsc_data, ga4_data):
    """Generate AI recommendations based on all data"""
    
    summary = f"""COMPREHENSIVE SEO AUDIT FOR: {all_pages_data[0]['url']}

TECHNICAL INFRASTRUCTURE:
- robots.txt: {'✅ EXISTS' if technical_findings['has_robots_txt'] else '❌ MISSING'}
- sitemap.xml: {'✅ EXISTS' if technical_findings['has_sitemap'] else '❌ MISSING'}
- Blog/Content section: {'✅ FOUND' if has_blog else '❌ NOT FOUND'}

PAGES ANALYZED: {len(all_pages_data)}

"""
    
    # Add GSC insights to summary
    if gsc_data and gsc_data.get('success'):
        summary += f"""
GOOGLE SEARCH CONSOLE DATA (Last 28 days):
- Total Clicks: {gsc_data['summary']['total_clicks']:,}
- Total Impressions: {gsc_data['summary']['total_impressions']:,}
- Average CTR: {gsc_data['summary']['avg_ctr']}%
- Average Position: {gsc_data['summary']['avg_position']}

Top 5 Queries:
"""
        for q in gsc_data['queries'][:5]:
            summary += f"  - {q['keys'][0]}: {q.get('clicks', 0)} clicks, Position {round(q.get('position', 0), 1)}\n"
    
    # Add GA4 insights
    if ga4_data and ga4_data.get('success') and ga4_data.get('overall'):
        summary += f"""
GOOGLE ANALYTICS DATA (Last 28 days):
- Sessions: {ga4_data['overall']['sessions']:,}
- Users: {ga4_data['overall']['users']:,}
- Pageviews: {ga4_data['overall']['pageviews']:,}
- Bounce Rate: {ga4_data['overall']['bounce_rate']}%

Top 3 Pages:
"""
        for p in ga4_data['top_pages'][:3]:
            summary += f"  - {p['page']}: {p['pageviews']:,} views\n"
    
    # Add page details
    for page in all_pages_data:
        summary += f"\n{page['page_name']} - {page['url']}\n"
        summary += f"Title: {page['title']} ({page['title_length']} chars - {'GOOD' if 50 <= page['title_length'] <= 60 else 'NEEDS OPTIMIZATION'})\n"
        summary += f"Meta: {page['meta_length']} chars - {'GOOD' if 120 <= page['meta_length'] <= 160 else 'NEEDS WORK'}\n"
        summary += f"H1 tags: {page['h1_count']} - {'GOOD' if page['h1_count'] == 1 else 'ISSUE'}\n"
        summary += f"Load time: {page['load_time']}s - {'GOOD' if page['load_time'] < 3 else 'SLOW'}\n"
        summary += f"Schema: {', '.join(page['schemas']) if page['schemas'] else '❌ MISSING'}\n"
        summary += f"Images without ALT: {page['resources']['images_without_alt']}/{page['resources']['total_images']}\n"
    
    prompt = f"""You are a senior SEO consultant with 20+ years of experience. Based on the verified data below, provide 7-10 specific, prioritized recommendations.

{summary}

CRITICAL RULES:
1. ONLY recommend fixes for issues actually found in the data
2. DO NOT suggest things that already exist
3. Reference specific pages, metrics, and findings
4. If GSC/GA4 data is available, use it to prioritize recommendations
5. Focus on high-impact, actionable items

Format:
## HIGH PRIORITY
[Issues that significantly impact rankings/traffic]

## MEDIUM PRIORITY  
[Important optimizations]

## QUICK WINS
[Easy fixes with good impact]

Be specific, reference exact data, and explain expected impact."""

    with st.spinner('🤖 Generating evidence-based recommendations...'):
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3500,
            messages=[{"role": "user", "content": prompt}]
        )
    
    return message.content[0].text

# MAIN APP
st.title("🔍 AI-Powered SEO Audit Tool")
st.markdown("**By Punkaj Saini | Digital Marketing Consultant**")
st.markdown("Comprehensive SEO audit with real Google Search Console & Analytics data")
st.markdown("---")

with st.form("audit_form"):
    st.subheader("📝 Your Details")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name *", placeholder="John Doe")
        email = st.text_input("Email *", placeholder="john@company.com")
    with col2:
        company = st.text_input("Company (optional)", placeholder="Acme Inc")
        website_url = st.text_input("Website URL *", placeholder="https://example.com")
    
    st.markdown("---")
    st.subheader("🔗 Connect Your Data (Optional - Highly Recommended)")
    
    st.info(f"""
**Unlock the full audit with real Google data!**

Please add this email as a viewer to your properties:
📧 **{SERVICE_ACCOUNT_EMAIL}**

**Instructions:**
- **GSC:** Search Console → Settings → Users → Add User
- **GA4:** Analytics → Admin → Property Access → Add User (Viewer role)

This gives us access to your actual search queries, traffic data, and performance metrics.
    """)
    
    col3, col4 = st.columns(2)
    with col3:
        gsc_property = st.text_input(
            "GSC Property URL (optional)",
            placeholder="https://example.com or sc-domain:example.com",
            help="Find in GSC property dropdown. Leave blank if you haven't added our email yet."
        )
    with col4:
        ga4_property_id = st.text_input(
            "GA4 Property ID (optional)",
            placeholder="123456789",
            help="Find in GA4 Admin → Property Settings. Leave blank if you haven't added our email yet."
        )
    
    submit = st.form_submit_button("🚀 Run Comprehensive SEO Audit", use_container_width=True)
    
    if submit:
        if not name or not email or not website_url:
            st.error("Please fill in Name, Email, and Website URL")
        elif not website_url.startswith(('http://', 'https://')):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            # Save lead
            save_to_sheets(name, email, company, website_url, gsc_property or "Not provided", ga4_property_id or "Not provided")
            
           # Initialize email sender
            email_sender = EmailSender()

            # Send onboarding email if GSC/GA4 not provided
                if not gsc_property or not ga4_property_id:
                    email_sender.send_onboarding_email(email, name, website_url, SERVICE_ACCOUNT_EMAIL)
                    st.info(f"📧 Sent setup instructions to {email}")
            
            # Run audit
            all_pages_data, technical_findings, has_blog, gsc_data, ga4_data = comprehensive_audit(
                website_url, 
                gsc_property if gsc_property else None,
                ga4_property_id if ga4_property_id else None
            )
            
            if all_pages_data:
                st.success(f"✅ Analyzed {len(all_pages_data)} pages successfully!")
                
                # Technical findings
                st.header("🔧 Technical Infrastructure")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("robots.txt", "✅ Found" if technical_findings['has_robots_txt'] else "❌ Missing")
                with col2:
                    st.metric("sitemap.xml", "✅ Found" if technical_findings['has_sitemap'] else "❌ Missing")
                with col3:
                    st.metric("Blog Section", "✅ Found" if has_blog else "❌ Not Found")
                
                st.markdown("---")
                
                # GSC insights
                if gsc_data:
                    display_gsc_insights(gsc_data)
                    st.markdown("---")
                
                # GA4 insights
                if ga4_data:
                    display_ga4_insights(ga4_data)
                    st.markdown("---")
                
                # Page analysis
                st.header("📊 Page-by-Page Analysis")
                for page_data in all_pages_data:
                    display_page_results(page_data)
                
                # AI recommendations
                st.header("🤖 AI-Powered Recommendations")
                st.caption("Based on verified findings from this audit")
                recommendations = generate_ai_recommendations(all_pages_data, technical_findings, has_blog, gsc_data, ga4_data)
                st.markdown(recommendations)
                
                st.markdown("---")
                st.success("💡 **Want help implementing these recommendations?** Let's discuss your digital growth strategy.")
                st.info("[Schedule a Call](mailto:punkaj@psdigital.io) | [LinkedIn](https://linkedin.com/in/punkaj)")

                # Send audit complete email
                try:
                email_sender.send_audit_complete_email(email, name, website_url)
                st.caption("✅ Audit summary sent to your email")
                except:
                pass  # Don't break if email fails

st.sidebar.title("About")
st.sidebar.info("""
**AI SEO Audit Tool**

Built by Punkaj Saini - 20+ years in SEO & digital strategy.

This tool analyzes your site with REAL data from Google Search Console and Analytics - not guesses!

📧 punkaj@psdigital.io  
🌐 [psdigital.io](https://psdigital.io)  
💼 [LinkedIn](https://linkedin.com/in/punkaj)
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### ✅ What We Check:")
st.sidebar.markdown("""
**Technical:**
- robots.txt & sitemap
- Page speed & size
- Schema markup
- Meta tags & OpenGraph
- Canonical tags

**Real Data:**
- GSC search queries
- Traffic & rankings
- GA4 user behavior
- Top performing pages
- CTR & impressions
""")
