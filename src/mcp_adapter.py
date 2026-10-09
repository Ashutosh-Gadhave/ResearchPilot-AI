import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SERPAPI_MCP_ENDPOINT = "https://mcp.serpapi.com/mcp"

class SerpApiMCPError(Exception):
    """Exception raised for errors during MCP JSON-RPC protocol communication."""
    pass

class SerpApiMCPClient:
    """
    Official Model Context Protocol (MCP) client for SerpApi hosted server (mcp.serpapi.com).
    Communicates using standard JSON-RPC 2.0 protocol over Streamable HTTP transport.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_url: str = SERPAPI_MCP_ENDPOINT,
        timeout: float = 15.0
    ):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        self.endpoint_url = endpoint_url
        self.timeout = timeout

    def _send_json_rpc(self, method: str, params: Optional[Dict[str, Any]] = None, req_id: int = 1) -> Dict[str, Any]:
        """Sends a JSON-RPC 2.0 request to the SerpApi MCP server endpoint."""
        if not self.api_key:
            raise SerpApiMCPError("SERPAPI_API_KEY is missing. Cannot authenticate MCP connection.")

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method
        }
        if params is not None:
            payload["params"] = params

        data_bytes = json.dumps(payload).encode("utf-8")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ResearchPilot-AI-MCPClient/1.0"
        }

        req = urllib.request.Request(self.endpoint_url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_resp = resp.read().decode("utf-8")
                response_data = json.loads(raw_resp)
                
                if "error" in response_data:
                    err_msg = response_data["error"].get("message", str(response_data["error"]))
                    raise SerpApiMCPError(f"SerpApi MCP Server returned JSON-RPC error: {err_msg}")
                    
                return response_data

        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            raise SerpApiMCPError(f"HTTP {e.code} error connecting to SerpApi MCP Server: {e.reason}. {err_body}")
        except urllib.error.URLError as e:
            raise SerpApiMCPError(f"Network error connecting to SerpApi MCP Server: {e.reason}")
        except json.JSONDecodeError as e:
            raise SerpApiMCPError(f"Failed to parse JSON response from SerpApi MCP Server: {e}")
        except Exception as e:
            raise SerpApiMCPError(f"Unexpected MCP protocol failure: {str(e)}")

    def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Invokes MCP `tools/list` JSON-RPC method to discover available search tools.
        """
        response = self._send_json_rpc(method="tools/list", req_id=1)
        result = response.get("result", {})
        tools = result.get("tools", [])
        logger.info(f"Discovered {len(tools)} tools on SerpApi MCP server.")
        return tools

    def call_search_tool(
        self,
        query: str,
        engine: str = "google_light",
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        Invokes MCP `tools/call` method with tool name 'search' over the official SerpApi MCP protocol.
        """
        call_params = {
            "name": "search",
            "arguments": {
                "params": {
                    "q": query,
                    "engine": engine
                },
                "mode": "compact"
            }
        }

        response = self._send_json_rpc(method="tools/call", params=call_params, req_id=2)
        result = response.get("result", {})
        
        if result.get("isError"):
            raise SerpApiMCPError("SerpApi MCP Tool call returned execution error.")

        content_list = result.get("content", [])
        if not content_list:
            return {"organic_results": []}

        # Extract output text block containing serialized JSON search results
        raw_text = ""
        for block in content_list:
            if isinstance(block, dict) and block.get("type") == "text":
                raw_text += block.get("text", "")
            elif isinstance(block, dict) and "text" in block:
                raw_text += block["text"]

        if not raw_text and isinstance(content_list, str):
            raw_text = content_list

        try:
            search_json = json.loads(raw_text)
            return search_json
        except Exception as e:
            logger.warning(f"Could not parse MCP search text result as JSON: {e}")
            return {"organic_results": [], "raw_text": raw_text}
