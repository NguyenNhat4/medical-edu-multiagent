import os
import re
import ast
import requests
from bs4 import BeautifulSoup
import asyncio
from rag_agent import MedicalRAG
from utils.app_config import AppConfig

def extract_urls(log_file):
    urls = set()
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if " - Found [" in line:
                try:
                    # Extract the list part
                    start = line.find(" - Found [") + len(" - Found ")
                    # The line ends with "] results."
                    end = line.rfind("] results.") + 1
                    if start == -1 or end == 0:
                        continue
                    list_str = line[start:end]
                    results = ast.literal_eval(list_str)
                    for res in results:
                        if 'url' in res:
                            urls.add(res['url'])
                except Exception as e:
                    print(f"Error parsing line: {line[:50]}... : {e}")
    return list(urls)

def scrape_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
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

async def main():
    print("Initializing MedicalRAG...")
    config = AppConfig()
    rag_agent = MedicalRAG(config)

    urls = extract_urls("provided_logs.txt")
    print(f"Found {len(urls)} URLs to process.")

    for url in urls:
        print(f"Processing: {url}")
        content = scrape_url(url)
        if content:
            if len(content) < 200:
                print(f"Skipping {url}: Content too short ({len(content)} chars).")
                continue

            print(f"Scraped {len(content)} chars. Ingesting...")
            try:
                # Simple chunking to avoid huge chunks
                chunk_size = 1000
                text_chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

                # Add metadata to chunks to help retrieval
                formatted_chunks = []
                for chunk in text_chunks:
                     formatted_chunks.append(f"Source URL: {url}\n\n{chunk}")

                await asyncio.to_thread(
                    rag_agent.ingest_text_chunks,
                    formatted_chunks,
                    metadata_path=f"Scraped: {url}"
                )
                print(f"Successfully ingested {url}")
            except Exception as e:
                print(f"Error ingesting {url}: {e}")
        else:
            print(f"Skipping {url}: No content.")

if __name__ == "__main__":
    asyncio.run(main())
