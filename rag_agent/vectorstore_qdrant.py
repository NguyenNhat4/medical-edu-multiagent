import os
import logging
from uuid import uuid4
from typing import List, Dict, Any, Tuple, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from utils.get_embedding import get_embedding

class VectorStore:
    """
    Create vector store, ingest documents, retrieve relevant documents using pure Qdrant (in-memory).
    """
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.collection_name = config.rag.collection_name
        self.embedding_dim = config.rag.embedding_dim
        self.retrieval_top_k = config.rag.top_k

        # In-memory Qdrant client
        self.client = QdrantClient(":memory:")

    def _does_collection_exist(self) -> bool:
        """Check if the collection already exists in Qdrant."""
        try:
            collection_info = self.client.get_collections()
            collection_names = [collection.name for collection in collection_info.collections]
            return self.collection_name in collection_names
        except Exception as e:
            self.logger.error(f"Error checking for collection existence: {e}")
            return False

    def _create_collection(self):
        """Create a new collection with dense vectors."""
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE),
            )
            self.logger.info(f"Created new collection: {self.collection_name}")
        except Exception as e:
            self.logger.error(f"Error creating collection: {e}")
            raise e
            
    def load_vectorstore(self):
        """
        Check if vectorstore is ready.
        For in-memory, this just verifies the collection exists (if created).
        """
        # Check if collection exists
        if not self._does_collection_exist():
            self.logger.warning(f"Collection {self.collection_name} does not exist. Please ingest documents first.")
            # We don't raise error here, just return None, caller handles logic
            return None
            
        self.logger.info(f"Vectorstore (in-memory) is ready")
        return None

    def create_vectorstore(
            self,
            document_chunks: List[str],
            document_path: str,
        ) -> None:
        """
        Ingest documents into Qdrant store.
        
        Args:
            document_chunks: List of document chunks
            document_path: Path to the original document
        """
        
        if not document_chunks:
            return

        # Check if collection exists, create if it doesn't
        if not self._does_collection_exist():
            self._create_collection()
        
        # Generate embeddings
        try:
            embeddings = get_embedding(document_chunks)
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            return

        points = []
        for i, chunk in enumerate(document_chunks):
            doc_id = str(uuid4())
            vector = embeddings[i]

            payload = {
                "content": chunk,
                "source": os.path.basename(document_path),
                "source_path": os.path.join("http://localhost:8000/", document_path),
                "doc_id": doc_id
            }

            points.append(PointStruct(id=doc_id, vector=vector, payload=payload))

        # Upsert
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            self.logger.info(f"Ingested {len(points)} chunks into {self.collection_name}")
        except Exception as e:
            self.logger.error(f"Error upserting points: {e}")

    def retrieve_relevant_chunks(
            self,
            query: str,
            vectorstore: Any = None,
            docstore: Any = None,
        ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks based on a query.
        
        Args:
            query: User query
            
        Returns:
            List of dictionaries with content and score
        """
        # Generate query embedding
        query_vector = get_embedding(query)

        if not query_vector:
             self.logger.error("Failed to generate query embedding")
             return []

        try:
            # Use query_points which is available in newer clients (and :memory: mode)
            # Fallback to search if query_points not available (though it should be for 1.10+)
            if hasattr(self.client, 'query_points'):
                result = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=self.retrieval_top_k
                )
                search_result = result.points
            elif hasattr(self.client, 'search'):
                search_result = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=self.retrieval_top_k
                )
            else:
                self.logger.error("QdrantClient has neither query_points nor search method.")
                return []

        except Exception as e:
            self.logger.error(f"Error searching Qdrant: {e}")
            return []
        
        retrieved_docs = []
        
        for scored_point in search_result:
            payload = scored_point.payload
            doc = {
                "id": scored_point.id,
                "content": payload.get("content"),
                "score": scored_point.score,
                "source": payload.get("source"),
                "source_path": payload.get("source_path")
            }
            retrieved_docs.append(doc)
            
        return retrieved_docs
