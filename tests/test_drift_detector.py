import unittest
from src.drift_detector import (
    detect_evidence_drift,
    SEVERITY_NONE,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH
)

class TestDriftDetector(unittest.TestCase):

    def setUp(self):
        self.baseline = {
            "weighted_scores": {"Option A": 4.0, "Option B": 3.0},
            "evaluations": {
                "Option A": {"Speed": 4.0, "Cost": 4.0},
                "Option B": {"Speed": 3.0, "Cost": 3.0}
            },
            "organic_results": [
                {
                    "title": "Page 1",
                    "link": "https://example.com/1",
                    "snippet": "Original snippet 1 text"
                },
                {
                    "title": "Page 2",
                    "link": "https://example.com/2",
                    "snippet": "Original snippet 2 text"
                }
            ]
        }

    def test_first_run_fallback(self):
        res = detect_evidence_drift(None, self.baseline)
        self.assertTrue(res["is_first_run"])
        self.assertEqual(res["severity"], SEVERITY_NONE)

    def test_no_drift(self):
        latest = dict(self.baseline)
        res = detect_evidence_drift(self.baseline, latest)
        self.assertFalse(res["is_first_run"])
        self.assertEqual(res["severity"], SEVERITY_NONE)
        self.assertEqual(res["max_score_abs_delta"], 0.0)
        self.assertFalse(res["rank_flip"])

    def test_low_drift_new_url_and_snippet_text(self):
        latest = {
            "weighted_scores": {"Option A": 4.0, "Option B": 3.0},
            "evaluations": self.baseline["evaluations"],
            "organic_results": [
                {
                    "title": "Page 1",
                    "link": "https://example.com/1",
                    "snippet": "Updated snippet 1 text"  # Changed snippet
                },
                {
                    "title": "Page 3 (New)",
                    "link": "https://example.com/3",  # New URL
                    "snippet": "Snippet 3"
                }
            ]
        }
        res = detect_evidence_drift(self.baseline, latest)
        self.assertEqual(res["severity"], SEVERITY_LOW)
        self.assertIn("https://example.com/3", res["url_drift"]["new_urls"])
        self.assertIn("https://example.com/2", res["url_drift"]["removed_urls"])
        self.assertEqual(len(res["snippet_drift"]), 1)
        self.assertIn("Search Engine Snippet Update", res["snippet_drift"][0]["note"])

    def test_medium_drift_score_shift_under_threshold(self):
        latest = {
            "weighted_scores": {"Option A": 4.3, "Option B": 3.2},  # max delta = +0.3 <= 0.5
            "evaluations": {},
            "organic_results": self.baseline["organic_results"]
        }
        res = detect_evidence_drift(self.baseline, latest)
        self.assertEqual(res["severity"], SEVERITY_MEDIUM)
        self.assertEqual(res["max_score_abs_delta"], 0.3)
        self.assertFalse(res["rank_flip"])

    def test_high_drift_score_shift_over_threshold(self):
        latest = {
            "weighted_scores": {"Option A": 4.6, "Option B": 3.0},  # max delta = +0.6 > 0.5
            "evaluations": {},
            "organic_results": self.baseline["organic_results"]
        }
        res = detect_evidence_drift(self.baseline, latest)
        self.assertEqual(res["severity"], SEVERITY_HIGH)
        self.assertEqual(res["max_score_abs_delta"], 0.6)

    def test_high_drift_recommendation_rank_flip(self):
        latest = {
            "weighted_scores": {"Option A": 3.8, "Option B": 4.5},  # Top flipped to Option B
            "evaluations": {},
            "organic_results": self.baseline["organic_results"]
        }
        res = detect_evidence_drift(self.baseline, latest)
        self.assertEqual(res["severity"], SEVERITY_HIGH)
        self.assertTrue(res["rank_flip"])
        self.assertEqual(res["top_candidate_baseline"], "Option A")
        self.assertEqual(res["top_candidate_latest"], "Option B")

    def test_dict_score_subtraction_bug_regression(self):
        """
        Regression test: Verify baseline or latest runs with dictionary-of-dictionaries
        or empty weighted_scores with evaluations do not raise TypeError: dict - dict.
        """
        baseline_with_evals_only = {
            "weighted_scores": {},
            "evaluations": {
                "DuckDB": {"Speed": 4.8, "Memory": 4.8},
                "PostgreSQL": {"Speed": 2.5, "Memory": 2.5}
            },
            "organic_results": self.baseline["organic_results"]
        }
        latest_with_nested_dicts = {
            "weighted_scores": {
                "DuckDB": {"option": "DuckDB", "overall_score": 4.8, "breakdown": {}},
                "PostgreSQL": {"option": "PostgreSQL", "overall_score": 2.5, "breakdown": {}}
            },
            "evaluations": {},
            "organic_results": self.baseline["organic_results"]
        }
        res = detect_evidence_drift(baseline_with_evals_only, latest_with_nested_dicts)
        self.assertFalse(res["is_first_run"])
        self.assertEqual(res["severity"], SEVERITY_NONE)
        self.assertEqual(res["score_drift"]["DuckDB"]["delta"], 0.0)
        self.assertEqual(res["score_drift"]["PostgreSQL"]["delta"], 0.0)

    def test_missing_scores_handling(self):
        """
        Verify missing option scores are reported as 'N/A' rather than inventing zero deltas.
        """
        latest_missing_opt_b = {
            "weighted_scores": {"Option A": 4.0},
            "evaluations": {},
            "organic_results": self.baseline["organic_results"]
        }
        res = detect_evidence_drift(self.baseline, latest_missing_opt_b)
        self.assertIn("Option B", res["score_drift"])
        self.assertEqual(res["score_drift"]["Option B"]["baseline_score"], 3.0)
        self.assertEqual(res["score_drift"]["Option B"]["latest_score"], "N/A")
        self.assertEqual(res["score_drift"]["Option B"]["delta"], "N/A")

    def test_malformed_scores_handling(self):
        """
        Verify string scores ("4.5") parse correctly while malformed values ("invalid", None) report 'N/A'.
        """
        baseline_malformed = {
            "weighted_scores": {"Option A": "4.0", "Option B": "invalid_score"},
            "organic_results": self.baseline["organic_results"]
        }
        latest_valid = {
            "weighted_scores": {"Option A": 4.2, "Option B": 3.5},
            "organic_results": self.baseline["organic_results"]
        }
        res = detect_evidence_drift(baseline_malformed, latest_valid)
        self.assertEqual(res["score_drift"]["Option A"]["delta"], 0.2)
        self.assertEqual(res["score_drift"]["Option B"]["baseline_score"], "N/A")
        self.assertEqual(res["score_drift"]["Option B"]["delta"], "N/A")

    def test_list_of_dicts_score_structure(self):
        """
        Verify weighted_scores passed as a list of dicts (e.g. rankings output) is parsed cleanly.
        """
        baseline_list = {
            "weighted_scores": [
                {"option": "Option A", "overall_score": 4.0},
                {"option": "Option B", "overall_score": 3.0}
            ],
            "organic_results": self.baseline["organic_results"]
        }
        latest_list = {
            "weighted_scores": [
                {"option": "Option A", "overall_score": 4.5},
                {"option": "Option B", "overall_score": 3.0}
            ],
            "organic_results": self.baseline["organic_results"]
        }
        res = detect_evidence_drift(baseline_list, latest_list)
        self.assertEqual(res["score_drift"]["Option A"]["delta"], 0.5)
        self.assertEqual(res["score_drift"]["Option B"]["delta"], 0.0)
        self.assertEqual(res["severity"], SEVERITY_MEDIUM)

if __name__ == "__main__":
    unittest.main()
