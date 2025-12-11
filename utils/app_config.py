class AppConfig:
    class RAGConfig:
        def __init__(self):
            self.collection_name = "medical_rag"
            self.embedding_dim = 768
            self.top_k = 3
            self.vector_local_path = ":memory:"
            self.doc_local_path = "output/docstore"
            self.parsed_content_dir = "output/parsed_content"
            self.distance_metric = "cosine"
            self.embedding_model = "models/text-embedding-004"
            self.include_sources = True
            self.reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self.reranker_top_k = 3

    class WebSearchConfig:
        def __init__(self):
            self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def __init__(self):
        self.rag = self.RAGConfig()
        self.web_search = self.WebSearchConfig()
