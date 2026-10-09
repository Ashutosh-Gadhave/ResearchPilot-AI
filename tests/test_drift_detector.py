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

if __name__ == "__main__":
    unittest.main()
