import sys
import os
import unittest
from unittest.mock import MagicMock, patch, Mock
import tempfile
import shutil

# Mock google.genai BEFORE importing anything
mock_genai = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = mock_genai

from rag_agent import MedicalRAG


class TestMedicalRAG(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock config object
        self.mock_config = MagicMock()
        self.mock_config.rag = MagicMock()
        self.mock_config.rag.parsed_content_dir = "/tmp/parsed_content"
        
        # Set up mock instances
        self.mock_doc_parser = MagicMock()
        self.mock_content_processor = MagicMock()
        self.mock_vector_store = MagicMock()
        self.mock_reranker = MagicMock()
        self.mock_query_expander = MagicMock()
        self.mock_response_generator = MagicMock()
        
        # Patch all dependencies before creating RAG instance
        # Use MagicMock as the replacement class that returns our instances when instantiated
        self.parser_patcher = patch('rag_agent.MedicalDocParser', 
                                    MagicMock(return_value=self.mock_doc_parser))
        self.processor_patcher = patch('rag_agent.ContentProcessor', 
                                      MagicMock(return_value=self.mock_content_processor))
        self.vectorstore_patcher = patch('rag_agent.VectorStore', 
                                        MagicMock(return_value=self.mock_vector_store))
        self.reranker_patcher = patch('rag_agent.Reranker', 
                                     MagicMock(return_value=self.mock_reranker))
        self.expander_patcher = patch('rag_agent.QueryExpander', 
                                     MagicMock(return_value=self.mock_query_expander))
        self.generator_patcher = patch('rag_agent.ResponseGenerator', 
                                      MagicMock(return_value=self.mock_response_generator))
        
        # Start all patches
        self.parser_patcher.start()
        self.processor_patcher.start()
        self.vectorstore_patcher.start()
        self.reranker_patcher.start()
        self.expander_patcher.start()
        self.generator_patcher.start()
        
        # Create RAG instance
        self.rag = MedicalRAG(self.mock_config)
        
        # Create temporary directory for file tests
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests"""
        # Stop all patches
        self.parser_patcher.stop()
        self.processor_patcher.stop()
        self.vectorstore_patcher.stop()
        self.reranker_patcher.stop()
        self.expander_patcher.stop()
        self.generator_patcher.stop()
        
        # Clean up temp directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_init_success(self):
        """Test MedicalRAG initialization"""
        self.assertIsNotNone(self.rag.config)
        self.assertEqual(self.rag.parsed_content_dir, self.mock_config.rag.parsed_content_dir)
        self.assertIsNotNone(self.rag.doc_parser)
        self.assertIsNotNone(self.rag.content_processor)
        self.assertIsNotNone(self.rag.vector_store)
        self.assertIsNotNone(self.rag.reranker)
        self.assertIsNotNone(self.rag.query_expander)
        self.assertIsNotNone(self.rag.response_generator)
        self.assertIsNotNone(self.rag.logger)
    
    def test_ingest_file_success(self):
        """Test successful file ingestion"""
        # Setup mocks
        test_file = os.path.join(self.test_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        mock_parsed_doc = {"text": "Parsed document content"}
        mock_images = ["image1.png", "image2.png"]
        mock_image_summaries = ["Summary 1", "Summary 2"]
        mock_formatted_doc = "Formatted document with images"
        mock_chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        
        self.mock_doc_parser.parse_document.return_value = (mock_parsed_doc, mock_images)
        self.mock_content_processor.summarize_images.return_value = mock_image_summaries
        self.mock_content_processor.format_document_with_images.return_value = mock_formatted_doc
        self.mock_content_processor.chunk_document.return_value = mock_chunks
        
        # Execute
        result = self.rag.ingest_file(test_file)
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(result["documents_ingested"], 1)
        self.assertEqual(result["chunks_processed"], 3)
        self.assertIn("processing_time", result)
        
        # Verify method calls
        self.mock_doc_parser.parse_document.assert_called_once_with(
            test_file, self.mock_config.rag.parsed_content_dir
        )
        self.mock_content_processor.summarize_images.assert_called_once_with(mock_images)
        self.mock_content_processor.format_document_with_images.assert_called_once_with(
            mock_parsed_doc, mock_image_summaries
        )
        self.mock_content_processor.chunk_document.assert_called_once_with(mock_formatted_doc)
        self.mock_vector_store.create_vectorstore.assert_called_once_with(
            document_chunks=mock_chunks,
            document_path=test_file
        )
    
    def test_ingest_file_parser_error(self):
        """Test file ingestion with parser error"""
        test_file = os.path.join(self.test_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        self.mock_doc_parser.parse_document.side_effect = Exception("Parser error")
        
        result = self.rag.ingest_file(test_file)
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Parser error")
        self.assertIn("processing_time", result)
    
    def test_ingest_file_no_images(self):
        """Test file ingestion with no images"""
        test_file = os.path.join(self.test_dir, "test.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        mock_parsed_doc = {"text": "Parsed document"}
        mock_images = []
        mock_chunks = ["Chunk 1"]
        
        self.mock_doc_parser.parse_document.return_value = (mock_parsed_doc, mock_images)
        self.mock_content_processor.summarize_images.return_value = []
        self.mock_content_processor.format_document_with_images.return_value = "Formatted"
        self.mock_content_processor.chunk_document.return_value = mock_chunks
        
        result = self.rag.ingest_file(test_file)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_processed"], 1)
    
    def test_ingest_directory_success(self):
        """Test successful directory ingestion"""
        # Create test files
        test_file1 = os.path.join(self.test_dir, "file1.pdf")
        test_file2 = os.path.join(self.test_dir, "file2.pdf")
        with open(test_file1, 'w') as f:
            f.write("content1")
        with open(test_file2, 'w') as f:
            f.write("content2")
        
        # Setup mocks
        mock_parsed_doc = {"text": "Parsed"}
        mock_chunks1 = ["Chunk 1", "Chunk 2"]
        mock_chunks2 = ["Chunk 3"]
        
        self.mock_doc_parser.parse_document.return_value = (mock_parsed_doc, [])
        self.mock_content_processor.summarize_images.return_value = []
        self.mock_content_processor.format_document_with_images.return_value = "Formatted"
        
        # Return different chunks for each file
        def chunk_side_effect(doc):
            if "content1" in str(doc):
                return mock_chunks1
            return mock_chunks2
        
        self.mock_content_processor.chunk_document.side_effect = chunk_side_effect
        
        # Execute
        result = self.rag.ingest_directory(self.test_dir)
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(result["documents_ingested"], 2)
        self.assertEqual(result["chunks_processed"], 3)  # 2 + 1
        self.assertEqual(result["failed_documents"], 0)
        self.assertIn("processing_time", result)
    
    def test_ingest_directory_not_found(self):
        """Test directory ingestion with non-existent directory"""
        result = self.rag.ingest_directory("/nonexistent/directory")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_ingest_directory_empty(self):
        """Test directory ingestion with empty directory"""
        result = self.rag.ingest_directory(self.test_dir)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["documents_ingested"], 0)
        self.assertEqual(result["chunks_processed"], 0)
    
    def test_ingest_directory_partial_failure(self):
        """Test directory ingestion with some files failing"""
        # Create test files
        test_file1 = os.path.join(self.test_dir, "file1.pdf")
        test_file2 = os.path.join(self.test_dir, "file2.pdf")
        with open(test_file1, 'w') as f:
            f.write("content1")
        with open(test_file2, 'w') as f:
            f.write("content2")
        
        # Setup mocks - first file succeeds, second fails
        mock_parsed_doc = {"text": "Parsed"}
        mock_chunks = ["Chunk 1"]
        
        def parse_side_effect(file_path, *args):
            if "file2" in file_path:
                raise Exception("Parse error")
            return (mock_parsed_doc, [])
        
        self.mock_doc_parser.parse_document.side_effect = parse_side_effect
        self.mock_content_processor.summarize_images.return_value = []
        self.mock_content_processor.format_document_with_images.return_value = "Formatted"
        self.mock_content_processor.chunk_document.return_value = mock_chunks
        
        # Execute
        result = self.rag.ingest_directory(self.test_dir)
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(result["documents_ingested"], 1)
        self.assertEqual(result["failed_documents"], 1)
        self.assertEqual(len(result["failed_files"]), 1)
        self.assertIn("file2", result["failed_files"][0]["file"])
    
    def test_ingest_text_chunks_success(self):
        """Test successful text chunks ingestion"""
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        metadata = "Test Source"
        
        result = self.rag.ingest_text_chunks(chunks, metadata)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_processed"], 3)
        self.assertIn("processing_time", result)
        
        # Verify vector store was called
        self.mock_vector_store.create_vectorstore.assert_called_once_with(
            document_chunks=chunks,
            document_path=metadata
        )
    
    def test_ingest_text_chunks_empty(self):
        """Test text chunks ingestion with empty list"""
        result = self.rag.ingest_text_chunks([])
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_processed"], 0)
        self.mock_vector_store.create_vectorstore.assert_called_once()
    
    def test_ingest_text_chunks_error(self):
        """Test text chunks ingestion with error"""
        chunks = ["Chunk 1"]
        
        self.mock_vector_store.create_vectorstore.side_effect = Exception("Vector store error")
        
        result = self.rag.ingest_text_chunks(chunks)
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Vector store error")
    
    def test_process_query_success(self):
        """Test successful query processing"""
        query = "What is diabetes?"
        expanded_query = "diabetes mellitus type symptoms treatment"
        mock_docs = [
            {"content": "Document 1", "metadata": {}},
            {"content": "Document 2", "metadata": {}}
        ]
        mock_response = {
            "response": "Diabetes is a metabolic disorder...",
            "sources": ["source1", "source2"],
            "confidence": 0.85
        }
        
        # Setup mocks
        self.mock_query_expander.expand_query.return_value = {
            "expanded_query": expanded_query
        }
        self.mock_vector_store.retrieve_relevant_chunks.return_value = mock_docs
        self.mock_reranker.rerank.return_value = (mock_docs, ["image1.png"])
        self.mock_response_generator.generate_response.return_value = mock_response
        
        # Execute
        result = self.rag.process_query(query)
        
        # Verify
        self.assertIn("response", result)
        self.assertIn("sources", result)
        self.assertIn("confidence", result)
        self.assertIn("processing_time", result)
        self.assertEqual(result["response"], mock_response["response"])
        
        # Verify method calls
        self.mock_query_expander.expand_query.assert_called_once_with(query)
        self.mock_vector_store.load_vectorstore.assert_called_once()
        self.mock_vector_store.retrieve_relevant_chunks.assert_called_once_with(
            query=expanded_query
        )
        self.mock_reranker.rerank.assert_called_once()
        self.mock_response_generator.generate_response.assert_called_once()
    
    def test_process_query_no_reranking(self):
        """Test query processing without reranking (not enough documents)"""
        query = "test query"
        expanded_query = "expanded query"
        mock_docs = [{"content": "Doc 1"}]
        mock_response = {"response": "Answer", "sources": [], "confidence": 0.5}
        
        self.mock_query_expander.expand_query.return_value = {"expanded_query": expanded_query}
        self.mock_vector_store.retrieve_relevant_chunks.return_value = mock_docs
        self.mock_response_generator.generate_response.return_value = mock_response
        
        result = self.rag.process_query(query)
        
        # Should skip reranking with only 1 document
        self.mock_reranker.rerank.assert_not_called()
        self.assertIn("response", result)
    
    def test_process_query_no_reranker(self):
        """Test query processing without reranker"""
        # Remove reranker
        self.rag.reranker = None
        
        query = "test query"
        expanded_query = "expanded query"
        mock_docs = [{"content": "Doc 1"}, {"content": "Doc 2"}]
        mock_response = {"response": "Answer", "sources": [], "confidence": 0.5}
        
        self.mock_query_expander.expand_query.return_value = {"expanded_query": expanded_query}
        self.mock_vector_store.retrieve_relevant_chunks.return_value = mock_docs
        self.mock_response_generator.generate_response.return_value = mock_response
        
        result = self.rag.process_query(query)
        
        # Should skip reranking when reranker is None
        self.assertIn("response", result)
    
    def test_process_query_with_chat_history(self):
        """Test query processing with chat history"""
        query = "What is diabetes?"
        chat_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi, how can I help?"}
        ]
        expanded_query = "diabetes"
        mock_docs = [{"content": "Doc"}]
        mock_response = {"response": "Answer", "sources": [], "confidence": 0.5}
        
        self.mock_query_expander.expand_query.return_value = {"expanded_query": expanded_query}
        self.mock_vector_store.retrieve_relevant_chunks.return_value = mock_docs
        self.mock_reranker.rerank.return_value = (mock_docs, [])
        self.mock_response_generator.generate_response.return_value = mock_response
        
        result = self.rag.process_query(query, chat_history)
        
        # Verify chat_history was passed to response generator
        call_args = self.mock_response_generator.generate_response.call_args
        self.assertEqual(call_args[1]["chat_history"], chat_history)
        self.assertIn("response", result)
    
    def test_process_query_expansion_error(self):
        """Test query processing with query expansion error"""
        query = "test query"
        
        self.mock_query_expander.expand_query.side_effect = Exception("Expansion error")
        
        result = self.rag.process_query(query)
        
        self.assertIn("response", result)
        self.assertIn("error", result["response"].lower())
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["confidence"], 0.0)
    
    def test_process_query_retrieval_error(self):
        """Test query processing with retrieval error"""
        query = "test query"
        expanded_query = "expanded"
        
        self.mock_query_expander.expand_query.return_value = {"expanded_query": expanded_query}
        self.mock_vector_store.retrieve_relevant_chunks.side_effect = Exception("Retrieval error")
        
        result = self.rag.process_query(query)
        
        self.assertIn("response", result)
        self.assertIn("error", result["response"].lower())
    
    def test_process_query_response_generation_error(self):
        """Test query processing with response generation error"""
        query = "test query"
        expanded_query = "expanded"
        mock_docs = [{"content": "Doc"}]
        
        self.mock_query_expander.expand_query.return_value = {"expanded_query": expanded_query}
        self.mock_vector_store.retrieve_relevant_chunks.return_value = mock_docs
        self.mock_reranker.rerank.return_value = (mock_docs, [])
        self.mock_response_generator.generate_response.side_effect = Exception("Generation error")
        
        result = self.rag.process_query(query)
        
        self.assertIn("response", result)
        self.assertIn("error", result["response"].lower())


if __name__ == '__main__':
    unittest.main()

