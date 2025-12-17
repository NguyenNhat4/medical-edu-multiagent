import logging
from pocketflow import Node


class ContentAggregatorNode(Node):
    """
    Node for aggregating content from multiple research sources.

    Combines results from:
    - PubMed medical literature
    - Web search (Tavily)
    - Other sources

    Formats aggregated content for ingestion into vector store.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read search results from all sources.

        Args:
            shared: Shared data store

        Returns:
            Dict with results from each source
        """
        return {
            "pubmed_results": shared.get("pubmed_results", []),
            "tavily_results": shared.get("tavily_results", []),
            "web_search_results": shared.get("web_search_results_raw", [])
        }

    def exec(self, inputs):
        """
        Aggregate and format content from multiple sources.

        Args:
            inputs: Dict with results from each source

        Returns:
            Dict with aggregated_chunks and source_stats
        """
        pubmed = inputs.get("pubmed_results", [])
        tavily = inputs.get("tavily_results", [])
        web = inputs.get("web_search_results", [])

        aggregated_chunks = []
        source_stats = {
            "pubmed": 0,
            "tavily": 0,
            "web": 0,
            "total": 0
        }

        # Process PubMed results
        for article in pubmed:
            chunk = {
                "source_type": "pubmed",
                "title": article.get("title", "Unknown"),
                "url": article.get("url", ""),
                "content": article.get("content", ""),
                "metadata": {
                    "source": "PubMed Medical Database"
                }
            }
            aggregated_chunks.append(chunk)
            source_stats["pubmed"] += 1

        # Process Tavily results
        for result in tavily:
            chunk = {
                "source_type": "tavily",
                "title": result.get("title", "Unknown"),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "metadata": {
                    "source": "Tavily Web Search",
                    "score": result.get("score", 0)
                }
            }
            aggregated_chunks.append(chunk)
            source_stats["tavily"] += 1

        # Process general web results
        for result in web:
            chunk = {
                "source_type": "web",
                "title": result.get("title", "Unknown"),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "metadata": {
                    "source": "Web Search"
                }
            }
            aggregated_chunks.append(chunk)
            source_stats["web"] += 1

        source_stats["total"] = len(aggregated_chunks)

        self.logger.info(f"Aggregated content from {source_stats['total']} sources")
        self.logger.info(f"  PubMed: {source_stats['pubmed']}")
        self.logger.info(f"  Tavily: {source_stats['tavily']}")
        self.logger.info(f"  Web: {source_stats['web']}")

        return {
            "aggregated_chunks": aggregated_chunks,
            "source_stats": source_stats
        }

    def post(self, shared, prep_res, exec_res):
        """
        Store aggregated content in shared store.

        Args:
            shared: Shared data store
            prep_res: Prepared inputs
            exec_res: Aggregated results

        Returns:
            Action string
        """
        shared["aggregated_content"] = exec_res["aggregated_chunks"]
        shared["content_stats"] = exec_res["source_stats"]

        return "default"


def main():
    """
    Test function for ContentAggregatorNode.
    """
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("Testing ContentAggregatorNode")
    print("="*60 + "\n")

    # Mock search results
    shared = {
        "pubmed_results": [
            {
                "title": "Diabetes Treatment Guidelines 2024",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                "content": "Title: Diabetes Treatment Guidelines 2024\nDate: 2024\nSource: JAMA\nComprehensive guidelines for diabetes management..."
            },
            {
                "title": "Novel Insulin Therapy Approaches",
                "url": "https://pubmed.ncbi.nlm.nih.gov/87654321/",
                "content": "Title: Novel Insulin Therapy Approaches\nDate: 2024\nSource: Diabetes Care\nNew approaches to insulin therapy..."
            }
        ],
        "tavily_results": [
            {
                "title": "ADA Diabetes Guidelines",
                "url": "https://diabetes.org/guidelines",
                "content": "American Diabetes Association guidelines for diabetes care...",
                "score": 0.95
            }
        ],
        "web_search_results_raw": [
            {
                "title": "WHO Diabetes Fact Sheet",
                "url": "https://who.int/diabetes",
                "content": "World Health Organization diabetes information and statistics..."
            }
        ]
    }

    aggregator = ContentAggregatorNode()
    action = aggregator.run(shared)

    print(f"\nAction: {action}")
    print(f"\nSource Statistics:")
    stats = shared.get("content_stats", {})
    print(f"  Total: {stats.get('total', 0)}")
    print(f"  PubMed: {stats.get('pubmed', 0)}")
    print(f"  Tavily: {stats.get('tavily', 0)}")
    print(f"  Web: {stats.get('web', 0)}")

    print(f"\nAggregated Chunks:")
    for idx, chunk in enumerate(shared.get("aggregated_content", []), 1):
        print(f"\n{idx}. [{chunk['source_type']}] {chunk['title']}")
        print(f"   URL: {chunk['url']}")
        print(f"   Content preview: {chunk['content'][:100]}...")


if __name__ == "__main__":
    main()
