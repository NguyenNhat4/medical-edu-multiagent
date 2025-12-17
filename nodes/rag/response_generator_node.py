import logging
from typing import List, Dict, Any, Optional
from pocketflow import Node
from utils.call_llm import call_llm

class ResponseGeneratorNode(Node):
    """
    Node for generating responses based on retrieved context and user query.
    """
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.include_sources = getattr(config.rag, "include_sources", True)

    def prep(self, shared):
        """
        Read query, retrieved documents, picture paths, and chat history from shared store.

        Returns:
            Tuple of (query, retrieved_docs, picture_paths, chat_history)
        """
        query = shared.get("query", "")
        # Try reranked documents first, fall back to retrieved documents
        retrieved_docs = shared.get("reranked_documents") or shared.get("retrieved_documents", [])
        picture_paths = shared.get("picture_paths", [])
        chat_history = shared.get("chat_history", None)

        return (query, retrieved_docs, picture_paths, chat_history)

    def exec(self, prep_res):
        """
        Generate a response based on retrieved documents.

        Args:
            prep_res: Tuple of (query, retrieved_docs, picture_paths, chat_history)

        Returns:
            Dict containing response text, sources, and confidence
        """
        query, retrieved_docs, picture_paths, chat_history = prep_res

        # Extract content from documents for context
        doc_texts = [doc["content"] for doc in retrieved_docs]

        # Combine retrieved documents into a single context
        context = "\n\n===DOCUMENT SECTION===\n\n".join(doc_texts)

        # Build the prompt
        prompt = self._build_prompt(query, context, chat_history)

        # Generate response
        response_text = call_llm(prompt)

        # Extract sources for citation
        sources = self._extract_sources(retrieved_docs) if self.include_sources else []

        # Calculate confidence
        confidence = self._calculate_confidence(retrieved_docs)

        # Add sources to response
        if self.include_sources:
            response_with_source = response_text + "\n\n##### Source documents:"
            for current_source in sources:
                source_path = current_source['path']
                source_title = current_source['title']
                response_with_source += f"\n- [{source_title}]({source_path})"
        else:
            response_with_source = response_text

        # Add picture paths to response
        response_with_source_and_picture_paths = response_with_source + "\n\n##### Reference images:"
        for picture_path in picture_paths:
            response_with_source_and_picture_paths += f"\n- [{picture_path.split('/')[-1]}]({picture_path})"

        # Format final response
        result = {
            "response": response_with_source_and_picture_paths,
            "sources": sources,
            "confidence": confidence
        }

        return result

    def exec_fallback(self, prep_res, exc):
        """
        Return error message if response generation fails.

        Args:
            prep_res: Prep result (not used)
            exc: Exception that occurred

        Returns:
            Error response dict
        """
        self.logger.error(f"Error generating response: {exc}")
        return {
            "response": "I apologize, but I encountered an error while generating a response. Please try rephrasing your question.",
            "sources": [],
            "confidence": 0.0
        }

    def post(self, shared, prep_res, exec_res):
        """
        Store response in shared store.

        Args:
            shared: Shared data store
            prep_res: Prep result (not used)
            exec_res: Response dict from exec

        Returns:
            Action string
        """
        shared["rag_response"] = exec_res
        return "default"

    def _build_prompt(
            self,
            query: str,
            context: str,
            chat_history: Optional[List[Dict[str, str]]] = None
        ) -> str:
        """
        Build the prompt for the language model.

        Args:
            query: User query
            context: Formatted context from retrieved documents
            chat_history: Optional chat history

        Returns:
            Complete prompt string
        """
        table_instructions = """
        Some of the retrieved information is presented in table format. When using information from tables:
        1. Present tabular data using proper markdown table formatting with headers, like this:
            | Column1 | Column2 | Column3 |
            |---------|---------|---------|
            | Value1  | Value2  | Value3  |
        2. Re-format the table structure to make it easier to read and understand
        3. If any new component is introduced during re-formatting of the table, mention it explicitly
        4. Clearly interpret the tabular data in your response
        5. Reference the relevant table when presenting specific data points
        6. If appropriate, summarize trends or patterns shown in the tables
        7. If only reference numbers are mentioned and you can fetch the corresponding values like research paper title or authors from the context, replace the reference numbers with the actual values
        """

        response_format_instructions = """Instructions:
        1. Answer the query based ONLY on the information provided in the context.
        2. If the context doesn't contain relevant information to answer the query, state: "I don't have enough information to answer this question based on the provided context."
        3. Do not use prior knowledge not contained in the context.
        5. Be concise and accurate.
        6. Provide a well-structured response with heading, sub-headings and tabular structure if required in markdown format based on retrieved knowledge. Keep the headings and sub-headings small sized.
        7. Only provide sections that are meaningful to have in a chatbot reply. For example, do not explicitly mention references.
        8. If values are involved, make sure to respond with perfect values present in context. Do not make up values.
        9. Do not repeat the question in the answer or response."""

        # Build the prompt
        prompt = f"""You are a medical assistant providing accurate information based on verified medical sources.

        Here are the last few messages from our conversation:

        {chat_history}

        The user has asked the following question:
        {query}

        I've retrieved the following information to help answer this question:

        {context}

        {table_instructions}

        {response_format_instructions}

        Based on the provided information, please answer the user's question thoroughly but concisely.
        If the information doesn't contain the answer, acknowledge the limitations of the available information.

        Do not provide any source link that is not present in the context. Do not make up any source link.

        Medical Assistant Response:"""

        return prompt

    def _extract_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract source information from retrieved documents for citation.

        Args:
            documents: List of retrieved document dictionaries

        Returns:
            List of source information dictionaries
        """
        sources = []
        seen_sources = set()

        for doc in documents:
            source = doc.get("source")
            source_path = doc.get("source_path")

            if not source:
                continue

            source_id = f"{source}|{source_path}"

            if source_id in seen_sources:
                continue

            source_info = {
                "title": source,
                "path": source_path,
                "score": doc.get("combined_score", doc.get("rerank_score", doc.get("score", 0.0)))
            }

            sources.append(source_info)
            seen_sources.add(source_id)

        # Sort sources by score
        sources.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Format the final sources list
        formatted_sources = []
        for source in sources:
            formatted_source = {
                "title": source["title"],
                "path": source["path"]
            }
            formatted_sources.append(formatted_source)

        return formatted_sources

    def _calculate_confidence(self, documents: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score based on retrieved documents.

        Args:
            documents: Retrieved documents

        Returns:
            Confidence score between 0 and 1
        """
        if not documents:
            return 0.0

        # Use combined score if available, otherwise use original score
        if "combined_score" in documents[0]:
            scores = [doc.get("combined_score", 0) for doc in documents[:3]]
        elif "rerank_score" in documents[0]:
            scores = [doc.get("rerank_score", 0) for doc in documents[:3]]
        else:
            scores = [doc.get("score", 0) for doc in documents[:3]]

        # Average of top 3 document scores
        return sum(scores) / len(scores) if scores else 0.0
