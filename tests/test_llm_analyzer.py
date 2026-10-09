import unittest
from unittest.mock import patch, MagicMock
from src.llm_analyzer import format_search_context, generate_decision_report

class TestLLMAnalyzer(unittest.TestCase):

    def test_format_search_context(self):
        sample_results = [
            {
                "position": 1,
                "title": "PostgreSQL Docs",
                "link": "https://postgresql.org",
                "snippet": "Official documentation"
            }
        ]
        context = format_search_context(sample_results)
        self.assertIn("[Source 1]", context)
        self.assertIn("Title: PostgreSQL Docs", context)
        self.assertIn("URL: https://postgresql.org", context)

    def test_empty_search_results(self):
        result = generate_decision_report("Question", "Priorities", [], api_key="fake_key")
        self.assertFalse(result["success"])
        self.assertIn("Cannot generate analysis without search results", result["error"])

    def test_missing_gemini_api_key(self):
        result = generate_decision_report("Question", "Priorities", [{"title": "X", "link": "Y"}], api_key="")
        self.assertFalse(result["success"])
        self.assertIn("GEMINI_API_KEY is missing", result["error"])

    @patch("src.llm_analyzer.genai.Client")
    def test_successful_report_generation(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "# 🏆 Recommendation Summary\nUse DuckDB for local analytics."
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        sample_results = [{"title": "DuckDB Docs", "link": "https://duckdb.org", "snippet": "Fast local SQL"}]
        result = generate_decision_report("DuckDB vs Postgres", "Speed", sample_results, api_key="fake_key")
        
        self.assertTrue(result["success"])
        self.assertIn("Recommendation Summary", result["report"])
        self.assertIn("DuckDB", result["report"])

if __name__ == "__main__":
    unittest.main()
