import os
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from serpapi_search_tools import web_search, SerpApiSearchError

load_dotenv()

logger = logging.getLogger(__name__)

def execute_search(
    query: str,
    engine: str = "google_light",
    num_results: int = 10,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes web search via SerpApi search tools and returns structured results.
    """
    if api_key is None:
        api_key = os.getenv("SERPAPI_API_KEY", "")
    if not api_key:
        return {
            "success": False,
            "error": "SERPAPI_API_KEY is missing. Please set it in your .env file or sidebar.",
            "query": query,
            "organic_results": [],
            "raw_response": ""
        }

    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "success": False,
            "error": "Search query cannot be empty.",
            "query": query,
            "organic_results": [],
            "raw_response": ""
        }

    try:
        search_fn = web_search(
            provider="function",
            response_format="json",
            result_limit=num_results,
            api_key=api_key
        )
        
        raw_output = search_fn(query=cleaned_query, engine=engine)
        
        # Parse JSON string output from web_search
        results_data = {}
        if isinstance(raw_output, str):
            results_data = json.loads(raw_output)
        elif isinstance(raw_output, dict):
            results_data = raw_output

        raw_organic = results_data.get("organic_results", [])
        
        structured_results: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw_organic, start=1):
            structured_results.append({
                "position": item.get("position", idx),
                "title": item.get("title", "Untitled Result"),
                "link": item.get("link", "#"),
                "snippet": item.get("snippet", "No snippet available."),
                "source": item.get("displayed_link", item.get("link", ""))
            })

        return {
            "success": True,
            "error": None,
            "query": cleaned_query,
            "organic_results": structured_results,
            "raw_response": raw_output
        }

    except SerpApiSearchError as e:
        logger.error(f"SerpApi Error: {e}")
        return {
            "success": False,
            "error": f"SerpApi Search Failure: {str(e)}",
            "query": cleaned_query,
            "organic_results": [],
            "raw_response": ""
        }
    except Exception as e:
        logger.error(f"Search Execution Error: {e}")
        return {
            "success": False,
            "error": f"Search execution failed: {str(e)}",
            "query": cleaned_query,
            "organic_results": [],
            "raw_response": ""
        }
