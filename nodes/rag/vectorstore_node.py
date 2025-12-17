import os
import logging
from uuid import uuid4
from typing import List, Dict, Any
from pocketflow import Node, BatchNode

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

class VectorStoreIngestNode(Node):
    """
    Node for ingesting document chunks into Qdrant vector store.
    Uses Hybrid Search (Dense + Sparse) and Late Interaction Reranking (ColBERT).
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.client = None # Lazy init

    def prep(self, shared):
        """
        Read config, client, document chunks and metadata from shared store.

        Returns:
            Dict containing necessary context
        """
        config = shared.get("config", {})

        # Get or Initialize Qdrant Client (Shared across nodes)
        if "qdrant_client" not in shared:
             shared["qdrant_client"] = QdrantClient(":memory:")
        self.client = shared["qdrant_client"]

        self.collection_name = config.get("rag", {}).get("collection_name", "medical_docs")
        self.dense_dim = config.get("rag", {}).get("embedding_dim", 384)

        # Model names (as vector names in Qdrant)
        self.dense_vector_name = "all-MiniLM-L6-v2"
        self.sparse_vector_name = "bm25"
        self.colbert_vector_name = "colbertv2.0"

        document_chunks = shared.get("document_chunks", [])
        document_path = shared.get("document_path", "Ingested Text")

        return {
            "chunks": document_chunks,
            "path": document_path
        }

    def exec(self, prep_res):
        """
        Generate embeddings and create vector store points.

        Args:
            prep_res: Dict with context

        Returns:
            List of PointStruct objects ready for ingestion
        """
        document_chunks = prep_res["chunks"]
        document_path = prep_res["path"]

        if not document_chunks:
            return []

        # Check if collection exists, create if it doesn't
        if not self._does_collection_exist():
            self._create_collection()

        # Generate embeddings
        self.logger.info("Generating embeddings (Dense, Sparse, ColBERT)...")
        dense_embs, sparse_embs, late_embs = get_all_embeddings(document_chunks)

        points = []
        self.logger.info("Preparing points for upload...")
        for i, chunk in enumerate(document_chunks):
            doc_id = str(uuid4())

            # Prepare Dense
            dense_vec = dense_embs[i]

            # Prepare Sparse
            sp_obj = sparse_embs[i].as_object()
            sparse_vec = SparseVector(
                indices=sp_obj['indices'].tolist(),
                values=sp_obj['values'].tolist()
            )

            # Prepare ColBERT
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

        return points

    def post(self, shared, prep_res, exec_res):
        """
        Upsert points into Qdrant collection.

        Args:
            shared: Shared data store
            prep_res: Prep result (not used)
            exec_res: List of points from exec

        Returns:
            Action string
        """
        points = exec_res

        if not points:
            self.logger.warning("No points to ingest")
            return "default"

        # Upsert
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            self.logger.info(f"Ingested {len(points)} chunks into {self.collection_name}")
        except Exception as e:
            self.logger.error(f"Error upserting points: {e}")
            raise

        return "default"

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
                    size=128,  # ColBERTv2.0 dimension
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


class VectorStoreRetrievalNode(Node):
    """
    Node for retrieving relevant chunks from Qdrant vector store.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.client = None

    def prep(self, shared):
        """Read query and config from shared store."""
        config = shared.get("config", {})

        if "qdrant_client" not in shared:
             shared["qdrant_client"] = QdrantClient(":memory:")
        self.client = shared["qdrant_client"]

        self.collection_name = config.get("rag", {}).get("collection_name", "medical_docs")
        self.retrieval_top_k = config.get("rag", {}).get("top_k", 5)

        # Model names (as vector names in Qdrant)
        self.dense_vector_name = "all-MiniLM-L6-v2"
        self.sparse_vector_name = "bm25"
        self.colbert_vector_name = "colbertv2.0"

        return shared.get("query", "")

    def exec(self, query):
        """
        Retrieve relevant chunks based on query using Hybrid Search + ColBERT Reranking.

        Args:
            query: Search query string

        Returns:
            List of retrieved documents
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
            prefetch = [
                models.Prefetch(
                    query=dense_vec,
                    using=self.dense_vector_name,
                    limit=self.retrieval_top_k * 2  # Fetch more candidates
                ),
                models.Prefetch(
                    query=sparse_vec,
                    using=self.sparse_vector_name,
                    limit=self.retrieval_top_k * 2
                )
            ]

            # Rerank with ColBERT
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

    def post(self, shared, prep_res, exec_res):
        """
        Store retrieved documents in shared store.

        Args:
            shared: Shared data store
            prep_res: Query from prep
            exec_res: Retrieved documents list

        Returns:
            Action string
        """
        shared["retrieved_documents"] = exec_res
        self.logger.info(f"Retrieved {len(exec_res)} relevant document chunks")
        return "default"


# Legacy wrapper for backward compatibility
class VectorStoreNode(Node):
    """
    Legacy wrapper that combines vectorstore operations.
    For new code, use VectorStoreIngestNode and VectorStoreRetrievalNode separately.
    """
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
