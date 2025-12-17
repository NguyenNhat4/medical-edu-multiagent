"""
Educational Content Generation Flow

Complete workflow for generating educational medical content:
1. Interview user for requirements
2. Create content blueprint/plan
3. Research content from PubMed and web sources
4. Ingest research into RAG vector store
5. Generate queries for each blueprint section
6. Retrieve relevant context for each section
7. Write content using RAG-enhanced generation
8. Generate final Word document

This demonstrates the full RAG pattern:
- Research → Chunk → Embed → Store (Qdrant)
- Query → Retrieve → Rerank → Generate
"""

import logging
from pocketflow import AsyncFlow
from nodes import (
    InterviewerNode,
    PlannerNode,
    ResearcherNode,
    QueryGeneratorNode,
    ContentWriterNode,
    DocumentGeneratorNode
)


def create_educational_content_flow():
    """
    Create the complete educational content generation flow.

    Returns:
        AsyncFlow: Configured flow ready to run
    """
    logger = logging.getLogger(__name__)

    # === Phase 1: Interview & Planning ===
    interviewer = InterviewerNode()
    planner = PlannerNode()

    # === Phase 2: Research & RAG Ingestion ===
    researcher = ResearcherNode()  # Async batch node

    # === Phase 3: Content Generation ===
    query_generator = QueryGeneratorNode()  # Batch node
    content_writer = ContentWriterNode()  # Async batch node
    doc_generator = DocumentGeneratorNode()

    # === Connect the Flow ===

    # Interview until requirements complete
    interviewer - "ask" >> interviewer  # Loop if more info needed
    interviewer - "done" >> planner     # Proceed when done

    # Planning (can refine if needed)
    planner >> researcher

    # Research for all blueprint items (parallel)
    researcher >> query_generator

    # Generate queries and write content (parallel)
    query_generator >> content_writer

    # Generate final document
    content_writer >> doc_generator

    # Create flow starting with interviewer
    flow = AsyncFlow(start=interviewer)

    logger.info("Educational content flow created successfully")
    return flow


def create_simple_content_flow():
    """
    Create a simplified flow that skips interviewer (for testing).

    Assumes requirements and blueprint are already in shared store.

    Returns:
        AsyncFlow: Configured flow ready to run
    """
    logger = logging.getLogger(__name__)

    # === Research & Generation Only ===
    researcher = ResearcherNode()
    query_generator = QueryGeneratorNode()
    content_writer = ContentWriterNode()
    doc_generator = DocumentGeneratorNode()

    # Connect in sequence
    researcher >> query_generator >> content_writer >> doc_generator

    flow = AsyncFlow(start=researcher)

    logger.info("Simple content flow created (no interview)")
    return flow


def create_research_only_flow():
    """
    Create a flow that only does research and RAG ingestion.

    Useful for building up knowledge base before generation.

    Returns:
        AsyncFlow: Configured flow ready to run
    """
    logger = logging.getLogger(__name__)

    researcher = ResearcherNode()

    flow = AsyncFlow(start=researcher)

    logger.info("Research-only flow created")
    return flow


async def run_educational_flow_example():
    """
    Example of how to run the educational content flow.

    Note: This is a demonstration. Actual usage should provide:
    - rag_agent instance
    - web_search_agent instance
    """
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*70)
    print("EDUCATIONAL CONTENT GENERATION FLOW - Example")
    print("="*70 + "\n")

    # Shared store with pre-populated requirements (skipping interview for demo)
    shared = {
        "requirements": {
            "topic": "Diabetes Management",
            "audience": "Medical Students (3rd year)",
            "objectives": "Understand diagnosis, treatment protocols, and patient management"
        },
        "blueprint": [
            {
                "title": "Introduction to Diabetes",
                "description": "Overview of diabetes types, prevalence, and pathophysiology"
            },
            {
                "title": "Diagnosis and Testing",
                "description": "Diagnostic criteria, laboratory tests, and screening guidelines"
            },
            {
                "title": "Treatment Protocols",
                "description": "Evidence-based treatment approaches for Type 1 and Type 2 diabetes"
            }
        ],
        # These would normally be injected
        "rag_agent": None,  # Replace with actual RAG agent
        "web_search_agent": None  # Replace with actual web search agent
    }

    print("Requirements:")
    print(f"  Topic: {shared['requirements']['topic']}")
    print(f"  Audience: {shared['requirements']['audience']}")
    print(f"\nBlueprint ({len(shared['blueprint'])} sections):")
    for idx, section in enumerate(shared['blueprint'], 1):
        print(f"  {idx}. {section['title']}")

    print("\n" + "-"*70)
    print("Flow would execute:")
    print("  1. Research each blueprint item (PubMed + Web)")
    print("  2. Ingest research into Qdrant vector store")
    print("  3. Generate targeted queries")
    print("  4. Retrieve relevant chunks for each section")
    print("  5. Write content using RAG context")
    print("  6. Generate final Word document")
    print("-"*70)

    print("\nNote: Full execution requires:")
    print("  - RAG agent with Qdrant connection")
    print("  - Web search agent (PubMed + Tavily)")
    print("  - MCP document tools")
    print("\nUse with actual agents for full functionality.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_educational_flow_example())
