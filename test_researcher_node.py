import sys
from unittest.mock import MagicMock

# Mock modules to avoid import errors
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["dotenv"] = MagicMock()
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["docx"] = MagicMock()
sys.modules["docx.shared"] = MagicMock()
sys.modules["docx.enum"] = MagicMock()
sys.modules["docx.enum.text"] = MagicMock()
sys.modules["docx.enum.style"] = MagicMock()
sys.modules["docx.oxml"] = MagicMock()
sys.modules["docx.oxml.ns"] = MagicMock()
sys.modules["yaml"] = MagicMock()

import unittest
import asyncio
from unittest.mock import patch
from pocketflow import AsyncFlow
from nodes import ResearcherNode

class TestResearcherNode(unittest.TestCase):
    def setUp(self):
        self.shared = {
            "blueprint": [
                {"title": "Section 1", "description": "Description 1"},
                {"title": "Section 2", "description": "Description 2"}
            ],
            "rag_agent": MagicMock(),
            "web_search_agent": MagicMock()
        }
        self.node = ResearcherNode()

    def test_researcher_node_success(self):
        # Mock dependencies
        with patch('nodes.call_llm') as mock_call_llm:
            # call_llm return value
            mock_call_llm.return_value = "query"

            # search_raw return value
            self.shared["web_search_agent"].search_raw.return_value = [
                {"title": "Title 1", "url": "http://url1.com", "content": "Content 1"}
            ]

            # ingest_text_chunks return value
            self.shared["rag_agent"].ingest_text_chunks.return_value = None

            # Create flow
            flow = AsyncFlow(start=self.node)

            # Run async test
            asyncio.run(flow.run_async(self.shared))

            # Verifications
            # call_llm should be called twice (once for each blueprint item)
            self.assertEqual(mock_call_llm.call_count, 2)

            # web_search_agent.search_raw should be called twice
            self.assertEqual(self.shared["web_search_agent"].search_raw.call_count, 2)
            self.shared["web_search_agent"].search_raw.assert_any_call("query")

            # rag_agent.ingest_text_chunks should be called twice
            self.assertEqual(self.shared["rag_agent"].ingest_text_chunks.call_count, 2)

            # Check results in shared
            self.assertIn("research_log", self.shared)
            self.assertEqual(len(self.shared["research_log"]), 2)
            for res in self.shared["research_log"]:
                self.assertEqual(res, "Ingested 1 results.")

    def test_researcher_node_error(self):
        with patch('nodes.call_llm') as mock_call_llm:
            # Simulate an exception in call_llm
            mock_call_llm.side_effect = Exception("LLM Error")

            flow = AsyncFlow(start=self.node)
            asyncio.run(flow.run_async(self.shared))

            # Check that error was caught and logged
            self.assertIn("research_log", self.shared)
            for res in self.shared["research_log"]:
                self.assertEqual(res, "Error in research.")

    def test_researcher_node_no_web_search_agent(self):
        # Test case where web_search_agent is None
        self.shared["web_search_agent"] = None

        with patch('nodes.call_llm') as mock_call_llm:
            mock_call_llm.return_value = "query"

            flow = AsyncFlow(start=self.node)
            asyncio.run(flow.run_async(self.shared))

            # Should ingest 0 results because search fallback returns []
            self.assertIn("research_log", self.shared)
            # Logic: results = [], chunks = [], if chunks and rag_agent: ... return "Ingested..."
            # If chunks is empty, it returns "No results."
            for res in self.shared["research_log"]:
                self.assertEqual(res, "No results.")

if __name__ == '__main__':
    unittest.main()
