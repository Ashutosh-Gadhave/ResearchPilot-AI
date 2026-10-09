import os
import json
import uuid
import logging
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.agents import run_research_pilot_agent_workflow, ResearchState

logger = logging.getLogger(__name__)

DEFAULT_WATCHLIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_WATCHLIST_FILE = os.path.join(DEFAULT_WATCHLIST_DIR, "watchlist.json")

def sanitize_state_for_storage(data: Any) -> Any:
    """
    Recursively strips out sensitive keys (API keys, secrets, tokens) prior to serialization.
    """
    if isinstance(data, dict):
        clean_dict = {}
        for k, v in data.items():
            if any(secret_kw in k.lower() for secret_kw in ["api_key", "secret", "token", "password"]):
                continue
            clean_dict[k] = sanitize_state_for_storage(v)
        return clean_dict
    elif isinstance(data, list):
        return [sanitize_state_for_storage(item) for item in data]
    return data

def load_watchlist(filepath: str = DEFAULT_WATCHLIST_FILE) -> Dict[str, Any]:
    """
    Loads and parses the watchlist JSON file safely.
    Returns default structure on missing, empty, or corrupted files.
    """
    default_schema = {"version": "1.0", "items": {}}

    if not os.path.exists(filepath):
        return default_schema

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                logger.warning(f"Watchlist file at {filepath} is empty. Returning default schema.")
                return default_schema
            data = json.loads(content)

            if not isinstance(data, dict) or "items" not in data:
                logger.warning(f"Watchlist file at {filepath} missing 'items' key. Resetting to default.")
                return default_schema

            return data
    except Exception as e:
        logger.error(f"Error reading watchlist file at {filepath}: {e}. Returning default schema.")
        return default_schema

def save_watchlist(watchlist_data: Dict[str, Any], filepath: str = DEFAULT_WATCHLIST_FILE) -> bool:
    """
    Atomically writes watchlist data to JSON file via temporary file replacement.
    """
    try:
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        clean_data = sanitize_state_for_storage(watchlist_data)

        # Write to temporary file in the same directory for atomic rename
        with tempfile.NamedTemporaryFile("w", dir=dir_path or ".", delete=False, encoding="utf-8") as tmp_file:
            tmp_path = tmp_file.name
            json.dump(clean_data, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        # Atomic replace
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        logger.error(f"Failed to atomically save watchlist to {filepath}: {e}")
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False

def add_watchlist_item(
    question: str,
    priorities_input: str,
    criteria_weights: Dict[str, int],
    baseline_state: Optional[ResearchState] = None,
    title: Optional[str] = None,
    search_engine: str = "google_light",
    llm_model: str = "gemini-2.5-flash",
    filepath: str = DEFAULT_WATCHLIST_FILE
) -> Dict[str, Any]:
    """
    Creates and persists a new watched research item.
    """
    watchlist = load_watchlist(filepath)
    item_id = f"watch_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    baseline_run = None
    if baseline_state and baseline_state.success:
        baseline_run = {
            "run_id": f"run_base_{uuid.uuid4().hex[:6]}",
            "timestamp": now_iso,
            "weighted_scores": getattr(baseline_state, "weighted_scores", {}),
            "evaluations": baseline_state.evaluations,
            "organic_results": baseline_state.organic_results,
            "rag_passages": baseline_state.rag_passages,
            "final_report": baseline_state.final_report,
            "matrix_md": baseline_state.matrix_md
        }

    item_title = title or (question[:50] + ("..." if len(question) > 50 else ""))

    item_data = {
        "id": item_id,
        "title": item_title,
        "question": question,
        "priorities_input": priorities_input,
        "criteria_weights": criteria_weights,
        "search_engine": search_engine,
        "llm_model": llm_model,
        "created_at": now_iso,
        "last_run_at": now_iso if baseline_run else None,
        "baseline_run": baseline_run,
        "latest_drift": {"severity": "NONE", "summary": "Baseline established."} if baseline_run else {"severity": "UNKNOWN", "summary": "No baseline established yet."},
        "history": [baseline_run] if baseline_run else []
    }

    watchlist["items"][item_id] = item_data
    save_watchlist(watchlist, filepath)
    return item_data

def get_watchlist_item(item_id: str, filepath: str = DEFAULT_WATCHLIST_FILE) -> Optional[Dict[str, Any]]:
    """Retrieves a single watchlist item by ID."""
    watchlist = load_watchlist(filepath)
    return watchlist.get("items", {}).get(item_id)

def list_watchlist_items(filepath: str = DEFAULT_WATCHLIST_FILE) -> List[Dict[str, Any]]:
    """Returns all watched items sorted by creation time descending."""
    watchlist = load_watchlist(filepath)
    items = list(watchlist.get("items", {}).values())
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items

def delete_watchlist_item(item_id: str, filepath: str = DEFAULT_WATCHLIST_FILE) -> bool:
    """Deletes a watchlist item by ID."""
    watchlist = load_watchlist(filepath)
    if item_id in watchlist.get("items", {}):
        del watchlist["items"][item_id]
        return save_watchlist(watchlist, filepath)
    return False

def record_watchlist_run(
    item_id: str,
    new_state: ResearchState,
    drift_analysis: Optional[Dict[str, Any]] = None,
    max_history: int = 10,
    filepath: str = DEFAULT_WATCHLIST_FILE
) -> bool:
    """
    Appends a completed research run state to item history and updates drift status.
    """
    watchlist = load_watchlist(filepath)
    item = watchlist.get("items", {}).get(item_id)
    if not item:
        logger.warning(f"Item {item_id} not found in watchlist.")
        return False

    if not new_state.success:
        logger.warning(f"Run for item {item_id} failed. Preserving existing baseline & history.")
        return False

    now_iso = datetime.now(timezone.utc).isoformat()

    new_run = {
        "run_id": f"run_{uuid.uuid4().hex[:6]}",
        "timestamp": now_iso,
        "weighted_scores": getattr(new_state, "weighted_scores", {}),
        "evaluations": new_state.evaluations,
        "organic_results": new_state.organic_results,
        "rag_passages": new_state.rag_passages,
        "final_report": new_state.final_report,
        "matrix_md": new_state.matrix_md,
        "drift_analysis": drift_analysis or {}
    }

    # Set as baseline if no baseline existed
    if not item.get("baseline_run"):
        item["baseline_run"] = new_run

    item["last_run_at"] = now_iso
    if drift_analysis:
        item["latest_drift"] = {
            "severity": drift_analysis.get("severity", "NONE"),
            "summary": drift_analysis.get("summary", "No significant drift.")
        }

    if "history" not in item or not isinstance(item["history"], list):
        item["history"] = []

    item["history"].append(new_run)
    # Cap history retention
    if len(item["history"]) > max_history:
        item["history"] = item["history"][-max_history:]

    watchlist["items"][item_id] = item
    return save_watchlist(watchlist, filepath)
