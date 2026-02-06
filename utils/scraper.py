import requests
from bs4 import BeautifulSoup
import logging

def scrape_url(url):
    """
    Scrape full text content from a URL.
    Returns the cleaned text or None if failed.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script, style, and other non-content elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
            script.decompose()

        text = soup.get_text()

        # Clean text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return None
