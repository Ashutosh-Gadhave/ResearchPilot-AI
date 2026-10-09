import unittest
from unittest.mock import patch, MagicMock
from src.agents import (
    ResearchState,
    PlannerAgent,
    ResearcherAgent,
    DecisionCriticAgent,
    run_research_pilot_agent_workflow
)

class TestMultiAgentWorkflow(unittest.TestCase):

    def test_research_state_initialization(self):
        state = ResearchState(
            question="Postgres vs DuckDB",
            priorities_input="Speed, Memory",
            criteria_weights={"Speed": 5, "Memory": 4}
        )
        self.assertEqual(state.question, "Postgres vs DuckDB")
        self.assertEqual(state.searches_executed, 0)
        self.assertEqual(state.max_search_budget, 4)

    @patch("src.agents.genai.Client")
    def test_planner_agent_output_validation(self, mock_genai_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"options": ["Postgres", "DuckDB"], "queries": ["Postgres vs DuckDB speed", "Postgres vs DuckDB memory"]}\n```'
        mock_client.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client

        state = ResearchState("Postgres vs DuckDB", "Speed", {"Speed": 5})
        planner = PlannerAgent(api_key="fake_key")
        plan = planner.plan(state)

        self.assertEqual(len(state.planned_queries), 2)
        self.assertIn("Postgres vs DuckDB speed", state.planned_queries)
        self.assertEqual(state.options_compared, ["Postgres", "DuckDB"])

    @patch("src.agents.execute_search")
    def test_researcher_agent_deduplication_and_budget(self, mock_execute_search):
        # Return overlapping URLs to test deduplication
        mock_execute_search.return_value = {
            "success": True,
            "organic_results": [
                {"title": "Result 1", "link": "https://example.com/p1", "snippet": "s1"},
                {"title": "Result 2", "link": "https://example.com/p2", "snippet": "s2"}
            ]
        }

        state = ResearchState("Test Question", "Speed", {"Speed": 5}, max_search_budget=2)
        researcher = ResearcherAgent()
        
        # Search 1
        researcher.search_queries(state, ["query 1"], num_per_query=5)
        self.assertEqual(len(state.organic_results), 2)
        self.assertEqual(state.searches_executed, 1)

        # Search 2 (with duplicate URL)
        mock_execute_search.return_value = {
            "success": True,
            "organic_results": [
                {"title": "Result 1 Duplicate", "link": "https://example.com/p1", "snippet": "s1"},
                {"title": "Result 3 New", "link": "https://example.com/p3", "snippet": "s3"}
            ]
        }
        researcher.search_queries(state, ["query 2"], num_per_query=5)
        
        # Should deduplicate https://example.com/p1 -> Total unique = 3
        self.assertEqual(len(state.organic_results), 3)
        self.assertEqual(state.searches_executed, 2)

        # Search 3 (Exceeding max_search_budget=2)
        researcher.search_queries(state, ["query 3"], num_per_query=5)
        # Should not execute search 3 because budget limit reached
        self.assertEqual(state.searches_executed, 2)

    def test_critic_agent_gap_detection(self):
        state = ResearchState("Test Q", "Query speed, Low memory consumption", {"Query speed": 5})
        state.organic_results = [
            {"title": "T1", "link": "L1", "snippet": "Discusses query speed performance"}
        ]
        state.searches_executed = 1
        state.max_search_budget = 4

        critic = DecisionCriticAgent()
        gap_res = critic.evaluate_gaps(state)

        # 'Low memory consumption' missing from snippets -> triggers follow up
        self.assertTrue(gap_res["needs_follow_up"])
        self.assertIsNotNone(gap_res["follow_up_query"])

    @patch("src.agents.generate_decision_report")
    @patch("src.agents.execute_search")
    @patch("src.agents.genai.Client")
    def test_full_orchestrator_workflow_mocked(self, mock_genai, mock_search, mock_report):
        # Mock Planner response
        mock_genai_instance = MagicMock()
        mock_plan_resp = MagicMock()
        mock_plan_resp.text = '```json\n{"options": ["Postgres", "DuckDB"], "queries": ["Postgres vs DuckDB"]}\n```'
        mock_genai_instance.models.generate_content.return_value = mock_plan_resp
        mock_genai.return_value = mock_genai_instance

        # Mock Search response
        mock_search.return_value = {
            "success": True,
            "organic_results": [{"title": "Postgres vs DuckDB speed", "link": "https://example.com", "snippet": "Query speed benchmark"}]
        }

        # Mock Final Report response
        mock_report.return_value = {
            "success": True,
            "error": None,
            "report": "# 🏆 Executive Recommendation\nDuckDB",
            "matrix_md": "| Candidate | Overall Score |\n| DuckDB | 4.8 |",
            "evaluations": {"DuckDB": {"Speed": 5.0}},
            "model_used": "gemini-3.8-flash"
        }

        state = run_research_pilot_agent_workflow(
            question="Postgres vs DuckDB for analytics",
            priorities_input="Query speed",
            criteria_weights={"Query speed": 5},
            api_key_serpapi="fake_serpapi",
            api_key_gemini="fake_gemini"
        )

        self.assertTrue(state.success)
        self.assertIn("Executive Recommendation", state.final_report)
        self.assertEqual(state.searches_executed, 1)
        self.assertGreater(len(state.stage_logs), 0)

if __name__ == "__main__":
    unittest.main()
