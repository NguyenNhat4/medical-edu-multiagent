import requests
import os
from typing import Optional, List, Dict, Any

class TavilySearchAgent:
    """
    Processes general documents for the RAG system with context-aware chunking.
    """
    def __init__(self):
        """
        Initialize the Tavily search agent.
        """
        pass

    def search_tavily_raw(self, query: str) -> List[Dict[str, Any]]:
        """Perform a general web search using Tavily API and return list of results."""
        tavily_api_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_api_key:
            print("Error: TAVILY_API_KEY not found in environment variables.")
            return []

        # Strip any surrounding quotes from the query for robustness
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

            return data.get("results", [])
        except Exception as e:
            print(f"Error retrieving web search results: {e}")
            return []

    def search_tavily(self, query: str) -> str:
        """Perform a general web search using Tavily API and return formatted string."""
        results = self.search_tavily_raw(query)
        if results:
            return "\n".join(["title: " + str(res.get("title", "")) + " - " +
                              "url: " + str(res.get("url", "")) + " - " +
                              "content: " + str(res.get("content", "")) + " - " +
                              "score: " + str(res.get("score", "")) for res in results])
        return "No relevant results found."
