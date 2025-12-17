import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
from pocketflow import Node
from sentence_transformers import CrossEncoder

class RerankerNode(Node):
    """
    Node for reranking retrieved documents using a cross-encoder model.
    """
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

        # Load the cross-encoder model for reranking
        try:
            self.model_name = config.rag.reranker_model
            self.logger.info(f"Loading reranker model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            self.top_k = config.rag.reranker_top_k
            self.parsed_content_dir = config.rag.parsed_content_dir
        except Exception as e:
            self.logger.error(f"Error loading reranker model: {e}")
            raise

    def prep(self, shared):
        """
        Read query and retrieved documents from shared store.

        Returns:
            Tuple of (query, documents)
        """
        query = shared.get("query", "")
        documents = shared.get("retrieved_documents", [])
        return (query, documents)

    def exec(self, prep_res):
        """
        Rerank documents based on query relevance using cross-encoder.

        Args:
            prep_res: Tuple of (query, documents)

        Returns:
            Tuple of (reranked_documents, picture_reference_paths)
        """
        query, documents = prep_res

        if not documents:
            return ([], [])

        # Ensure documents have consistent structure
        if isinstance(documents[0], str):
            # Convert simple strings to dictionaries
            docs_list = []
            for i, doc_text in enumerate(documents):
                docs_list.append({
                    "id": i,
                    "content": doc_text,
                    "score": 1.0
                })
            documents = docs_list
        elif isinstance(documents[0], dict):
            # Ensure all required fields exist
            for i, doc in enumerate(documents):
                if "id" not in doc:
                    doc["id"] = i
                if "score" not in doc:
                    doc["score"] = 1.0
                if "content" not in doc:
                    if "text" in doc:
                        doc["content"] = doc["text"]
                    else:
                        doc["content"] = f"Document {i}"

        # Create query-document pairs for scoring
        pairs = [(query, doc["content"]) for doc in documents]

        # Get relevance scores
        scores = self.model.predict(pairs)

        # Add scores to documents
        for i, score in enumerate(scores):
            documents[i]["rerank_score"] = float(score)
            if "score" not in documents[i]:
                documents[i]["score"] = 1.0
            # Combine (average) the original score and rerank score
            documents[i]["combined_score"] = (documents[i]["score"] + float(score)) / 2

        # Sort by combined score
        reranked_docs = sorted(documents, key=lambda x: x["combined_score"], reverse=True)

        # Limit to top_k if needed
        if self.top_k and len(reranked_docs) > self.top_k:
            reranked_docs = reranked_docs[:self.top_k]

        # Extract picture references
        picture_reference_paths = []
        for doc in reranked_docs:
            matches = re.finditer(r"picture_counter_(\d+)", doc["content"])
            for match in matches:
                counter_value = int(match.group(1))
                doc_basename = os.path.splitext(doc['source'])[0]
                picture_path = os.path.join("http://localhost:8000/", self.parsed_content_dir + "/" + f"{doc_basename}-picture-{counter_value}.png")
                picture_reference_paths.append(picture_path)

        return (reranked_docs, picture_reference_paths)

    def exec_fallback(self, prep_res, exc):
        """
        Fallback to original ranking if reranking fails.

        Args:
            prep_res: Tuple of (query, documents)
            exc: Exception that occurred

        Returns:
            Tuple of (original_documents, empty_picture_paths)
        """
        self.logger.error(f"Error during reranking: {exc}")
        self.logger.warning("Falling back to original ranking")
        query, documents = prep_res
        return (documents, [])

    def post(self, shared, prep_res, exec_res):
        """
        Store reranked documents and picture paths in shared store.

        Args:
            shared: Shared data store
            prep_res: Prep result (not used)
            exec_res: Tuple of (reranked_documents, picture_paths)

        Returns:
            Action string
        """
        reranked_docs, picture_paths = exec_res

        shared["reranked_documents"] = reranked_docs
        shared["picture_paths"] = picture_paths

        self.logger.info(f"Reranked retrieved documents and chose top {len(reranked_docs)}")
        self.logger.info(f"Found {len(picture_paths)} referenced images")

        return "default"
