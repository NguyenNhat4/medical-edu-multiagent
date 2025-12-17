import logging
from typing import Dict, Any
from pocketflow import Node
from utils.call_llm import call_llm

class QueryExpanderNode(Node):
    """
    Node for expanding user queries with medical terminology to improve retrieval.
    """
    def __init__(self, config=None, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.config = config

    def prep(self, shared):
        """Read query from shared store."""
        return shared.get("query", "")

    def exec(self, original_query):
        """
        Expand the original query with relevant medical terms.

        Args:
            original_query: The user's original query

        Returns:
            Expanded query string
        """
        self.logger.info(f"Expanding query: {original_query}")

        prompt = f"""
        As a medical expert, expand the following query with relevant medical terminology,
        synonyms, and related concepts that would help in retrieving relevant medical information:

        User Query: {original_query}

        Expand the query only if you feel like it is required, otherwise keep the user query intact.
        Be specific to the medical or any other domain mentioned in the user query, do not add other medical domains.
        If the user query asks about answering in tabular format, include that in the expanded query and do not answer in tabular format yourself.
        Provide only the expanded query without explanations.
        """

        expanded_query = call_llm(prompt)

        return expanded_query

    def post(self, shared, prep_res, exec_res):
        """
        Store both original and expanded queries in shared store.

        Args:
            shared: Shared data store
            prep_res: Original query from prep
            exec_res: Expanded query from exec

        Returns:
            Action string
        """
        shared["original_query"] = prep_res
        shared["expanded_query"] = exec_res
        # Update the query with expanded version for downstream nodes
        shared["query"] = exec_res

        self.logger.info(f"   Original: '{prep_res}'")
        self.logger.info(f"   Expanded: '{exec_res}'")

        return "default"
