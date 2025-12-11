import requests
from typing import Dict, List, Any

from .pubmed_search import PubmedSearchAgent
from .tavily_search import TavilySearchAgent

class WebSearchAgent:
    """
    Agent responsible for retrieving real-time medical information from web sources.
    """
    
    def __init__(self, config):
        self.tavily_search_agent = TavilySearchAgent()
        self.pubmed_search_agent = PubmedSearchAgent()
        self.pubmed_base_url = config.web_search.pubmed_base_url
    
    def search(self, query: str) -> str:
        """
        Perform both general and medical-specific searches.
        """
        tavily_results = self.tavily_search_agent.search_tavily(query=query)
        return f"Tavily Results:\n{tavily_results}\n"

    def search_raw(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform search and return list of results.
        """
        results = []
        # Tavily
        tavily = self.tavily_search_agent.search_tavily_raw(query)
        results.extend(tavily)

        # Pubmed
        pubmed = self.pubmed_search_agent.search_pubmed_raw(self.pubmed_base_url, query)
        results.extend(pubmed)

        return results
