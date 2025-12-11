class AppConfig:
    class RAGConfig:
        def __init__(self):
            self.collection_name = "medical_rag"
            # Dense embedding dimension for 'all-MiniLM-L6-v2'
            self.embedding_dim = 384
            self.top_k = 5 # Increased slightly for hybrid search
            self.vector_local_path = ":memory:"
            self.doc_local_path = "output/docstore"
            self.parsed_content_dir = "output/parsed_content"
            self.distance_metric = "cosine"

            # Model Names
            self.dense_model_name = "sentence-transformers/all-MiniLM-L6-v2"
            self.sparse_model_name = "Qdrant/bm25"
            self.late_interaction_model_name = "colbert-ir/colbertv2.0"
            self.fastembed_cache_dir = "fastembed_cache"

            self.include_sources = True
            self.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self.reranker_top_k = 3
            self.reranker_model = "pritamdeka/S-PubMedBert-MS-MARCO"

    class WebSearchConfig:
        def __init__(self):
            self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def __init__(self):
        self.rag = self.RAGConfig()
        self.web_search = self.WebSearchConfig()
