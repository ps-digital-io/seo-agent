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

load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=api_key)

st.set_page_config(page_title="AI SEO Audit Tool", page_icon="🔍", layout="wide")

def save_to_sheets(name, email, company, url):
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key('1eilZ_xDiOukzIRRf-f_MHWHfUCA2Btrf16qEgT8jPEE').sheet1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, name, email, company, url])
        return True
    except Exception as e:
        st.error(f"Error saving lead: {e}")
        return False

def fetch_page_with_timing(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=15)
        load_time = time.time() - start_time
        return response.text, load_time, len(response.content)
    except Exception as e:
        return None, 0, 0

def check_technical_elements(base_url):
    """Actually verify technical SEO elements exist"""
    domain = urlparse(base_url).scheme + "://" + urlparse(base_url).netloc
    findings = {}
    
    # Check robots.txt
    try:
        robots_response = requests.get(f"{domain}/robots.txt", timeout=5)
        findings['has_robots_txt'] = robots_response.status_code == 200 and len(robots_response.text) > 10
        findings['robots_txt_content'] = robots_response.text[:500] if findings['has_robots_txt'] else None
    except:
        findings['has_robots_txt'] = False
        findings['robots_txt_content'] = None
    
    # Check sitemap.xml
    try:
        sitemap_response = requests.get(f"{domain}/sitemap.xml", timeout=5)
        findings['has_sitemap'] = sitemap_response.status_code == 200 and 'xml' in sitemap_response.text[:100].lower()
    except:
        findings['has_sitemap'] = False
    
    return findings

def find_internal_links(soup, base_url):
    """Find important internal pages to audit"""
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
    
    # Track if blog/content section exists
    has_blog = any('blog' in link.lower() for link in links)
    
    return important_pages[:3], has_blog

def detect_schemas(soup):
    """Detect schema markup on page"""
    schemas_found = []
    
    # JSON-LD schemas
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
    
    # Microdata schemas
    microdata = soup.find_all(attrs={'itemtype': True})
    for item in microdata:
        schema_type = item['itemtype'].split('/')[-1]
        schemas_found.append(f"{schema_type}")
    
    return list(set(schemas_found))

def check_page_elements(soup):
    """Check for important page elements"""
    elements = {}
    
    # Canonical tag
    canonical = soup.find('link', rel='canonical')
    elements['has_canonical'] = canonical is not None
    
    # Meta robots
    meta_robots = soup.find('meta', attrs={'name': 'robots'})
    elements['meta_robots'] = meta_robots['content'] if meta_robots else None
    
    # OpenGraph tags
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    og_image = soup.find('meta', property='og:image')
    elements['has_opengraph'] = all([og_title, og_desc, og_image])
    
    # Twitter Card
    twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
    elements['has_twitter_card'] = twitter_card is not None
    
    # Structured data
    elements['has_json_ld'] = len(soup.find_all('script', type='application/ld+json')) > 0
    
    # GSC/GA verification tags
    gsc_meta = soup.find('meta', attrs={'name': 'google-site-verification'})
    elements['has_gsc_verification'] = gsc_meta is not None
    
    # Hreflang
    hreflang = soup.find_all('link', rel='alternate', hreflang=True)
    elements['has_hreflang'] = len(hreflang) > 0
    
    return elements

def analyze_page_resources(soup):
    """Analyze images and resource counts"""
    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt') or len(img.get('alt', '').strip()) == 0]
    
    scripts = soup.find_all('script', src=True)
    stylesheets = soup.find_all('link', rel='stylesheet')
    
    # Internal links
    internal_links = soup.find_all('a', href=True)
    
    return {
        'total_images': len(images),
        'images_without_alt': len(images_without_alt),
        'external_scripts': len(scripts),
        'stylesheets': len(stylesheets),
        'internal_links': len(internal_links)
    }

def analyze_single_page(url, page_name="Page"):
    """Analyze a single page and return results"""
    html, load_time, page_size = fetch_page_with_timing(url)
    
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Basic SEO elements
    title = soup.find('title')
    title_text = title.text.strip() if title else "No title found"
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_desc_text = meta_desc['content'] if meta_desc else "No meta description"
    
    h1_tags = soup.find_all('h1')
    h1_count = len(h1_tags)
    h1_texts = [h1.text.strip() for h1 in h1_tags[:3]]
    
    # Schema detection
    schemas = detect_schemas(soup)
    
    # Page elements check
    page_elements = check_page_elements(soup)
    
    # Resource analysis
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

def comprehensive_audit(url):
    """Perform comprehensive multi-page audit"""
    st.info("🔍 Crawling website and analyzing multiple pages...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Check technical elements first
    status_text.text("Checking technical SEO infrastructure...")
    technical_findings = check_technical_elements(url)
    progress_bar.progress(10)
    
    # Analyze homepage
    status_text.text("Analyzing homepage...")
    homepage_data = analyze_single_page(url, "Homepage")
    
    if not homepage_data:
        st.error("Could not fetch the website. Please check the URL.")
        return None, None, None
    
    progress_bar.progress(30)
    
    # Find and analyze additional pages
    html, _, _ = fetch_page_with_timing(url)
    soup = BeautifulSoup(html, 'html.parser')
    additional_urls, has_blog = find_internal_links(soup, url)
    
    all_pages_data = [homepage_data]
    
    for idx, add_url in enumerate(additional_urls[:3]):
        status_text.text(f"Analyzing page {idx + 2}...")
        page_data = analyze_single_page(add_url, f"Page {idx + 2}")
        if page_data:
            all_pages_data.append(page_data)
        progress_bar.progress(30 + (idx + 1) * 20)
    
    progress_bar.progress(100)
    status_text.text("✅ Analysis complete!")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    return all_pages_data, technical_findings, has_blog

def display_page_results(page_data):
    """Display results for a single page"""
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
            st.write(f"**Schema Markup Found:** {', '.join(page_data['schemas'])}")
        else:
            st.write(f"**Schema Markup:** ❌ None detected")
        
        # Technical elements
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

def generate_ai_recommendations(all_pages_data, technical_findings, has_blog):
    """Generate evidence-based AI recommendations"""
    
    # Build factual summary
    summary = f"""VERIFIED FINDINGS FOR: {all_pages_data[0]['url']}

TECHNICAL INFRASTRUCTURE (Actually Checked):
- robots.txt: {'✅ EXISTS' if technical_findings['has_robots_txt'] else '❌ MISSING'}
- sitemap.xml: {'✅ EXISTS' if technical_findings['has_sitemap'] else '❌ MISSING'}
- Blog/Content section: {'✅ FOUND' if has_blog else '❌ NOT FOUND'}

PAGES ANALYZED: {len(all_pages_data)}

"""
    
    for page in all_pages_data:
        summary += f"\n{page['page_name']} - {page['url']}\n"
        summary += f"Title: {page['title']} ({page['title_length']} chars - {'GOOD' if 50 <= page['title_length'] <= 60 else 'NEEDS OPTIMIZATION'})\n"
        summary += f"Meta Description: {page['meta_length']} chars - {'GOOD' if 120 <= page['meta_length'] <= 160 else 'NEEDS WORK'}\n"
        summary += f"H1 tags: {page['h1_count']} found - {'GOOD' if page['h1_count'] == 1 else 'ISSUE: Should have exactly 1'}\n"
        summary += f"Load time: {page['load_time']}s - {'GOOD' if page['load_time'] < 3 else 'SLOW - needs optimization'}\n"
        summary += f"Page size: {page['page_size_kb']}KB - {'GOOD' if page['page_size_kb'] < 1000 else 'LARGE - needs optimization'}\n"
        
        if page['schemas']:
            summary += f"Schema markup: ✅ Found - {', '.join(page['schemas'])}\n"
        else:
            summary += f"Schema markup: ❌ MISSING - No structured data detected\n"
        
        elements = page['page_elements']
        summary += f"Canonical tag: {'✅ Present' if elements['has_canonical'] else '❌ MISSING'}\n"
        summary += f"OpenGraph: {'✅ Complete' if elements['has_opengraph'] else '⚠️ Incomplete or missing'}\n"
        summary += f"GSC verification: {'✅ Detected' if elements['has_gsc_verification'] else 'Not detected in meta tags'}\n"
        summary += f"Images without ALT: {page['resources']['images_without_alt']} out of {page['resources']['total_images']}\n"
        summary += f"Internal links: {page['resources']['internal_links']}\n"
    
    prompt = f"""You are an SEO expert. Based on ONLY the verified findings below, provide 5-8 specific, actionable recommendations.

CRITICAL RULES:
1. ONLY recommend fixes for issues that are ACTUALLY DETECTED in the data
2. DO NOT make generic suggestions for things that already exist (e.g. if robots.txt exists, don't recommend creating it)
3. DO NOT assume anything - only work with verified facts
4. Be specific - reference exact pages, metrics, and findings
5. Prioritize by impact

{summary}

Provide recommendations in this format:
## [Priority Level] [Specific Issue Found]
**What's wrong:** [Exact finding from data]
**Fix:** [Specific action]
**Page(s):** [Which pages]
**Impact:** [Expected improvement]

Focus ONLY on genuine issues found in the data above."""

    with st.spinner('🤖 Generating evidence-based recommendations...'):
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
    
    return message.content[0].text

st.title("🔍 AI-Powered SEO Audit Tool")
st.markdown("**By Punkaj Saini | Digital Marketing Consultant**")
st.markdown("Comprehensive, evidence-based SEO audit with verified technical checks")
st.markdown("---")

with st.form("audit_form"):
    st.subheader("Enter Your Details")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name *", placeholder="John Doe")
        email = st.text_input("Email *", placeholder="john@company.com")
    with col2:
        company = st.text_input("Company (optional)", placeholder="Acme Inc")
        url_input = st.text_input("Website URL *", placeholder="https://example.com")
    
    submit = st.form_submit_button("🚀 Run Comprehensive SEO Audit", use_container_width=True)
    
    if submit:
        if not name or not email or not url_input:
            st.error("Please fill in all required fields (Name, Email, Website URL)")
        elif not url_input.startswith(('http://', 'https://')):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            save_to_sheets(name, email, company, url_input)
            
            all_pages_data, technical_findings, has_blog = comprehensive_audit(url_input)
            
            if all_pages_data:
                st.success(f"✅ Analyzed {len(all_pages_data)} pages successfully!")
                
                # Show technical findings
                st.header("🔧 Technical SEO Infrastructure")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("robots.txt", "✅ Found" if technical_findings['has_robots_txt'] else "❌ Missing")
                with col2:
                    st.metric("sitemap.xml", "✅ Found" if technical_findings['has_sitemap'] else "❌ Missing")
                with col3:
                    st.metric("Blog Section", "✅ Found" if has_blog else "❌ Not Found")
                
                st.markdown("---")
                
                # Display results for each page
                st.header("📊 Page-by-Page Analysis")
                for page_data in all_pages_data:
                    display_page_results(page_data)
                
                # Generate and display AI recommendations
                st.header("🤖 Evidence-Based Recommendations")
                st.caption("Based only on verified findings from this audit")
                recommendations = generate_ai_recommendations(all_pages_data, technical_findings, has_blog)
                st.markdown(recommendations)
                
                st.markdown("---")
                st.info("💡 Need help implementing these recommendations? [Contact Punkaj](mailto:punkaj@psdigital.io)")

st.sidebar.title("About")
st.sidebar.info("""
**AI SEO Audit Tool**

Built by Punkaj Saini - 20+ years in SEO & digital strategy.

This tool actually VERIFIES what exists on your site before making recommendations - no generic fluff!

📧 punkaj@psdigital.io  
🌐 [psdigital.io](https://psdigital.io)  
💼 [LinkedIn](https://linkedin.com/in/punkaj)
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### ✅ What We Actually Check:")
st.sidebar.markdown("""
- robots.txt & sitemap existence
- Schema markup detection
- Page load performance
- Meta tags & content
- Image optimization
- Canonical tags
- OpenGraph/Twitter cards
- GSC verification
- Internal linking
""")
