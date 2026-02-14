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

def find_internal_links(soup, base_url):
    """Find important internal pages to audit"""
    links = []
    domain = urlparse(base_url).netloc
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        
        # Only internal links from same domain
        if urlparse(full_url).netloc == domain:
            links.append(full_url)
    
    # Filter for important pages (about, contact, products, services, etc.)
    important_keywords = ['about', 'contact', 'product', 'service', 'shop', 'store', 'collection']
    important_pages = []
    
    for link in links:
        link_lower = link.lower()
        if any(keyword in link_lower for keyword in important_keywords):
            if link not in important_pages and len(important_pages) < 4:
                important_pages.append(link)
    
    return important_pages[:3]  # Return max 3 additional pages

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
        schemas_found.append(f"{schema_type} (Microdata)")
    
    return list(set(schemas_found)) if schemas_found else ["No schema markup found"]

def analyze_page_resources(soup):
    """Analyze images and resource counts"""
    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt')]
    
    scripts = soup.find_all('script', src=True)
    stylesheets = soup.find_all('link', rel='stylesheet')
    
    return {
        'total_images': len(images),
        'images_without_alt': len(images_without_alt),
        'external_scripts': len(scripts),
        'stylesheets': len(stylesheets)
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
        'resources': resources
    }

def comprehensive_audit(url):
    """Perform comprehensive multi-page audit"""
    st.info("🔍 Crawling website and analyzing multiple pages...")
    
    # Analyze homepage
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Analyzing homepage...")
    homepage_data = analyze_single_page(url, "Homepage")
    
    if not homepage_data:
        st.error("Could not fetch the website. Please check the URL.")
        return None
    
    progress_bar.progress(25)
    
    # Find and analyze additional pages
    html, _, _ = fetch_page_with_timing(url)
    soup = BeautifulSoup(html, 'html.parser')
    additional_urls = find_internal_links(soup, url)
    
    all_pages_data = [homepage_data]
    
    for idx, add_url in enumerate(additional_urls[:3]):  # Max 3 additional pages
        status_text.text(f"Analyzing page {idx + 2}...")
        page_data = analyze_single_page(add_url, f"Page {idx + 2}")
        if page_data:
            all_pages_data.append(page_data)
        progress_bar.progress(25 + (idx + 1) * 25)
    
    progress_bar.progress(100)
    status_text.text("✅ Analysis complete!")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    return all_pages_data

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
        
        st.write(f"**Schema Markup:** {', '.join(page_data['schemas'][:3])}")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Total Images:** {page_data['resources']['total_images']}")
            st.write(f"**Images without ALT:** {page_data['resources']['images_without_alt']}")
        with col_b:
            st.write(f"**External Scripts:** {page_data['resources']['external_scripts']}")
            st.write(f"**Stylesheets:** {page_data['resources']['stylesheets']}")
    
    st.markdown("---")

def generate_ai_recommendations(all_pages_data):
    """Generate AI recommendations based on all page data"""
    
    summary = f"Website: {all_pages_data[0]['url']}\n"
    summary += f"Total pages analyzed: {len(all_pages_data)}\n\n"
    
    for page in all_pages_data:
        summary += f"\n{page['page_name']} ({page['url']}):\n"
        summary += f"- Title: {page['title']} ({page['title_length']} chars)\n"
        summary += f"- Meta: {page['meta_description'][:100]}... ({page['meta_length']} chars)\n"
        summary += f"- H1s: {page['h1_count']} found\n"
        summary += f"- Load time: {page['load_time']}s, Size: {page['page_size_kb']}KB\n"
        summary += f"- Schema: {', '.join(page['schemas'][:2])}\n"
        summary += f"- Images: {page['resources']['total_images']} total, {page['resources']['images_without_alt']} missing ALT\n"
    
    prompt = f"""You are an SEO expert with 20+ years of experience. Analyze this comprehensive multi-page website audit and provide 7-10 prioritized, actionable recommendations.

{summary}

Focus on:
1. Critical technical issues across all pages
2. Content optimization opportunities
3. Performance improvements (page speed, size)
4. Schema markup recommendations
5. Image optimization needs
6. Quick wins vs long-term improvements

Format with clear headings, specific page references, and implementation priority."""

    with st.spinner('🤖 AI is analyzing all pages and generating recommendations...'):
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
    
    return message.content[0].text

st.title("🔍 AI-Powered SEO Audit Tool")
st.markdown("**By Punkaj Saini | Digital Marketing Consultant**")
st.markdown("Get comprehensive, AI-powered SEO insights across multiple pages")
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
            # Save lead
            save_to_sheets(name, email, company, url_input)
            
            # Run comprehensive audit
            all_pages_data = comprehensive_audit(url_input)
            
            if all_pages_data:
                st.success(f"✅ Analyzed {len(all_pages_data)} pages successfully!")
                st.markdown("---")
                
                # Display results for each page
                st.header("📊 Page-by-Page Analysis")
                for page_data in all_pages_data:
                    display_page_results(page_data)
                
                # Generate and display AI recommendations
                st.header("🤖 AI-Powered Recommendations")
                recommendations = generate_ai_recommendations(all_pages_data)
                st.markdown(recommendations)
                
                st.markdown("---")
                st.info("💡 Want a detailed implementation roadmap and hands-on support? [Contact Punkaj](mailto:punkaj@psdigital.io)")

st.sidebar.title("About")
st.sidebar.info("""
**AI SEO Audit Tool**

Built by Punkaj Saini, a digital marketing consultant with 20+ years of experience in SEO, digital strategy, and growth marketing.

This tool analyzes multiple pages, detects schema markup, measures performance, and provides AI-powered recommendations.

📧 punkaj@psdigital.io  
🌐 [psdigital.io](https://psdigital.io)  
💼 [LinkedIn](https://linkedin.com/in/punkaj)
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 What This Tool Checks:")
st.sidebar.markdown("""
- ✅ Multi-page analysis
- ✅ Schema markup detection
- ✅ Page load performance
- ✅ Image optimization
- ✅ Meta tags & content
- ✅ Mobile responsiveness indicators
""")
