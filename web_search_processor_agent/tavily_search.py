import requests
import os
from typing import Optional

class TavilySearchAgent:
    """
    Processes general documents for the RAG system with context-aware chunking.
    """
    def __init__(self):
        """
        Initialize the Tavily search agent.
        """
        pass

    def search_tavily(self, query: str) -> str:
        """Perform a general web search using Tavily API."""

        tavily_api_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_api_key:
            return "Error: TAVILY_API_KEY not found in environment variables."

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

            results = data.get("results", [])

            if results:
                return "\n".join(["title: " + str(res.get("title", "")) + " - " +
                                  "url: " + str(res.get("url", "")) + " - " +
                                  "content: " + str(res.get("content", "")) + " - " +
                                  "score: " + str(res.get("score", "")) for res in results])
            return "No relevant results found."
        except Exception as e:
            return f"Error retrieving web search results: {e}"
