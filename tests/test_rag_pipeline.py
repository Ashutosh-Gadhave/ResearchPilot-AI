import unittest
from unittest.mock import patch, MagicMock
from src.rag_pipeline import (
    cosine_similarity,
    chunk_evidence_items,
    InMemoryVectorStore,
    format_rag_context
)

class TestRAGPipeline(unittest.TestCase):

    def test_cosine_similarity_math(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0)

        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v3), 0.0)

        v4 = [1.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v4), 0.70710678, places=4)

    def test_chunk_evidence_items(self):
        sample_results = [
            {
                "title": "PostgreSQL vs DuckDB",
                "link": "https://example.com/db",
                "snippet": "DuckDB is an in-process SQL OLAP database management system.",
                "source": "example.com"
            }
        ]
        chunks = chunk_evidence_items(sample_results)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0]["title"], "PostgreSQL vs DuckDB")
        self.assertEqual(chunks[0]["link"], "https://example.com/db")
        self.assertFalse(chunks[0]["verified_full_page"])

    @patch("src.rag_pipeline.genai.Client")
    def test_vector_store_indexing_and_retrieval_mocked(self, mock_genai_client):
        mock_client = MagicMock()
        
        # Mock embeddings: Query=[1, 0], Passage1=[1, 0] (high sim), Passage2=[0, 1] (low sim)
        mock_emb_query = MagicMock()
        mock_emb_query.embeddings = [MagicMock(values=[1.0, 0.0])]

        mock_emb_p1 = MagicMock()
        mock_emb_p1.embeddings = [MagicMock(values=[1.0, 0.0])]

        mock_emb_p2 = MagicMock()
        mock_emb_p2.embeddings = [MagicMock(values=[0.0, 1.0])]

        mock_client.models.embed_content.side_effect = [mock_emb_p1, mock_emb_p2, mock_emb_query]
        mock_genai_client.return_value = mock_client

        store = InMemoryVectorStore(api_key="fake_key")
        sample_results = [
            {"title": "P1", "link": "https://p1.com", "snippet": "Passage 1 text"},
            {"title": "P2", "link": "https://p2.com", "snippet": "Passage 2 text"}
        ]
        
        indexed = store.index_evidence(sample_results)
        self.assertTrue(indexed)

        retrieved = store.retrieve_relevant_passages("query text", top_k=2)
        self.assertEqual(len(retrieved), 2)
        # P1 should have higher similarity score than P2
        self.assertGreater(retrieved[0]["similarity_score"], retrieved[1]["similarity_score"])
        self.assertEqual(retrieved[0]["title"], "P1")

    def test_rag_pipeline_empty_input_and_error_fallback(self):
        store = InMemoryVectorStore(api_key="")
        self.assertFalse(store.index_evidence([]))
        self.assertEqual(store.retrieve_relevant_passages("query"), [])

    def test_format_rag_context(self):
        passages = [
            {
                "title": "DuckDB Docs",
                "link": "https://duckdb.org",
                "snippet": "Fast local OLAP",
                "similarity_score": 0.892
            }
        ]
        formatted = format_rag_context(passages)
        self.assertIn("Title: DuckDB Docs", formatted)
        self.assertIn("URL: https://duckdb.org", formatted)
        self.assertIn("Retrieval Similarity Score: 0.892", formatted)

if __name__ == "__main__":
    unittest.main()
