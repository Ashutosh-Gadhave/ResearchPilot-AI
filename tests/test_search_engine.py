import unittest
from unittest.mock import patch, MagicMock
from src.search_engine import execute_search

class TestSearchEngine(unittest.TestCase):

    def test_missing_api_key(self):
        result = execute_search("test query", api_key="")
        self.assertFalse(result["success"])
        self.assertIn("SERPAPI_API_KEY is missing", result["error"])

    def test_empty_query(self):
        result = execute_search("   ", api_key="fake_key")
        self.assertFalse(result["success"])
        self.assertIn("Search query cannot be empty", result["error"])

    @patch("src.search_engine.web_search")
    def test_successful_search_parsing(self, mock_web_search):
        mock_callable = MagicMock()
        mock_callable.return_value = '{"organic_results": [{"position": 1, "title": "Test Title", "link": "https://example.com", "snippet": "Test snippet", "displayed_link": "example.com"}]}'
        mock_web_search.return_value = mock_callable

        result = execute_search("Python unittest", api_key="fake_key")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["organic_results"]), 1)
        self.assertEqual(result["organic_results"][0]["title"], "Test Title")
        self.assertEqual(result["organic_results"][0]["link"], "https://example.com")

if __name__ == "__main__":
    unittest.main()
