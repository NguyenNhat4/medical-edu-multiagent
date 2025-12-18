from typing import List, Dict, Any, Optional
from .web_search_processor import WebSearchProcessor

class WebSearchProcessorAgent:
    """
    Agent responsible for processing web search results and routing them to the appropriate LLM for response generation.
    """

    def __init__(self, config):
        self.web_search_processor = WebSearchProcessor(config)

    def get_raw_search_results(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetches raw web search results without LLM processing.

        Args:
            query: Search query

        Returns:
            List of search result dictionaries with 'title', 'url', and 'content' keys
        """
        return self.web_search_processor.get_raw_search_results(query)

    def process_web_search_results(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Processes web search results and returns a user-friendly response."""
        return self.web_search_processor.process_web_results(query, chat_history)