import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.watchlist import (
    load_watchlist,
    save_watchlist,
    add_watchlist_item,
    get_watchlist_item,
    list_watchlist_items,
    delete_watchlist_item,
    record_watchlist_run,
    sanitize_state_for_storage
)

class TestWatchlistPersistence(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.watchlist_file = os.path.join(self.tmp_dir.name, "test_watchlist.json")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_load_missing_file(self):
        data = load_watchlist(self.watchlist_file)
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["items"], {})

    def test_load_corrupted_file(self):
        with open(self.watchlist_file, "w", encoding="utf-8") as f:
            f.write("{invalid json content...")

        data = load_watchlist(self.watchlist_file)
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["items"], {})

    def test_atomic_save_and_read(self):
        payload = {"version": "1.0", "items": {"item1": {"title": "Test Item"}}}
        saved = save_watchlist(payload, self.watchlist_file)
        self.assertTrue(saved)
        self.assertTrue(os.path.exists(self.watchlist_file))

        loaded = load_watchlist(self.watchlist_file)
        self.assertIn("item1", loaded["items"])
        self.assertEqual(loaded["items"]["item1"]["title"], "Test Item")

    def test_sanitize_state_for_storage(self):
        sensitive_data = {
            "title": "Public Title",
            "api_key_serpapi": "secret_serp_key_123",
            "api_key_gemini": "secret_gemini_key_456",
            "nested": {
                "user_id": 42,
                "secret_token": "bearer_abc"
            }
        }
        cleaned = sanitize_state_for_storage(sensitive_data)
        self.assertIn("title", cleaned)
        self.assertNotIn("api_key_serpapi", cleaned)
        self.assertNotIn("api_key_gemini", cleaned)
        self.assertNotIn("secret_token", cleaned["nested"])
        self.assertEqual(cleaned["nested"]["user_id"], 42)

    def test_add_get_list_delete_item(self):
        # Add Item
        item = add_watchlist_item(
            question="PostgreSQL vs DuckDB",
            priorities_input="Speed, Memory",
            criteria_weights={"Speed": 4, "Memory": 3},
            filepath=self.watchlist_file
        )
        item_id = item["id"]
        self.assertTrue(item_id.startswith("watch_"))

        # Get Item
        retrieved = get_watchlist_item(item_id, self.watchlist_file)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["question"], "PostgreSQL vs DuckDB")

        # List Items
        all_items = list_watchlist_items(self.watchlist_file)
        self.assertEqual(len(all_items), 1)
        self.assertEqual(all_items[0]["id"], item_id)

        # Delete Item
        deleted = delete_watchlist_item(item_id, self.watchlist_file)
        self.assertTrue(deleted)
        self.assertIsNone(get_watchlist_item(item_id, self.watchlist_file))

    def test_record_watchlist_run_and_history_cap(self):
        item = add_watchlist_item(
            question="Next.js vs Remix",
            priorities_input="SEO",
            criteria_weights={"SEO": 4},
            filepath=self.watchlist_file
        )
        item_id = item["id"]

        mock_state = MagicMock()
        mock_state.success = True
        mock_state.weighted_scores = {"Next.js": 4.5, "Remix": 4.2}
        mock_state.evaluations = {"Next.js": {"SEO": 4.5}, "Remix": {"SEO": 4.2}}
        mock_state.organic_results = [{"title": "Next.js Docs", "link": "https://nextjs.org"}]
        mock_state.rag_passages = []
        mock_state.final_report = "Report text"
        mock_state.matrix_md = "| Matrix |"

        drift_info = {"severity": "LOW", "summary": "Minor URL addition."}

        ok = record_watchlist_run(item_id, mock_state, drift_info, max_history=3, filepath=self.watchlist_file)
        self.assertTrue(ok)

        updated_item = get_watchlist_item(item_id, self.watchlist_file)
        self.assertEqual(len(updated_item["history"]), 1)
        self.assertEqual(updated_item["latest_drift"]["severity"], "LOW")

    def test_record_watchlist_refresh_failure_preserves_history(self):
        from src.watchlist import record_watchlist_refresh_failure
        item = add_watchlist_item(
            question="Postgres vs DuckDB",
            priorities_input="Speed",
            criteria_weights={"Speed": 5},
            filepath=self.watchlist_file
        )
        item_id = item["id"]

        # Record initial successful run
        mock_state = MagicMock()
        mock_state.success = True
        mock_state.weighted_scores = {"DuckDB": 4.8}
        mock_state.evaluations = {"DuckDB": {"Speed": 4.8}}
        mock_state.organic_results = [{"title": "DuckDB Docs", "link": "https://duckdb.org"}]
        mock_state.rag_passages = []
        mock_state.final_report = "Base report"
        mock_state.matrix_md = "| Base Matrix |"
        record_watchlist_run(item_id, mock_state, {"severity": "NONE", "summary": "Baseline established."}, filepath=self.watchlist_file)

        # Record refresh failure
        recorded = record_watchlist_refresh_failure(item_id, "Gemini 503 error", filepath=self.watchlist_file)
        self.assertTrue(recorded)

        updated_item = get_watchlist_item(item_id, self.watchlist_file)
        self.assertEqual(len(updated_item["history"]), 1)  # History length preserved
        self.assertEqual(updated_item["latest_drift"]["severity"], "ERROR")
        self.assertIn("Gemini 503 error", updated_item["latest_drift"]["summary"])
        self.assertIsNotNone(updated_item["baseline_run"])  # Baseline preserved

if __name__ == "__main__":
    unittest.main()
