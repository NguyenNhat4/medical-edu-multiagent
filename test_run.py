import sys
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Mock google.genai BEFORE importing nodes
mock_genai = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = mock_genai

from pocketflow import AsyncParallelBatchNode
from utils.call_llm import call_llm


class ResearcherNode(AsyncParallelBatchNode):
    async def prep_async(self, shared):
        self.rag_agent = shared.get("rag_agent")
        self.web_search_agent = shared.get("web_search_agent")
        return shared.get("blueprint", [])

    async def exec_async(self, item):
        if not item: return "No item"

        # 1. Generate Query
        prompt = f"""
Generate a specific, high-quality search query to find detailed medical information for the following section of a document.
Section Title: {item.get('title')}
Description: {item.get('description')}

Return ONLY the query string, no quotes.
"""
        try:
            query = await asyncio.to_thread(call_llm, prompt)
            query = query.strip().strip('"')
            print(f"🔎 Researching: {query}")

            # 2. Search
            if self.web_search_agent:
                results = await asyncio.to_thread(self.web_search_agent.search_raw, query)
            else:
                results = [] # Fallback

            # 3. Ingest
            chunks = []
            for res in results:
                content = res.get('content')
                if content:
                    # Format chunk with metadata
                    chunk_text = f"Source: {res.get('title', 'Web')}\nURL: {res.get('url', '')}\nContent: {content}"
                    chunks.append(chunk_text)

            if chunks and self.rag_agent:
                await asyncio.to_thread(self.rag_agent.ingest_text_chunks, chunks, metadata_path=f"Query: {query}")
                return f"Ingested {len(chunks)} results."
        except Exception as e:
            print(f"Researcher Error: {e}")
            return "Error in research."

        return "No results."

    async def post_async(self, shared, prep_res, exec_res_list):
        shared["research_log"] = exec_res_list
        return "default"


class TestResearcherNode(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.node = ResearcherNode()
        
    @patch('test_run.call_llm')
    async def test_prep_async_success(self, mock_call_llm):
        """Test prep_async extracts agents and blueprint from shared"""
        shared = {
            "rag_agent": MagicMock(),
            "web_search_agent": MagicMock(),
            "blueprint": [
                {"title": "Section 1", "description": "Description 1"},
                {"title": "Section 2", "description": "Description 2"}
            ]
        }
        
        prep_res = await self.node.prep_async(shared)
        
        self.assertIsNotNone(self.node.rag_agent)
        self.assertIsNotNone(self.node.web_search_agent)
        self.assertEqual(len(prep_res), 2)
        self.assertEqual(prep_res[0]["title"], "Section 1")
        
    async def test_prep_async_missing_agents(self):
        """Test prep_async handles missing agents gracefully"""
        shared = {
            "blueprint": [{"title": "Section 1", "description": "Desc"}]
        }
        
        prep_res = await self.node.prep_async(shared)
        
        self.assertIsNone(self.node.rag_agent)
        self.assertIsNone(self.node.web_search_agent)
        self.assertEqual(len(prep_res), 1)
        
    async def test_prep_async_empty_blueprint(self):
        """Test prep_async returns empty list when blueprint is missing"""
        shared = {}
        
        prep_res = await self.node.prep_async(shared)
        
        self.assertEqual(prep_res, [])
        
    @patch('test_run.call_llm')
    async def test_exec_async_no_item(self, mock_call_llm):
        """Test exec_async returns early when item is None or empty"""
        result = await self.node.exec_async(None)
        self.assertEqual(result, "No item")
        
        result = await self.node.exec_async({})
        self.assertEqual(result, "No item")
        
        mock_call_llm.assert_not_called()
        
    @patch('test_run.call_llm')
    async def test_exec_async_successful_research(self, mock_call_llm):
        """Test exec_async successfully processes item with search results"""
        # Setup mocks
        mock_call_llm.return_value = "medical treatment guidelines"
        
        mock_rag_agent = MagicMock()
        mock_rag_agent.ingest_text_chunks = MagicMock()
        
        mock_web_search_agent = MagicMock()
        mock_web_search_agent.search_raw = MagicMock(return_value=[
            {
                "title": "Medical Guide",
                "url": "https://example.com/guide",
                "content": "Treatment information here"
            },
            {
                "title": "Research Paper",
                "url": "https://example.com/paper",
                "content": "More detailed content"
            }
        ])
        
        self.node.rag_agent = mock_rag_agent
        self.node.web_search_agent = mock_web_search_agent
        
        item = {
            "title": "Treatment Methods",
            "description": "Different treatment approaches"
        }
        
        result = await self.node.exec_async(item)
        
        # Verify LLM was called
        mock_call_llm.assert_called_once()
        prompt = mock_call_llm.call_args[0][0]
        self.assertIn("Treatment Methods", prompt)
        self.assertIn("Different treatment approaches", prompt)
        
        # Verify search was called
        mock_web_search_agent.search_raw.assert_called_once_with("medical treatment guidelines")
        
        # Verify ingestion was called
        mock_rag_agent.ingest_text_chunks.assert_called_once()
        chunks_arg = mock_rag_agent.ingest_text_chunks.call_args[0][0]
        self.assertEqual(len(chunks_arg), 2)
        self.assertIn("Medical Guide", chunks_arg[0])
        self.assertIn("Treatment information here", chunks_arg[0])
        
        # Verify result
        self.assertEqual(result, "Ingested 2 results.")
        
    @patch('test_run.call_llm')
    async def test_exec_async_no_search_results(self, mock_call_llm):
        """Test exec_async handles case with no search results"""
        mock_call_llm.return_value = "query with no results"
        
        mock_web_search_agent = MagicMock()
        mock_web_search_agent.search_raw = MagicMock(return_value=[])
        
        self.node.web_search_agent = mock_web_search_agent
        self.node.rag_agent = MagicMock()
        
        item = {"title": "Section", "description": "Desc"}
        
        result = await self.node.exec_async(item)
        
        self.assertEqual(result, "No results.")
        self.node.rag_agent.ingest_text_chunks.assert_not_called()
        
    @patch('test_run.call_llm')
    async def test_exec_async_no_web_search_agent(self, mock_call_llm):
        """Test exec_async handles missing web_search_agent"""
        mock_call_llm.return_value = "some query"
        
        self.node.web_search_agent = None
        self.node.rag_agent = MagicMock()
        
        item = {"title": "Section", "description": "Desc"}
        
        result = await self.node.exec_async(item)
        
        self.assertEqual(result, "No results.")
        self.node.rag_agent.ingest_text_chunks.assert_not_called()
        
    @patch('test_run.call_llm')
    async def test_exec_async_no_rag_agent(self, mock_call_llm):
        """Test exec_async handles missing rag_agent"""
        mock_call_llm.return_value = "medical query"
        
        mock_web_search_agent = MagicMock()
        mock_web_search_agent.search_raw = MagicMock(return_value=[
            {"title": "Result", "url": "http://example.com", "content": "Content"}
        ])
        
        self.node.web_search_agent = mock_web_search_agent
        self.node.rag_agent = None
        
        item = {"title": "Section", "description": "Desc"}
        
        result = await self.node.exec_async(item)
        
        # Should return "No results" because rag_agent is None
        self.assertEqual(result, "No results.")
        
    @patch('test_run.call_llm')
    async def test_exec_async_error_handling(self, mock_call_llm):
        """Test exec_async handles exceptions gracefully"""
        mock_call_llm.side_effect = Exception("LLM API error")
        
        self.node.web_search_agent = MagicMock()
        self.node.rag_agent = MagicMock()
        
        item = {"title": "Section", "description": "Desc"}
        
        result = await self.node.exec_async(item)
        
        self.assertEqual(result, "Error in research.")
        
    @patch('test_run.call_llm')
    async def test_exec_async_query_stripping(self, mock_call_llm):
        """Test exec_async properly strips quotes from LLM query"""
        # Test with quotes
        mock_call_llm.return_value = '"medical treatment"'
        
        mock_web_search_agent = MagicMock()
        mock_web_search_agent.search_raw = MagicMock(return_value=[])
        
        self.node.web_search_agent = mock_web_search_agent
        self.node.rag_agent = None
        
        item = {"title": "Section", "description": "Desc"}
        
        await self.node.exec_async(item)
        
        # Verify search was called with stripped query
        mock_web_search_agent.search_raw.assert_called_once_with("medical treatment")
        
    @patch('test_run.call_llm')
    async def test_exec_async_chunk_formatting(self, mock_call_llm):
        """Test exec_async formats chunks correctly with metadata"""
        mock_call_llm.return_value = "test query"
        
        mock_rag_agent = MagicMock()
        mock_rag_agent.ingest_text_chunks = MagicMock()
        
        mock_web_search_agent = MagicMock()
        mock_web_search_agent.search_raw = MagicMock(return_value=[
            {
                "title": "Test Title",
                "url": "https://test.com/page",
                "content": "Test content here"
            }
        ])
        
        self.node.rag_agent = mock_rag_agent
        self.node.web_search_agent = mock_web_search_agent
        
        item = {"title": "Section", "description": "Desc"}
        
        await self.node.exec_async(item)
        
        # Verify chunk formatting
        chunks_arg = mock_rag_agent.ingest_text_chunks.call_args[0][0]
        self.assertEqual(len(chunks_arg), 1)
        chunk = chunks_arg[0]
        self.assertIn("Source: Test Title", chunk)
        self.assertIn("URL: https://test.com/page", chunk)
        self.assertIn("Content: Test content here", chunk)
        
        # Verify metadata_path
        metadata_arg = mock_rag_agent.ingest_text_chunks.call_args[1]["metadata_path"]
        self.assertEqual(metadata_arg, "Query: test query")
        
    async def test_post_async_success(self):
        """Test post_async stores results in shared"""
        shared = {}
        prep_res = [{"title": "Section 1"}, {"title": "Section 2"}]
        exec_res_list = ["Ingested 2 results.", "Ingested 1 results."]
        
        action = await self.node.post_async(shared, prep_res, exec_res_list)
        
        self.assertEqual(shared["research_log"], exec_res_list)
        self.assertEqual(action, "default")


if __name__ == '__main__':
    unittest.main()
