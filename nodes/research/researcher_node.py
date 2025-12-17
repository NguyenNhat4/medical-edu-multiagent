import logging
import asyncio
from pocketflow import AsyncParallelBatchNode
from utils.call_llm import call_llm


class ResearcherNode(AsyncParallelBatchNode):
    """
    Node for researching medical content from multiple sources in parallel.

    For each blueprint item:
    1. Generates targeted search query
    2. Searches PubMed and web sources
    3. Aggregates and formats results
    4. Ingests into RAG vector store for later retrieval

    Uses AsyncParallelBatchNode to process multiple blueprint items concurrently.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    async def prep_async(self, shared):
        """
        Read blueprint and research dependencies from shared store.

        Args:
            shared: Shared data store

        Returns:
            List of blueprint items to research
        """
        self.rag_agent = shared.get("rag_agent")
        self.web_search_agent = shared.get("web_search_agent")

        blueprint = shared.get("blueprint", [])
        self.logger.info(f"Preparing to research {len(blueprint)} blueprint items")

        return blueprint

    async def exec_async(self, item):
        """
        Research a single blueprint item.

        Args:
            item: Blueprint item dict with 'title' and 'description'

        Returns:
            Status string describing research results
        """
        if not item:
            return "No item"

        title = item.get('title', 'Unknown')
        description = item.get('description', '')

        self.logger.info(f"Researching: {title}")

        # 1. Generate targeted search query
        prompt = f"""
Generate a specific, high-quality search query to find detailed medical information for the following section of a document.

Section Title: {title}
Description: {description}

Return ONLY the query string, no quotes or extra text.
Focus on medical terminology and evidence-based sources.
"""
        try:
            query = await asyncio.to_thread(call_llm, prompt)
            query = query.strip().strip('"')
            self.logger.info(f"Generated query: {query}")

            # 2. Search multiple sources
            results = []
            if self.web_search_agent:
                results = await asyncio.to_thread(
                    self.web_search_agent.search_raw,
                    query
                )
                self.logger.info(f"Found {len(results)} search results for '{title}'")
            else:
                self.logger.warning("No web search agent available")
                results = []

            # 3. Format and ingest chunks
            chunks = []
            for res in results:
                content = res.get('content')
                if content:
                    # Format chunk with metadata
                    chunk_text = f"Source: {res.get('title', 'Web')}\nURL: {res.get('url', '')}\nContent: {content}"
                    chunks.append(chunk_text)

            # 4. Ingest into RAG vector store
            if chunks and self.rag_agent:
                await asyncio.to_thread(
                    self.rag_agent.ingest_text_chunks,
                    chunks,
                    metadata_path=f"Query: {query}"
                )
                self.logger.info(f"Ingested {len(chunks)} chunks for '{title}'")
                return f"✓ Researched '{title}': {len(chunks)} sources ingested"
            else:
                self.logger.warning(f"No chunks to ingest for '{title}'")
                return f"⚠ Researched '{title}': No sources found"

        except Exception as e:
            self.logger.error(f"Research error for '{title}': {e}")
            return f"✗ Error researching '{title}': {str(e)}"

    async def post_async(self, shared, prep_res, exec_res_list):
        """
        Store research results log in shared store.

        Args:
            shared: Shared data store
            prep_res: Blueprint items
            exec_res_list: List of research result strings

        Returns:
            Action string
        """
        shared["research_log"] = exec_res_list

        # Log summary
        self.logger.info("\nResearch Summary:")
        for log in exec_res_list:
            self.logger.info(f"  {log}")

        return "default"


def main():
    """
    Test function for ResearcherNode.

    Note: This is a mock test since ResearcherNode requires:
    - rag_agent
    - web_search_agent
    - Async execution environment
    """
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("ResearcherNode Structure Test")
    print("="*60 + "\n")

    # Create mock blueprint
    blueprint = [
        {
            "title": "Introduction to Diabetes",
            "description": "Overview of diabetes types, prevalence, and basic pathophysiology"
        },
        {
            "title": "Diagnosis and Testing",
            "description": "Diagnostic criteria, laboratory tests, and screening guidelines"
        },
        {
            "title": "Treatment Protocols",
            "description": "Evidence-based treatment approaches for Type 1 and Type 2 diabetes"
        }
    ]

    print("Test Blueprint:")
    for idx, item in enumerate(blueprint, 1):
        print(f"{idx}. {item['title']}")
        print(f"   {item['description']}\n")

    print("\nNote: Full testing requires:")
    print("  - RAG agent instance")
    print("  - Web search agent instance")
    print("  - Async runtime environment")
    print("\nUse integration tests with complete flow for full testing.")


if __name__ == "__main__":
    main()
