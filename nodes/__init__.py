# Nodes for Medical Education Multiagent System

# Interview nodes
from .interview import InterviewerNode, PlannerNode

# Research nodes
from .research import (
    ResearcherNode,
    ContentAggregatorNode,
    PubmedSearchNode,
    TavilySearchNode,
    WebSearchQueryFormatterNode,
    WebSearchAggregatorNode,
    WebSearchResponseNode
)

# RAG nodes - import with error handling for optional dependencies
try:
    from .rag import (
        DocParserNode,
        ImageSummarizerNode,
        DocumentFormatterNode,
        DocumentChunkerNode,
        VectorStoreIngestNode,
        VectorStoreRetrievalNode,
        QueryExpanderNode,
        RerankerNode,
        ResponseGeneratorNode
    )
    _rag_available = True
except ImportError as e:
    _rag_available = False
    print(f"Warning: RAG nodes not available due to missing dependencies: {e}")
    # Create placeholder classes
    class DocParserNode: pass
    class ImageSummarizerNode: pass
    class DocumentFormatterNode: pass
    class DocumentChunkerNode: pass
    class VectorStoreIngestNode: pass
    class VectorStoreRetrievalNode: pass
    class QueryExpanderNode: pass
    class RerankerNode: pass
    class ResponseGeneratorNode: pass

# Generation nodes
from .generation import (
    QueryGeneratorNode,
    ContentWriterNode,
    DocumentGeneratorNode
)

# MCP nodes
from .mcp import (
    GetToolsNode,
    DecideToolNode,
    ExecuteToolNode
)

# Legacy imports (kept for backward compatibility)
try:
    from .doc_parser_node import DocParserNode as _DocParserNodeLegacy
    from .content_processor_node import ContentProcessorNode
    from .vectorstore_node import VectorStoreNode
except ImportError:
    pass  # These are optional legacy imports

# Aliases for app.py compatibility (old naming convention)
DocGeneratorNode = DocumentGeneratorNode  # app.py uses DocGeneratorNode

__all__ = [
    # Interview
    'InterviewerNode',
    'PlannerNode',

    # Research
    'ResearcherNode',
    'ContentAggregatorNode',
    'PubmedSearchNode',
    'TavilySearchNode',
    'WebSearchQueryFormatterNode',
    'WebSearchAggregatorNode',
    'WebSearchResponseNode',

    # RAG
    'DocParserNode',
    'ImageSummarizerNode',
    'DocumentFormatterNode',
    'DocumentChunkerNode',
    'VectorStoreIngestNode',
    'VectorStoreRetrievalNode',
    'QueryExpanderNode',
    'RerankerNode',
    'ResponseGeneratorNode',

    # Generation
    'QueryGeneratorNode',
    'ContentWriterNode',
    'DocumentGeneratorNode',
    'DocGeneratorNode',  # Alias for backward compatibility

    # MCP
    'GetToolsNode',
    'DecideToolNode',
    'ExecuteToolNode',

    # Legacy (for backward compatibility)
    'ContentProcessorNode',
    'VectorStoreNode'
]
