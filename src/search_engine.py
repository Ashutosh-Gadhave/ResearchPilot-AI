import os
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from serpapi_search_tools import web_search, SerpApiSearchError
from src.mcp_adapter import SerpApiMCPClient, SerpApiMCPError

load_dotenv()

logger = logging.getLogger(__name__)

def extract_domain(url: str) -> str:
    """Extracts clean domain name from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or url
    except Exception:
        return url

def execute_search(
    query: str,
    engine: str = "google_light",
    num_results: int = 10,
    api_key: Optional[str] = None,
    use_mcp: bool = True
) -> Dict[str, Any]:
    """
    Executes web search via SerpApi Model Context Protocol (MCP) or falls back to SerpApi Python SDK.
    Preserves exact original URLs returned by SerpApi and annotates evidence metadata.
    """
    if api_key is None:
        api_key = os.getenv("SERPAPI_API_KEY", "")
    if not api_key:
        return {
            "success": False,
            "error": "SERPAPI_API_KEY is missing. Please set it in your .env file or sidebar.",
            "query": query,
            "organic_results": [],
            "raw_response": "",
            "via_mcp": False
        }

    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "success": False,
            "error": "Search query cannot be empty.",
            "query": query,
            "organic_results": [],
            "raw_response": "",
            "via_mcp": False
        }

    # Strategy 1: Attempt search over official SerpApi MCP Protocol (mcp.serpapi.com)
    if use_mcp:
        try:
            logger.info(f"Attempting search via SerpApi MCP Protocol for query: '{cleaned_query}'")
            mcp_client = SerpApiMCPClient(api_key=api_key)
            mcp_data = mcp_client.call_search_tool(query=cleaned_query, engine=engine, num_results=num_results)
            
            raw_organic = mcp_data.get("organic_results", [])
            structured_results: List[Dict[str, Any]] = []
            
            for idx, item in enumerate(raw_organic, start=1):
                original_url = item.get("link") or item.get("redirect_link") or "#"
                domain = item.get("displayed_link") or extract_domain(original_url)

                structured_results.append({
                    "position": item.get("position", idx),
                    "title": item.get("title", "Untitled Result"),
                    "link": original_url,
                    "snippet": item.get("snippet", "No snippet available."),
                    "source": domain,
                    "verified_full_page": False,
                    "via_mcp": True
                })

            return {
                "success": True,
                "error": None,
                "query": cleaned_query,
                "organic_results": structured_results,
                "raw_response": mcp_data,
                "via_mcp": True
            }

        except SerpApiMCPError as e:
            logger.warning(f"SerpApi MCP protocol attempt failed/unavailable: {e}. Falling back to Python SDK...")
        except Exception as e:
            logger.warning(f"Unexpected MCP error: {e}. Falling back to Python SDK...")

    # Strategy 2: Fallback to SerpApi Python Search Tools SDK
    try:
        logger.info(f"Executing search via SerpApi Python SDK fallback for query: '{cleaned_query}'")
        search_fn = web_search(
            provider="function",
            response_format="json",
            result_limit=num_results,
            api_key=api_key
        )
        
        raw_output = search_fn(query=cleaned_query, engine=engine)
        
        results_data = {}
        if isinstance(raw_output, str):
            results_data = json.loads(raw_output)
        elif isinstance(raw_output, dict):
            results_data = raw_output

        raw_organic = results_data.get("organic_results", [])
        
        structured_results: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw_organic, start=1):
            original_url = item.get("link") or item.get("redirect_link") or "#"
            domain = item.get("displayed_link") or extract_domain(original_url)

            structured_results.append({
                "position": item.get("position", idx),
                "title": item.get("title", "Untitled Result"),
                "link": original_url,
                "snippet": item.get("snippet", "No snippet available."),
                "source": domain,
                "verified_full_page": False,
                "via_mcp": False
            })

        return {
            "success": True,
            "error": None,
            "query": cleaned_query,
            "organic_results": structured_results,
            "raw_response": raw_output,
            "via_mcp": False
        }

    except SerpApiSearchError as e:
        logger.error(f"SerpApi Error: {e}")
        return {
            "success": False,
            "error": f"SerpApi Search Failure: {str(e)}",
            "query": cleaned_query,
            "organic_results": [],
            "raw_response": "",
            "via_mcp": False
        }
    except Exception as e:
        logger.error(f"Search Execution Error: {e}")
        return {
            "success": False,
            "error": f"Search execution failed: {str(e)}",
            "query": cleaned_query,
            "organic_results": [],
            "raw_response": "",
            "via_mcp": False
        }
