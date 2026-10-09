import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.watchlist import list_watchlist_items, get_watchlist_item, record_watchlist_run
from src.agents import run_research_pilot_agent_workflow
from src.drift_detector import detect_evidence_drift

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="ResearchPilot AI — Watchlist CLI Background Runner")
    parser.add_argument("--item_id", type=str, help="Specific watchlist item ID to rerun (if omitted, runs all)", default=None)
    parser.add_argument("--filepath", type=str, help="Path to watchlist.json", default=None)
    args = parser.parse_args()

    serpapi_key = os.getenv("SERPAPI_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    if not serpapi_key or not gemini_key:
        logger.error("❌ SERPAPI_API_KEY or GEMINI_API_KEY missing in environment/.env file.")
        sys.exit(1)

    kwargs = {}
    if args.filepath:
        kwargs["filepath"] = args.filepath

    items = list_watchlist_items(**kwargs)
    if args.item_id:
        items = [i for i in items if i["id"] == args.item_id]
        if not items:
            logger.error(f"❌ Item ID '{args.item_id}' not found in watchlist.")
            sys.exit(1)

    if not items:
        logger.info("ℹ️ No items found in watchlist to process.")
        return

    logger.info(f"🚀 Watchlist Runner started. Processing {len(items)} items...")
    success_count = 0
    fail_count = 0

    for idx, item in enumerate(items, start=1):
        item_id = item["id"]
        title = item.get("title", "Untitled")
        logger.info(f"[{idx}/{len(items)}] Rerunning '{title}' (ID: {item_id})...")

        baseline_run = item.get("baseline_run")

        try:
            agent_state = run_research_pilot_agent_workflow(
                question=item["question"],
                priorities_input=item["priorities_input"],
                criteria_weights=item.get("criteria_weights", {}),
                search_engine=item.get("search_engine", "google_light"),
                llm_model=item.get("llm_model", "gemini-2.5-flash"),
                api_key_serpapi=serpapi_key,
                api_key_gemini=gemini_key
            )

            if not agent_state.success:
                logger.warning(f"❌ Agent workflow failed for '{title}': {agent_state.error}")
                fail_count += 1
                continue

            latest_run_data = {
                "weighted_scores": getattr(agent_state, "weighted_scores", {}),
                "evaluations": agent_state.evaluations,
                "organic_results": agent_state.organic_results,
                "rag_passages": agent_state.rag_passages
            }

            drift_res = detect_evidence_drift(
                baseline_run=baseline_run,
                latest_run=latest_run_data,
                criteria_weights=item.get("criteria_weights")
            )

            saved_ok = record_watchlist_run(
                item_id=item_id,
                new_state=agent_state,
                drift_analysis=drift_res,
                **kwargs
            )

            if saved_ok:
                logger.info(f"✅ Success: '{title}' updated. Drift Severity: [{drift_res['severity']}] — {drift_res['summary']}")
                success_count += 1
            else:
                logger.warning(f"⚠️ Failed to save run snapshot for '{title}'.")
                fail_count += 1

        except Exception as e:
            logger.error(f"❌ Exception processing item '{title}': {e}")
            fail_count += 1

    logger.info(f"🏁 Watchlist Runner Complete. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
