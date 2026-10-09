import os
import json
import re
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from dotenv import load_dotenv
from google import genai
from google.genai import errors

from src.search_engine import execute_search
from src.llm_analyzer import generate_decision_report, extract_json_block
from src.scorer import parse_criteria, calculate_weighted_decision, format_decision_matrix_markdown

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class ResearchState:
    """State object passed between multi-agent pipeline stages."""
    question: str
    priorities_input: str
    criteria_weights: Dict[str, int]
    search_engine: str = "google_light"
    llm_model: str = "gemini-2.5-flash"
    api_key_serpapi: Optional[str] = None
    api_key_gemini: Optional[str] = None
    
    # Execution Tracking & Budgeting
    max_search_budget: int = 4
    searches_executed: int = 0
    
    # Stage Data
    options_compared: List[str] = field(default_factory=list)
    planned_queries: List[str] = field(default_factory=list)
    organic_results: List[Dict[str, Any]] = field(default_factory=list)
    seen_urls: Set[str] = field(default_factory=set)
    
    follow_up_performed: bool = False
    follow_up_query: Optional[str] = None
    
    final_report: str = ""
    matrix_md: str = ""
    evaluations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    stage_logs: List[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    def log_stage(self, msg: str):
        logger.info(msg)
        self.stage_logs.append(msg)


class PlannerAgent:
    """Agent 1: Deconstructs question and generates focused search queries."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name

    def plan(self, state: ResearchState) -> Dict[str, Any]:
        state.log_stage("🧠 [PlannerAgent] Deconstructing research question and generating query plan...")
        
        parsed_criteria = parse_criteria(state.priorities_input)
        
        if not self.api_key:
            # Fallback planning without LLM
            state.options_compared = ["Option A", "Option B"]
            state.planned_queries = [state.question]
            return {"options": state.options_compared, "queries": state.planned_queries}

        prompt = f"""You are the **Research Planner Agent** for ResearchPilot AI.
Analyze the user's decision prompt and generate a focused search plan.

### User Prompt
- **Question**: {state.question}
- **Evaluation Criteria**: {", ".join(parsed_criteria)}

### Instructions
1. Identify 2-3 candidate options being compared (if applicable).
2. Generate 1 to 3 concise, highly targeted web search queries to find benchmark data, trade-offs, and comparison evidence.

Return ONLY a JSON block:
```json
{{
  "options": ["Candidate 1", "Candidate 2"],
  "queries": [
    "query 1 for benchmark data",
    "query 2 for trade-offs"
  ],
  "plan_rationale": "Brief rationale for query selection"
}}
```
"""
        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw_text = response.text or ""
            
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            plan_data = json.loads(json_match.group(1)) if json_match else {}
            
            state.options_compared = plan_data.get("options", ["Candidate A", "Candidate B"])
            queries = plan_data.get("queries", [])
            
            # Bound planned queries to max 3 to conserve budget
            state.planned_queries = queries[:3] if queries else [state.question]
            state.log_stage(f"✓ [PlannerAgent] Generated {len(state.planned_queries)} queries for options: {state.options_compared}")
            return plan_data

        except Exception as e:
            logger.warning(f"PlannerAgent LLM fallback: {e}")
            state.options_compared = ["Option A", "Option B"]
            state.planned_queries = [state.question]
            state.log_stage(f"⚠️ [PlannerAgent] Fallback to direct query: {state.question}")
            return {"options": state.options_compared, "queries": state.planned_queries}


class ResearcherAgent:
    """Agent 2: Executes SerpApi searches, normalizes, and deduplicates evidence."""
    
    def search_queries(self, state: ResearchState, queries: List[str], num_per_query: int = 5) -> List[Dict[str, Any]]:
        new_items = []
        for q in queries:
            if state.searches_executed >= state.max_search_budget:
                state.log_stage(f"⚠️ [ResearcherAgent] Reached max search budget limit ({state.max_search_budget}).")
                break
                
            res = execute_search(
                query=q,
                engine=state.search_engine,
                num_results=num_per_query,
                api_key=state.api_key_serpapi,
                use_mcp=True
            )
            state.searches_executed += 1
            
            mcp_tag = " (via SerpApi MCP Protocol)" if res.get("via_mcp") else " (via SerpApi SDK fallback)"
            
            if res["success"]:
                for item in res["organic_results"]:
                    link = item.get("link", "#")
                    if link not in state.seen_urls and link != "#":
                        state.seen_urls.add(link)
                        item_copy = dict(item)
                        item_copy["query_origin"] = q
                        state.organic_results.append(item_copy)
                        new_items.append(item_copy)
                state.log_stage(f"✓ [ResearcherAgent] Retrieved {len(res['organic_results'])} items for '{q}'{mcp_tag}")
        
        state.log_stage(f"✓ [ResearcherAgent] Total deduplicated evidence items: {len(state.organic_results)}")
        return new_items


class DecisionCriticAgent:
    """Agent 3: Critiques evidence, identifies missing data, requests follow-up, and generates report."""
    
    def evaluate_gaps(self, state: ResearchState) -> Dict[str, Any]:
        state.log_stage("⚖️ [DecisionCriticAgent] Auditing retrieved evidence for missing data or unsupported claims...")
        
        # If budget depleted or no evidence, skip follow-up request
        if state.searches_executed >= state.max_search_budget or not state.organic_results:
            return {"needs_follow_up": False, "follow_up_query": None}
            
        parsed_criteria = parse_criteria(state.priorities_input)
        
        # Check if key criteria appear in snippets
        combined_text = " ".join([item.get("snippet", "").lower() for item in state.organic_results])
        missing_crit = [c for c in parsed_criteria if c.lower() not in combined_text]
        
        if missing_crit and state.searches_executed < state.max_search_budget:
            follow_up = f"{state.question} {missing_crit[0]} benchmark comparison"
            state.follow_up_performed = True
            state.follow_up_query = follow_up
            state.log_stage(f"🔍 [DecisionCriticAgent] Identified missing evidence for '{missing_crit[0]}'. Requesting 1 targeted search: '{follow_up}'")
            return {"needs_follow_up": True, "follow_up_query": follow_up, "missing_criteria": missing_crit}
            
        state.log_stage("✓ [DecisionCriticAgent] Evidence audit complete. Proceeding to final scoring.")
        return {"needs_follow_up": False, "follow_up_query": None}

    def synthesize(self, state: ResearchState) -> Dict[str, Any]:
        state.log_stage("🏆 [DecisionCriticAgent] Generating deterministic decision matrix & final grounded report...")
        
        report_res = generate_decision_report(
            question=state.question,
            priorities_input=state.priorities_input,
            organic_results=state.organic_results,
            criteria_weights=state.criteria_weights,
            model_name=state.llm_model,
            api_key=state.api_key_gemini
        )
        
        if report_res["success"]:
            state.final_report = report_res["report"]
            state.matrix_md = report_res["matrix_md"]
            state.evaluations = report_res.get("evaluations", {})
            state.log_stage("✅ [DecisionCriticAgent] Report synthesis complete.")
        else:
            state.success = False
            state.error = report_res["error"]
            state.log_stage(f"❌ [DecisionCriticAgent] Report synthesis failed: {state.error}")
            
        return report_res


def run_research_pilot_agent_workflow(
    question: str,
    priorities_input: str,
    criteria_weights: Dict[str, int],
    search_engine: str = "google_light",
    llm_model: str = "gemini-2.5-flash",
    api_key_serpapi: Optional[str] = None,
    api_key_gemini: Optional[str] = None,
    max_search_budget: int = 4,
    status_callback: Optional[Callable[[str, str], None]] = None
) -> ResearchState:
    """
    Orchestrates Phase 1 Multi-Agent Workflow:
    1. PlannerAgent: Query Planning
    2. ResearcherAgent: Evidence Gathering & Deduplication
    3. DecisionCriticAgent: Evidence Audit & Gap Analysis
    4. Bounded Follow-up Search (Max 1 round)
    5. DecisionCriticAgent: Final Grounded Synthesis & Matrix Computation
    """
    state = ResearchState(
        question=question,
        priorities_input=priorities_input,
        criteria_weights=criteria_weights,
        search_engine=search_engine,
        llm_model=llm_model,
        api_key_serpapi=api_key_serpapi,
        api_key_gemini=api_key_gemini,
        max_search_budget=max_search_budget
    )
    
    def update_status(stage: str, msg: str):
        state.log_stage(f"[{stage}] {msg}")
        if status_callback:
            status_callback(stage, msg)

    try:
        # Stage 1: Planning
        update_status("PlannerAgent", "Analyzing question and generating targeted search query plan...")
        planner = PlannerAgent(api_key=state.api_key_gemini, model_name=state.llm_model)
        planner.plan(state)

        # Stage 2: Initial Evidence Gathering
        update_status("ResearcherAgent", f"Executing {len(state.planned_queries)} planned search queries via SerpApi...")
        researcher = ResearcherAgent()
        researcher.search_queries(state, state.planned_queries, num_per_query=5)

        if not state.organic_results:
            state.success = False
            state.error = "No search results retrieved during evidence gathering."
            return state

        # Stage 3: Decision Audit & Gap Identification
        update_status("DecisionCriticAgent", "Auditing evidence coverage against weighted decision criteria...")
        critic = DecisionCriticAgent()
        gap_res = critic.evaluate_gaps(state)

        # Stage 4: Optional Bounded Follow-up Search (Max 1 query)
        if gap_res.get("needs_follow_up") and gap_res.get("follow_up_query"):
            update_status("ResearcherAgent", f"Executing 1 targeted follow-up search: '{gap_res['follow_up_query']}'...")
            researcher.search_queries(state, [gap_res["follow_up_query"]], num_per_query=3)

        # Stage 5: Report Synthesis & Matrix Computation
        update_status("DecisionCriticAgent", "Finalizing deterministic weighted matrix and evidence report...")
        critic.synthesize(state)

    except Exception as e:
        logger.error(f"Agent Orchestrator Failure: {e}")
        state.success = False
        state.error = f"Agent workflow failed: {str(e)}"

    return state
