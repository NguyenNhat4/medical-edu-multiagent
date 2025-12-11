import requests
from typing import List, Dict, Any

class PubmedSearchAgent:
    """
    Processes medical documents for the RAG system with context-aware chunking.
    """
    def __init__(self):
        pass

    def search_pubmed_raw(self, base_url, query: str) -> List[Dict[str, Any]]:
        """Search PubMed and return summaries."""
        if not base_url.endswith("/"):
            base_url += "/"

        # 1. Search for IDs
        search_url = base_url + "esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": 5
        }
        
        try:
            response = requests.get(search_url, params=params)
            data = response.json()
            article_ids = data.get("esearchresult", {}).get("idlist", [])

            if not article_ids:
                return []

            # 2. Fetch Summaries (Metadata)
            summary_url = base_url + "esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(article_ids),
                "retmode": "json"
            }

            summary_response = requests.get(summary_url, params=summary_params)
            summary_data = summary_response.json()
            
            results = []
            uid_data = summary_data.get("result", {})

            for uid in article_ids:
                if uid in uid_data:
                    item = uid_data[uid]
                    title = item.get("title", "")
                    pub_date = item.get("pubdate", "")
                    source = item.get("source", "")

                    # We construct content from metadata as abstract is harder to get via JSON
                    content = f"Title: {title}\nDate: {pub_date}\nSource: {source}\n(Abstract not retrieved)"

                    results.append({
                        "title": title,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                        "content": content
                    })

            return results

        except Exception as e:
            print(f"Error accessing PubMed: {e}")
            return []

    def search_pubmed(self, pubmed_api_url, query: str) -> str:
        """Legacy search returning links."""
        # This might be broken if pubmed_api_url is now base_url
        # But we are using search_raw in new flow.
        return "Use search_pubmed_raw"
