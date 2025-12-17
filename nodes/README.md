# Nodes Directory

This directory contains refactored components following the PocketFlow Node pattern. Each node class represents a single, well-defined task in the medical education multiagent system.

## Architecture Pattern

All nodes follow the PocketFlow framework pattern with three main methods:

### Node Structure
```python
class MyNode(Node):
    def prep(self, shared):
        """Read data from shared store and prepare for execution"""
        return data_for_exec

    def exec(self, prep_res):
        """Execute the main logic (LLM calls, API calls, computations)"""
        return result

    def post(self, shared, prep_res, exec_res):
        """Write results back to shared store and return action"""
        shared["result_key"] = exec_res
        return "default"  # or other action for flow control
```

### Key Principles

1. **Separation of Concerns**: Data operations (prep/post) are separate from compute logic (exec)
2. **Retry Mechanism**: Only `exec()` is retried on failure, controlled by `max_retries` and `wait` parameters
3. **Shared Store**: Communication between nodes via a shared dictionary
4. **Actions**: `post()` returns action strings to control flow transitions
5. **Batch Processing**: Use `BatchNode` for processing lists of items in parallel

## Node Categories

### Document Processing Nodes

#### `DocParserNode`
- **Purpose**: Parse medical documents using docling
- **Input**: `document_path`, `parsed_content_dir` from shared
- **Output**: `parsed_document`, `images` to shared
- **Type**: Regular Node

#### `ImageSummarizerNode`
- **Purpose**: Summarize extracted images using LLM
- **Input**: `images` from shared
- **Output**: `image_summaries` to shared
- **Type**: BatchNode (processes images in parallel)

#### `DocumentFormatterNode`
- **Purpose**: Format document by replacing image placeholders with summaries
- **Input**: `parsed_document`, `image_summaries` from shared
- **Output**: `formatted_document` to shared
- **Type**: Regular Node

#### `DocumentChunkerNode`
- **Purpose**: Split document into semantic chunks using LLM
- **Input**: `formatted_document` from shared
- **Output**: `document_chunks` to shared
- **Type**: Regular Node

### Vector Store Nodes

#### `VectorStoreIngestNode`
- **Purpose**: Ingest document chunks into Qdrant vector store
- **Input**: `document_chunks`, `document_path` from shared
- **Output**: Upserts to Qdrant collection
- **Type**: Regular Node
- **Features**: Hybrid search (Dense + Sparse + ColBERT)

#### `VectorStoreRetrievalNode`
- **Purpose**: Retrieve relevant chunks from vector store
- **Input**: `query` from shared
- **Output**: `retrieved_documents` to shared
- **Type**: Regular Node
- **Features**: Hybrid search with late interaction reranking

### RAG Nodes

#### `QueryExpanderNode`
- **Purpose**: Expand user queries with medical terminology
- **Input**: `query` from shared
- **Output**: `expanded_query`, updates `query` in shared
- **Type**: Regular Node

#### `RerankerNode`
- **Purpose**: Rerank retrieved documents using cross-encoder
- **Input**: `query`, `retrieved_documents` from shared
- **Output**: `reranked_documents`, `picture_paths` to shared
- **Type**: Regular Node
- **Features**: Combines retrieval score with rerank score

#### `ResponseGeneratorNode`
- **Purpose**: Generate final response based on context
- **Input**: `query`, `reranked_documents` or `retrieved_documents`, `picture_paths`, `chat_history` from shared
- **Output**: `rag_response` (with response, sources, confidence) to shared
- **Type**: Regular Node

### Web Search Nodes

#### `WebSearchQueryFormatterNode`
- **Purpose**: Format search query from user query and chat history
- **Input**: `query`, `chat_history` from shared
- **Output**: `search_query` to shared
- **Type**: Regular Node

#### `TavilySearchNode`
- **Purpose**: Search web using Tavily API
- **Input**: `search_query` from shared
- **Output**: `tavily_results`, `tavily_results_str` to shared
- **Type**: Regular Node

#### `PubmedSearchNode`
- **Purpose**: Search PubMed medical database
- **Input**: `search_query` from shared
- **Output**: `pubmed_results` to shared
- **Type**: Regular Node

#### `WebSearchAggregatorNode`
- **Purpose**: Aggregate results from multiple search sources
- **Input**: `tavily_results`, `pubmed_results` from shared
- **Output**: `web_search_results`, `web_search_results_raw` to shared
- **Type**: Regular Node

#### `WebSearchResponseNode`
- **Purpose**: Generate response from web search results
- **Input**: `query`, `web_search_results` from shared
- **Output**: `web_search_response` to shared
- **Type**: Regular Node

## Example Usage

### Document Ingestion Flow
```python
from pocketflow import Flow
from nodes import (
    DocParserNode,
    ImageSummarizerNode,
    DocumentFormatterNode,
    DocumentChunkerNode,
    VectorStoreIngestNode
)

# Create nodes
doc_parser = DocParserNode()
image_summarizer = ImageSummarizerNode()
doc_formatter = DocumentFormatterNode()
doc_chunker = DocumentChunkerNode()
vector_ingest = VectorStoreIngestNode(config)

# Connect nodes
doc_parser >> image_summarizer >> doc_formatter >> doc_chunker >> vector_ingest

# Create flow
ingestion_flow = Flow(start=doc_parser)

# Run flow
shared = {
    "document_path": "path/to/document.pdf",
    "parsed_content_dir": "parsed_content"
}
ingestion_flow.run(shared)
```

### Query Processing Flow
```python
from pocketflow import Flow
from nodes import (
    QueryExpanderNode,
    VectorStoreRetrievalNode,
    RerankerNode,
    ResponseGeneratorNode
)

# Create nodes
query_expander = QueryExpanderNode(config)
retrieval = VectorStoreRetrievalNode(config)
reranker = RerankerNode(config)
response_gen = ResponseGeneratorNode(config)

# Connect nodes
query_expander >> retrieval >> reranker >> response_gen

# Create flow
query_flow = Flow(start=query_expander)

# Run flow
shared = {
    "query": "What are the symptoms of diabetes?",
    "chat_history": []
}
query_flow.run(shared)
print(shared["rag_response"]["response"])
```

### Web Search Flow
```python
from pocketflow import Flow
from nodes import (
    WebSearchQueryFormatterNode,
    TavilySearchNode,
    PubmedSearchNode,
    WebSearchAggregatorNode,
    WebSearchResponseNode
)

# Create nodes
query_formatter = WebSearchQueryFormatterNode()
tavily_search = TavilySearchNode()
pubmed_search = PubmedSearchNode(config)
aggregator = WebSearchAggregatorNode()
response_node = WebSearchResponseNode()

# Connect nodes - parallel search then aggregate
query_formatter >> tavily_search >> aggregator
query_formatter >> pubmed_search >> aggregator
aggregator >> response_node

# Create flow
web_search_flow = Flow(start=query_formatter)

# Run flow
shared = {
    "query": "Latest research on COVID-19 treatments",
    "chat_history": None
}
web_search_flow.run(shared)
print(shared["web_search_response"])
```

## Migration Guide

### From Old Structure to Nodes

**Old (Agent-based):**
```python
from rag_agent import MedicalRAG

rag = MedicalRAG(config)
result = rag.process_query(query, chat_history)
```

**New (Node-based):**
```python
from pocketflow import Flow
from nodes import QueryExpanderNode, VectorStoreRetrievalNode, RerankerNode, ResponseGeneratorNode

# Build flow once
query_expander = QueryExpanderNode(config)
retrieval = VectorStoreRetrievalNode(config)
reranker = RerankerNode(config)
response_gen = ResponseGeneratorNode(config)

query_expander >> retrieval >> reranker >> response_gen
rag_flow = Flow(start=query_expander)

# Use flow multiple times
shared = {"query": query, "chat_history": chat_history}
rag_flow.run(shared)
result = shared["rag_response"]
```

## Benefits of Node-Based Architecture

1. **Modularity**: Each component is independent and reusable
2. **Testability**: Individual nodes can be tested in isolation
3. **Flexibility**: Easy to swap, add, or remove nodes
4. **Error Handling**: Built-in retry mechanism for each exec() method
5. **Flow Control**: Actions enable conditional branching and loops
6. **Observability**: Clear separation makes debugging easier
7. **Scalability**: BatchNodes enable parallel processing

## Configuration Requirements

Nodes require a config object with the following structure:

```python
config.rag.collection_name         # Qdrant collection name
config.rag.embedding_dim           # Embedding dimension
config.rag.top_k                   # Number of documents to retrieve
config.rag.reranker_top_k          # Number of reranked documents
config.rag.reranker_model          # Reranker model name
config.rag.parsed_content_dir      # Directory for parsed content
config.rag.include_sources         # Whether to include sources

config.web_search.pubmed_base_url  # PubMed API base URL
```

## Best Practices

1. **Keep exec() pure**: Only computation, no shared store access
2. **Handle errors in exec()**: Let Node retry mechanism work
3. **Use descriptive keys**: Name shared store keys clearly
4. **Document shared keys**: Comment what each node reads/writes
5. **Batch when possible**: Use BatchNode for list processing
6. **Chain wisely**: Keep flows focused on single responsibilities
