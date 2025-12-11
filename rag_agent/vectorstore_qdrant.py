import os
import logging
from uuid import uuid4
from typing import List, Dict, Any, Tuple, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    SparseVectorParams,
    SparseIndexParams,
    SparseVector,
    MultiVectorConfig,
    MultiVectorComparator
)
from utils.get_embedding import get_all_embeddings, get_embedding

class VectorStore:
    """
    Create vector store, ingest documents, retrieve relevant documents using Qdrant (in-memory)
    with Hybrid Search (Dense + Sparse) and Late Interaction Reranking (ColBERT).
    """
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.collection_name = config.rag.collection_name
        self.dense_dim = config.rag.embedding_dim
        self.retrieval_top_k = config.rag.top_k
        self.reranker_top_k = config.rag.reranker_top_k

        # Model names (as vector names in Qdrant)
        self.dense_vector_name = "all-MiniLM-L6-v2"
        self.sparse_vector_name = "bm25"
        self.colbert_vector_name = "colbertv2.0"

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
        """Create a new collection with Dense, Sparse, and Late Interaction vector configs."""
        try:
            vectors_config = {
                self.dense_vector_name: VectorParams(
                    size=self.dense_dim,
                    distance=Distance.COSINE
                ),
                self.colbert_vector_name: VectorParams(
                    size=128, # ColBERTv2.0 dimension
                    distance=Distance.COSINE,
                    multivector_config=MultiVectorConfig(
                        comparator=MultiVectorComparator.MAX_SIM
                    )
                )
            }

            sparse_vectors_config = {
                self.sparse_vector_name: SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=False
                    )
                )
            }

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
            self.logger.info(f"Created new collection: {self.collection_name} with Dense, Sparse, and ColBERT vectors")
        except Exception as e:
            self.logger.error(f"Error creating collection: {e}")
            raise e
            
    def load_vectorstore(self):
        """
        Check if vectorstore is ready.
        For in-memory, this just verifies the collection exists (if created).
        """
        if not self._does_collection_exist():
            self.logger.warning(f"Collection {self.collection_name} does not exist. Please ingest documents first.")
            return None
            
        self.logger.info(f"Vectorstore (in-memory) is ready")
        return None

    def create_vectorstore(
            self,
            document_chunks: List[str],
            document_path: str,
        ) -> None:
        """
        Ingest documents into Qdrant store using all 3 embedding models.
        """
        
        if not document_chunks:
            return

        # Check if collection exists, create if it doesn't
        if not self._does_collection_exist():
            self._create_collection()
        
        # Generate embeddings
        try:
            self.logger.info("Generating embeddings (Dense, Sparse, ColBERT)...")
            dense_embs, sparse_embs, late_embs = get_all_embeddings(document_chunks)
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            return

        points = []
        self.logger.info("Preparing points for upload...")
        for i, chunk in enumerate(document_chunks):
            doc_id = str(uuid4())

            # Prepare Dense
            dense_vec = dense_embs[i]

            # Prepare Sparse
            # sparse_embs[i] is an object with indices and values (numpy arrays)
            sp_obj = sparse_embs[i].as_object()
            sparse_vec = SparseVector(
                indices=sp_obj['indices'].tolist(),
                values=sp_obj['values'].tolist()
            )

            # Prepare ColBERT
            # late_embs[i] is numpy array (N, 128)
            colbert_vec = late_embs[i].tolist()

            payload = {
                "content": chunk,
                "source": os.path.basename(document_path),
                "source_path": os.path.join("http://localhost:8000/", document_path),
                "doc_id": doc_id
            }

            points.append(PointStruct(
                id=doc_id,
                vector={
                    self.dense_vector_name: dense_vec,
                    self.sparse_vector_name: sparse_vec,
                    self.colbert_vector_name: colbert_vec
                },
                payload=payload
            ))

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
        Retrieve relevant chunks based on a query using Hybrid Search + ColBERT Reranking.
        """
        # Generate query embeddings
        try:
            dense_q, sparse_q, late_q = get_all_embeddings([query])

            # Extract single query items
            dense_vec = dense_q[0]

            sp_obj = sparse_q[0].as_object()
            sparse_vec = SparseVector(
                indices=sp_obj['indices'].tolist(),
                values=sp_obj['values'].tolist()
            )

            colbert_vec = late_q[0].tolist()

        except Exception as e:
             self.logger.error(f"Failed to generate query embeddings: {e}")
             return []

        try:
            # Prefetch: Hybrid Search (Dense + Sparse)
            # We want to retrieve candidates that match EITHER Dense OR Sparse
            prefetch = [
                models.Prefetch(
                    query=dense_vec,
                    using=self.dense_vector_name,
                    limit=self.retrieval_top_k * 2 # Fetch more candidates
                ),
                models.Prefetch(
                    query=sparse_vec,
                    using=self.sparse_vector_name,
                    limit=self.retrieval_top_k * 2
                )
            ]

            # Rerank with ColBERT
            # Use query_points with prefetch
            result = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=colbert_vec,
                using=self.colbert_vector_name,
                limit=self.retrieval_top_k,
                with_payload=True
            )

            search_result = result.points

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
