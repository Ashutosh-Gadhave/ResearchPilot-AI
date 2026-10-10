import unittest
from unittest.mock import patch, MagicMock
from src.llm_analyzer import format_search_context, generate_decision_report, extract_json_block

class TestLLMAnalyzer(unittest.TestCase):

    def test_format_search_context_isolation(self):
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
        self.assertIn("Search Result Snippet", context)

    def test_extract_json_block(self):
        raw_text = 'Some markdown text\n```json\n{"evaluations": {"Option A": {"Speed": 5.0}}}\n```\nMore text'
        extracted = extract_json_block(raw_text)
        self.assertIsNotNone(extracted)
        self.assertIn("evaluations", extracted)
        self.assertEqual(extracted["evaluations"]["Option A"]["Speed"], 5.0)

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
        mock_response.text = (
            "```json\n"
            '{"candidates": ["DuckDB", "Postgres"], "evaluations": {"DuckDB": {"Speed": 5.0}, "Postgres": {"Speed": 3.0}}}\n'
            "```\n"
            "# 🏆 Executive Recommendation & Rationale\nUse DuckDB for local analytics."
        )
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        sample_results = [{"title": "DuckDB Docs", "link": "https://duckdb.org", "snippet": "Fast local SQL"}]
        result = generate_decision_report(
            question="DuckDB vs Postgres",
            priorities_input="Speed",
            organic_results=sample_results,
            criteria_weights={"Speed": 5},
            api_key="fake_key"
        )
        
        self.assertTrue(result["success"])
        self.assertIn("Executive Recommendation", result["report"])
        self.assertIn("DuckDB", result["report"])
        self.assertTrue(len(result["matrix_md"]) > 0)

    @patch("src.llm_analyzer.genai.Client")
    def test_priorities_parameter_mismatch_regression(self, mock_client_cls):
        """Regression test to verify priorities_input and priorities keyword args both work."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "# Recommendation Summary\nDuckDB"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        sample_results = [{"title": "X", "link": "https://x.com", "snippet": "Y"}]
        
        # Test keyword argument 'priorities_input'
        res1 = generate_decision_report(
            question="Q1",
            priorities_input="Criteria 1",
            organic_results=sample_results,
            api_key="fake_key"
        )
        self.assertTrue(res1["success"])

        # Test keyword argument 'priorities'
        res2 = generate_decision_report(
            question="Q2",
            priorities="Criteria 2",
            organic_results=sample_results,
            api_key="fake_key"
        )
        self.assertTrue(res2["success"])

    @patch("src.llm_analyzer.time.sleep")
    @patch("src.llm_analyzer.genai.Client")
    def test_gemini_503_unavailable_handling(self, mock_client_cls, mock_sleep):
        from google.genai.errors import APIError
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = APIError(503, {"error": {"message": "503 UNAVAILABLE: No capacity available for model on server"}})
        mock_client_cls.return_value = mock_client

        sample_results = [{"title": "X", "link": "https://x.com", "snippet": "Y"}]
        res = generate_decision_report(
            question="Q503",
            organic_results=sample_results,
            api_key="fake_key"
        )
        self.assertFalse(res["success"])
        self.assertIn("temporarily unavailable due to high demand (HTTP 503)", res["error"])

    @patch("src.llm_analyzer.time.sleep")
    @patch("src.llm_analyzer.genai.Client")
    def test_gemini_429_quota_handling(self, mock_client_cls, mock_sleep):
        from google.genai.errors import APIError
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = APIError(429, {"error": {"message": "429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric"}})
        mock_client_cls.return_value = mock_client

        sample_results = [{"title": "X", "link": "https://x.com", "snippet": "Y"}]
        res = generate_decision_report(
            question="Q429",
            organic_results=sample_results,
            api_key="fake_key"
        )
        self.assertFalse(res["success"])
        self.assertIn("rate limit or quota exceeded (HTTP 429)", res["error"])

if __name__ == "__main__":
    unittest.main()
