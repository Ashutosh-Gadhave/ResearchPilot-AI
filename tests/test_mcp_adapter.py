import unittest
import json
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from src.mcp_adapter import SerpApiMCPClient, SerpApiMCPError
from src.search_engine import execute_search

class TestSerpApiMCPAdapter(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_discover_tools_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {"name": "search", "description": "SerpApi search tool"},
                    {"name": "search_table", "description": "Table view"},
                    {"name": "search_dashboard", "description": "Dashboard view"}
                ]
            }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = SerpApiMCPClient(api_key="fake_key")
        tools = client.discover_tools()

        self.assertEqual(len(tools), 3)
        self.assertEqual(tools[0]["name"], "search")

    @patch("urllib.request.urlopen")
    def test_call_search_tool_success(self, mock_urlopen):
        mock_response = MagicMock()
        search_json_text = json.dumps({
            "organic_results": [
                {"position": 1, "title": "MCP Title", "link": "https://mcp.example.com", "snippet": "MCP Snippet"}
            ]
        })
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [{"type": "text", "text": search_json_text}],
                "isError": False
            }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = SerpApiMCPClient(api_key="fake_key")
        result = client.call_search_tool("MCP query", engine="google_light")

        self.assertIn("organic_results", result)
        self.assertEqual(len(result["organic_results"]), 1)
        self.assertEqual(result["organic_results"][0]["title"], "MCP Title")

    @patch("urllib.request.urlopen")
    def test_mcp_error_handling(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid MCP Request"}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = SerpApiMCPClient(api_key="fake_key")
        with self.assertRaises(SerpApiMCPError):
            client.discover_tools()

    @patch("src.search_engine.SerpApiMCPClient.call_search_tool")
    @patch("src.search_engine.web_search")
    def test_execute_search_mcp_fallback_on_error(self, mock_web_search, mock_mcp_call):
        # Mock MCP throwing an error
        mock_mcp_call.side_effect = SerpApiMCPError("MCP Connection Failed")
        
        # Mock SDK fallback succeeding
        mock_callable = MagicMock()
        mock_callable.return_value = json.dumps({
            "organic_results": [
                {"position": 1, "title": "SDK Fallback Title", "link": "https://fallback.com", "snippet": "Fallback snippet"}
            ]
        })
        mock_web_search.return_value = mock_callable

        result = execute_search("Test query", api_key="fake_key", use_mcp=True)

        self.assertTrue(result["success"])
        self.assertFalse(result["via_mcp"])  # Confirms transparent fallback to SDK
        self.assertEqual(len(result["organic_results"]), 1)
        self.assertEqual(result["organic_results"][0]["title"], "SDK Fallback Title")

if __name__ == "__main__":
    unittest.main()
