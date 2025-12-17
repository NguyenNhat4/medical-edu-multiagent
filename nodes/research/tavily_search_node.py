import os
import requests
import logging
from typing import List, Dict, Any
from pocketflow import Node

class TavilySearchNode(Node):
    """
    Node for performing general web search using Tavily API.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read search query from shared store.

        Returns:
            Search query string
        """
        return shared.get("search_query", "")

    def exec(self, query):
        """
        Perform a general web search using Tavily API.

        Args:
            query: Search query string

        Returns:
            List of search result dictionaries
        """
        tavily_api_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_api_key:
            self.logger.error("TAVILY_API_KEY not found in environment variables")
            return []

        # Strip any surrounding quotes
        query = query.strip('"\'')

        url = "https://api.tavily.com/search"
        params = {
            "api_key": tavily_api_key,
            "query": query,
            "max_results": 5
        }

        try:
            response = requests.post(url, json=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            self.logger.info(f"Tavily search returned {len(results)} results for query: {query}")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving Tavily search results: {e}")
            return []

    def post(self, shared, prep_res, exec_res):
        """
        Store search results in shared store.

        Args:
            shared: Shared data store
            prep_res: Query from prep
            exec_res: Search results list

        Returns:
            Action string
        """
        shared["tavily_results"] = exec_res

        # Also format results as string for backward compatibility
        if exec_res:
            formatted_results = "\n".join([
                "title: " + str(res.get("title", "")) + " - " +
                "url: " + str(res.get("url", "")) + " - " +
                "content: " + str(res.get("content", "")) + " - " +
                "score: " + str(res.get("score", ""))
                for res in exec_res
            ])
            shared["tavily_results_str"] = formatted_results
        else:
            shared["tavily_results_str"] = "No relevant results found."

        return "default"
