import requests
import logging
from typing import List, Dict, Any
from pocketflow import Node

class PubmedSearchNode(Node):
    """
    Node for searching PubMed medical literature database.
    """
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        # Get PubMed base URL from config if provided
        if config:
            self.base_url = config.web_search.pubmed_base_url
        else:
            self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def prep(self, shared):
        """
        Read search query from shared store.

        Returns:
            Search query string
        """
        return shared.get("search_query", "")

    def exec(self, query):
        """
        Search PubMed and return article summaries.

        Args:
            query: Search query string

        Returns:
            List of PubMed article dictionaries
        """
        base_url = self.base_url
        if not base_url.endswith("/"):
            base_url += "/"

        # 1. Search for IDs
        search_url = base_url + "esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": 20
        }

        try:
            response = requests.get(search_url, params=params)
            data = response.json()
            print("Search Response URL:", response.content)
            article_ids = data.get("esearchresult", {}).get("idlist", [])

            if not article_ids:
                self.logger.info(f"No PubMed articles found for query: {query}")
                return []

            # 2. Fetch Summaries (Metadata)
            summary_url = base_url + "esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(article_ids),
                "retmode": "json"
            }

            summary_response = requests.get(summary_url, params=summary_params)
            print("Summary Response URL:", summary_response)
            summary_data = summary_response.json()

            results = []
            uid_data = summary_data.get("result", {})

            for uid in article_ids:
                if uid in uid_data:
                    item = uid_data[uid]
                    title = item.get("title", "")
                    pub_date = item.get("pubdate", "")
                    source = item.get("source", "")

                    # Construct content from metadata
                    content = f"Title: {title}\nDate: {pub_date}\nSource: {source}\n"

                    results.append({
                        "title": title,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                        "content": content
                    })

            self.logger.info(f"PubMed search returned {len(results)} articles for query: {query}")
            return results

        except Exception as e:
            self.logger.error(f"Error accessing PubMed: {e}")
            return []

    def post(self, shared, prep_res, exec_res):
        """
        Store PubMed search results in shared store.

        Args:
            shared: Shared data store
            prep_res: Query from prep
            exec_res: Search results list

        Returns:
            Action string
        """
        shared["pubmed_results"] = exec_res
        return "default"


def main():
    """
    Test function for PubmedSearchNode.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a test query
    test_query = "COVID-19 currently approved treatments"

    print(f"\n{'='*60}")
    print(f"Testing PubmedSearchNode with query: '{test_query}'")
    print(f"{'='*60}\n")

    # Initialize shared store
    shared = {
        "search_query": test_query
    }

    # Create and run the node
    pubmed_node = PubmedSearchNode()
    action = pubmed_node.run(shared)

    # Display results
    print(f"\nAction returned: {action}")
    print(f"\nNumber of results: {len(shared.get('pubmed_results', []))}")
    print(f"\n{'='*60}")
    print("Search Results:")
    print(f"{'='*60}\n")

    for idx, result in enumerate(shared.get("pubmed_results", []), 1):
        print(f"Result {idx}:")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  Content Preview: {result['content']}...")
        print()


if __name__ == "__main__":
    main()
