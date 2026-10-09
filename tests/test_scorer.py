import unittest
from src.scorer import parse_criteria, calculate_weighted_decision, format_decision_matrix_markdown

class TestDecisionScorer(unittest.TestCase):

    def test_parse_criteria_default(self):
        criteria = parse_criteria("")
        self.assertGreater(len(criteria), 0)
        self.assertIn("Performance", criteria)

    def test_parse_criteria_custom(self):
        criteria = parse_criteria("Query Speed, Low Memory; Zero Config")
        self.assertEqual(criteria, ["Query Speed", "Low Memory", "Zero Config"])

    def test_calculate_weighted_decision_math(self):
        evaluations = {
            "Option A": {"Speed": 5.0, "Cost": 3.0},
            "Option B": {"Speed": 2.0, "Cost": 5.0}
        }
        weights = {"Speed": 4, "Cost": 1}
        # Option A weighted = (5*4 + 3*1)/5 = 23/5 = 4.6
        # Option B weighted = (2*4 + 5*1)/5 = 13/5 = 2.6
        result = calculate_weighted_decision(evaluations, weights)
        self.assertEqual(len(result["rankings"]), 2)
        self.assertEqual(result["rankings"][0]["option"], "Option A")
        self.assertEqual(result["rankings"][0]["overall_score"], 4.6)
        self.assertEqual(result["rankings"][1]["option"], "Option B")
        self.assertEqual(result["rankings"][1]["overall_score"], 2.6)

    def test_missing_evidence_handling(self):
        evaluations = {
            "Option A": {"Speed": 4.5, "Cost": None},  # Cost evidence missing
            "Option B": {"Speed": 3.0, "Cost": 4.0}
        }
        weights = {"Speed": 3, "Cost": 2}
        result = calculate_weighted_decision(evaluations, weights)
        
        # Option A should be flagged for missing Cost evidence
        self.assertTrue(result["weighted_scores"]["Option A"]["has_missing_evidence"])
        self.assertIn("Cost", result["weighted_scores"]["Option A"]["missing_criteria"])
        self.assertIn("Option A", result["missing_evidence_summary"])
        
        # Verify matrix markdown displays asterisk indicator for missing evidence
        matrix_md = format_decision_matrix_markdown(evaluations, weights)
        self.assertIn("3.0*", matrix_md)
        self.assertIn("baseline estimates due to unverified search snippet evidence", matrix_md)

    def test_deterministic_scoring_consistency(self):
        evaluations = {
            "PostgreSQL": {"Speed": 4.0, "Cost": 4.0},
            "DuckDB": {"Speed": 5.0, "Cost": 5.0}
        }
        weights = {"Speed": 3, "Cost": 2}
        
        calc_result = calculate_weighted_decision(evaluations, weights)
        duckdb_score = calc_result["weighted_scores"]["DuckDB"]["overall_score"]
        postgres_score = calc_result["weighted_scores"]["PostgreSQL"]["overall_score"]
        
        matrix_md = format_decision_matrix_markdown(evaluations, weights)
        
        # Verify that deterministic Python calculated scores match the matrix table string exactly
        self.assertIn(f"{duckdb_score} / 5.0", matrix_md)
        self.assertIn(f"{postgres_score} / 5.0", matrix_md)

    def test_empty_evaluations(self):
        result = calculate_weighted_decision({}, {"Speed": 3})
        self.assertEqual(len(result["rankings"]), 0)
        self.assertIn("Insufficient data", result["scoring_explanation"])

    def test_format_decision_matrix_markdown(self):
        evaluations = {
            "PostgreSQL": {"Speed": 4.0, "Cost": 4.0},
            "DuckDB": {"Speed": 5.0, "Cost": 5.0}
        }
        weights = {"Speed": 3, "Cost": 2}
        matrix_md = format_decision_matrix_markdown(evaluations, weights)
        self.assertIn("DuckDB", matrix_md)
        self.assertIn("PostgreSQL", matrix_md)
        self.assertIn("Overall Score", matrix_md)
        self.assertIn("1st", matrix_md)

if __name__ == "__main__":
    unittest.main()
