import anthropic
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=api_key)

def fetch_page(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text
    except Exception as e:
        return f"Error fetching page: {e}"

def analyze_seo(url):
    print(f"Analyzing: {url}\n")
    
    html = fetch_page(url)
    soup = BeautifulSoup(html, 'html.parser')
    
    title = soup.find('title')
    title_text = title.text if title else "No title found"
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_desc_text = meta_desc['content'] if meta_desc else "No meta description"
    
    h1_tags = soup.find_all('h1')
    h1_count = len(h1_tags)
    h1_texts = [h1.text.strip() for h1 in h1_tags[:3]]
    
    report = f"""
SEO Analysis Report
==================
URL: {url}

Title Tag: {title_text}
Title Length: {len(title_text)} characters

Meta Description: {meta_desc_text}
Meta Description Length: {len(meta_desc_text)} characters

H1 Tags Found: {h1_count}
H1 Content: {h1_texts}
"""
    
    print(report)
    
    prompt = f"""You are an SEO expert. Analyze this webpage data and provide 3-5 actionable recommendations:

{report}

Focus on: title optimization, meta description quality, H1 tag usage, and quick wins."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    print("\nAI Recommendations:")
    print("===================")
    print(message.content[0].text)

if __name__ == "__main__":
    test_url = input("Enter website URL (e.g., https://example.com): ")
    analyze_seo(test_url)