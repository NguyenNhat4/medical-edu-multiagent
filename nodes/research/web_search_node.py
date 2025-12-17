import logging
from typing import List, Dict, Any, Optional
from pocketflow import Node
from utils.call_llm import call_llm

class WebSearchQueryFormatterNode(Node):
    """
    Node for formatting a web search query based on user query and chat history.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read query and chat history from shared store.

        Returns:
            Tuple of (query, chat_history)
        """
        query = shared.get("query", "")
        chat_history = shared.get("chat_history", None)
        return (query, chat_history)

    def exec(self, prep_res):
        """
        Build a formatted search query using LLM.

        Args:
            prep_res: Tuple of (query, chat_history)

        Returns:
            Formatted search query string
        """
        query, chat_history = prep_res

        prompt = f"""Here are the last few messages from our conversation:

        {chat_history}

        The user asked the following question:

        {query}

        Summarize them into a single, well-formed question only if the past conversation seems relevant to the current query so that it can be used for a web search.
        Keep it concise and ensure it captures the key intent behind the discussion.
        """

        formatted_query = call_llm(prompt)
        self.logger.info(f"Formatted web search query: {formatted_query}")

        return formatted_query

    def post(self, shared, prep_res, exec_res):
        """
        Store formatted search query in shared store.

        Args:
            shared: Shared data store
            prep_res: Prep result
            exec_res: Formatted query

        Returns:
            Action string
        """
        shared["search_query"] = exec_res
        return "default"


class WebSearchAggregatorNode(Node):
    """
    Node for aggregating results from multiple web search sources.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read search results from different sources in shared store.

        Returns:
            List of all search results
        """
        results = []

        # Get Tavily results
        tavily_results = shared.get("tavily_results", [])
        results.extend(tavily_results)

        # Get PubMed results
        pubmed_results = shared.get("pubmed_results", [])
        results.extend(pubmed_results)

        return results

    def exec(self, all_results):
        """
        Aggregate and format search results.

        Args:
            all_results: List of search result dictionaries

        Returns:
            Formatted search results string
        """
        if not all_results:
            return "No relevant results found."

        # Format results as string
        formatted_results = []
        for i, result in enumerate(all_results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")
            score = result.get("score", "")

            formatted_result = f"{i}. Title: {title}\n   URL: {url}\n   Content: {content}"
            if score:
                formatted_result += f"\n   Score: {score}"

            formatted_results.append(formatted_result)

        return "\n\n".join(formatted_results)

    def post(self, shared, prep_res, exec_res):
        """
        Store aggregated results in shared store.

        Args:
            shared: Shared data store
            prep_res: All results from prep
            exec_res: Formatted results string

        Returns:
            Action string
        """
        shared["web_search_results"] = exec_res
        shared["web_search_results_raw"] = prep_res
        return "default"


class WebSearchResponseNode(Node):
    """
    Node for generating a response based on web search results.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read query and web search results from shared store.

        Returns:
            Tuple of (query, web_results)
        """
        query = shared.get("query", "")
        web_results = shared.get("web_search_results", "No results found.")
        return (query, web_results)

    def exec(self, prep_res):
        """
        Generate a response based on web search results using LLM.

        Args:
            prep_res: Tuple of (query, web_results)

        Returns:
            Generated response string
        """
        query, web_results = prep_res

        llm_prompt = (
            "You are an AI assistant specialized in medical information. Below are web search results "
            "retrieved for a user query. Summarize and generate a helpful, concise response. "
            "Use reliable sources only and ensure medical accuracy.\n\n"
            f"Query: {query}\n\nWeb Search Results:\n{web_results}\n\nResponse:"
        )

        response = call_llm(llm_prompt)
        return response

    def post(self, shared, prep_res, exec_res):
        """
        Store web search response in shared store.

        Args:
            shared: Shared data store
            prep_res: Prep result
            exec_res: Generated response

        Returns:
            Action string
        """
        shared["web_search_response"] = exec_res
        return "default"
