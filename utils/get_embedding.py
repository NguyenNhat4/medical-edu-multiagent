from fastembed import TextEmbedding, LateInteractionTextEmbedding, SparseTextEmbedding
from typing import List, Union, Any, Tuple
import os
import numpy as np
from utils.app_config import AppConfig

config = AppConfig()

class EmbeddingModels:
    """Container for embedding models with lazy loading and cache support."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingModels, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.dense_model = None
        self.sparse_model = None
        self.late_interaction_model = None
        self.cache_dir = config.rag.fastembed_cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.load()
        self.initialized = True

    def load(self):
        """Load all embedding models from cache directory."""
        print(f"Loading embedding models from cache: {self.cache_dir}")

        print(f"  - Dense model: {config.rag.dense_model_name}")
        self.dense_model = TextEmbedding(
            config.rag.dense_model_name,
            cache_dir=self.cache_dir
        )

        print(f"  - Sparse model: {config.rag.sparse_model_name}")
        self.sparse_model = SparseTextEmbedding(
            config.rag.sparse_model_name,
            cache_dir=self.cache_dir
        )

        print(f"  - Late interaction model: {config.rag.late_interaction_model_name}")
        self.late_interaction_model = LateInteractionTextEmbedding(
            config.rag.late_interaction_model_name,
            cache_dir=self.cache_dir
        )

        print("All models loaded from cache successfully.\n")

# Global instance
_models = None

def get_models():
    global _models
    if _models is None:
        _models = EmbeddingModels()
    return _models

def get_embedding(content: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """
    Get dense embedding for backward compatibility.
    """
    models = get_models()
    is_single = isinstance(content, str)
    contents = [content] if is_single else content

    # TextEmbedding.embed returns generator of numpy arrays
    embeddings = list(models.dense_model.embed(contents))

    # Convert numpy to list
    embeddings = [e.tolist() for e in embeddings]

    return embeddings[0] if is_single else embeddings

def get_all_embeddings(content: List[str]) -> Tuple[List[Any], List[Any], List[Any]]:
    """
    Get all three types of embeddings for a list of strings.
    Returns: (dense_embeddings, sparse_embeddings, late_interaction_embeddings)
    """
    models = get_models()

    dense = list(models.dense_model.embed(content))
    dense = [e.tolist() for e in dense]

    sparse = list(models.sparse_model.embed(content))
    # Sparse embeddings are objects (SparseEmbedding) with .indices and .values

    late = list(models.late_interaction_model.embed(content))
    # Late embeddings are numpy arrays (tokens, 128)

    return dense, sparse, late
