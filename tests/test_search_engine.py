import unittest
from unittest.mock import patch, MagicMock
from serpapi_search_tools import SerpApiSearchError
from src.search_engine import execute_search, extract_domain

class TestSearchEngine(unittest.TestCase):

    def test_extract_domain(self):
        self.assertEqual(extract_domain("https://docs.python.org/3/library/unittest.html"), "docs.python.org")
        self.assertEqual(extract_domain("invalid_url"), "invalid_url")

    def test_missing_api_key(self):
        result = execute_search("test query", api_key="")
        self.assertFalse(result["success"])
        self.assertIn("SERPAPI_API_KEY is missing", result["error"])

    def test_empty_query(self):
        result = execute_search("   ", api_key="fake_key")
        self.assertFalse(result["success"])
        self.assertIn("Search query cannot be empty", result["error"])

    @patch("src.search_engine.web_search")
    def test_successful_search_parsing_and_url_preservation(self, mock_web_search):
        mock_callable = MagicMock()
        mock_callable.return_value = '{"organic_results": [{"position": 1, "title": "Test Title", "link": "https://example.com/page?ref=serpapi", "snippet": "Test snippet", "displayed_link": "example.com"}]}'
        mock_web_search.return_value = mock_callable

        result = execute_search("Python unittest", api_key="fake_key")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["organic_results"]), 1)
        self.assertEqual(result["organic_results"][0]["title"], "Test Title")
        # Verify unaltered direct URL preservation
        self.assertEqual(result["organic_results"][0]["link"], "https://example.com/page?ref=serpapi")
        self.assertEqual(result["organic_results"][0]["source"], "example.com")
        self.assertFalse(result["organic_results"][0]["verified_full_page"])

    @patch("src.search_engine.web_search")
    def test_serpapi_error_handling(self, mock_web_search):
        mock_callable = MagicMock()
        mock_callable.side_effect = SerpApiSearchError("Invalid API Key")
        mock_web_search.return_value = mock_callable

        result = execute_search("Test query", api_key="invalid_key")
        self.assertFalse(result["success"])
        self.assertIn("SerpApi Search Failure", result["error"])

if __name__ == "__main__":
    unittest.main()
