import streamlit as st
import anthropic
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

def fetch_page(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text
    except Exception as e:
        return None

def analyze_seo(url, name, email, company):
    with st.spinner('Analyzing website... This may take 10-15 seconds'):
        html = fetch_page(url)
        
        if not html:
            st.error("Could not fetch the website. Please check the URL and try again.")
            return
        
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('title')
        title_text = title.text if title else "No title found"
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_desc_text = meta_desc['content'] if meta_desc else "No meta description"
        
        h1_tags = soup.find_all('h1')
        h1_count = len(h1_tags)
        h1_texts = [h1.text.strip() for h1 in h1_tags[:3]]
        
        st.success("✅ Analysis Complete!")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 SEO Metrics")
            st.metric("Title Length", f"{len(title_text)} chars", 
                     delta="Good" if 50 <= len(title_text) <= 60 else "Needs work")
            st.metric("Meta Description Length", f"{len(meta_desc_text)} chars",
                     delta="Good" if 120 <= len(meta_desc_text) <= 160 else "Needs work")
            st.metric("H1 Tags Found", h1_count,
                     delta="Good" if h1_count == 1 else "Check needed")
        
        with col2:
            st.subheader("📝 Current Content")
            st.write(f"**Title:** {title_text}")
            st.write(f"**Meta Description:** {meta_desc_text}")
            if h1_texts:
                st.write(f"**H1 Tags:** {', '.join(h1_texts)}")
        
        st.markdown("---")
        
        report = f"""
URL: {url}
Title: {title_text} ({len(title_text)} characters)
Meta Description: {meta_desc_text} ({len(meta_desc_text)} characters)
H1 Tags: {h1_count} found - {h1_texts}
"""
        
        prompt = f"""You are an SEO expert with 20+ years of experience. Analyze this webpage and provide 5-7 specific, actionable recommendations.

{report}

Format your response with clear headings and prioritize recommendations by impact. Focus on quick wins and technical improvements."""

        with st.spinner('Generating AI recommendations...'):
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
        
        st.subheader("🤖 AI-Powered Recommendations")
        st.markdown(message.content[0].text)
        
        st.markdown("---")
        st.info("💡 Want a detailed audit with actionable implementation plan? [Contact Punkaj](mailto:punkaj@psdigital.io)")

st.title("🔍 AI-Powered SEO Audit Tool")
st.markdown("**By Punkaj Saini | Digital Marketing Consultant**")
st.markdown("Get instant, AI-powered SEO insights for your website")
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
    
    submit = st.form_submit_button("🚀 Run Free SEO Audit", use_container_width=True)
    
    if submit:
        if not name or not email or not url_input:
            st.error("Please fill in all required fields (Name, Email, Website URL)")
        elif not url_input.startswith(('http://', 'https://')):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            if save_to_sheets(name, email, company, url_input):
                analyze_seo(url_input, name, email, company)
            else:
                st.warning("Analysis will continue, but we couldn't save your details.")
                analyze_seo(url_input, name, email, company)

st.sidebar.title("About")
st.sidebar.info("""
**AI SEO Audit Tool**

Built by Punkaj Saini, a digital marketing consultant with 20+ years of experience in SEO, digital strategy, and growth marketing.

This tool uses AI to analyze websites and provide actionable SEO recommendations instantly.

📧 punkaj@psdigital.io  
🌐 [psdigital.io](https://psdigital.io)  
💼 [LinkedIn](https://linkedin.com/in/punkaj)
""")
