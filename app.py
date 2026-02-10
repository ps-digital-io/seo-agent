import streamlit as st
import anthropic
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=api_key)

st.set_page_config(page_title="AI SEO Audit Tool", page_icon="🔍", layout="wide")

st.title("🔍 AI-Powered SEO Audit Tool")
st.markdown("**By Punkaj Saini | Digital Marketing Consultant**")
st.markdown("---")

def fetch_page(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text
    except Exception as e:
        return None

def analyze_seo(url):
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
        st.info("💡 Want a detailed audit with actionable implementation plan? [Contact Punkaj](mailto:punkaj.saini@gmail.com)")

with st.form("audit_form"):
    url_input = st.text_input("Enter Website URL", placeholder="https://example.com")
    submit = st.form_submit_button("🚀 Run SEO Audit", use_container_width=True)
    
    if submit and url_input:
        if not url_input.startswith(('http://', 'https://')):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            analyze_seo(url_input)

st.sidebar.title("About")
st.sidebar.info("""
**AI SEO Audit Tool**

Built by Punkaj Saini, a digital marketing consultant with 20+ years of experience in SEO, digital strategy, and growth marketing.

This tool uses AI to analyze websites and provide actionable SEO recommendations instantly.

📧 punkaj.saini@gmail.com  
🌐 psdigital.io  
💼 [LinkedIn](https://linkedin.com/in/punkaj)
""")