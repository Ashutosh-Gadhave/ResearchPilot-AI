import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def parse_criteria(priorities_input: str) -> List[str]:
    """
    Parses user priorities input into a list of clean criteria names.
    Supports comma-separated or semicolon-separated strings.
    """
    if not priorities_input or not priorities_input.strip():
        return ["Performance", "Cost Efficiency", "Ease of Use", "Reliability"]
    
    raw_tokens = [c.strip() for c in priorities_input.replace(";", ",").split(",")]
    criteria = [c for c in raw_tokens if c]
    return criteria if criteria else ["Performance", "Cost Efficiency", "Ease of Use", "Reliability"]

def calculate_weighted_decision(
    candidates_evaluations: Dict[str, Dict[str, float]],
    criteria_weights: Dict[str, int]
) -> Dict[str, Any]:
    """
    Calculates normalized weighted scores for candidate options.
    
    Formula:
      Weighted Score (O) = Sum(Weight(c) * Score(O, c)) / Sum(Weight(c))
      where Weight(c) in [1, 5] and Score(O, c) in [1.0, 5.0].
      
    Returns a sorted ranking dictionary with detailed score breakdowns.
    """
    if not candidates_evaluations or not criteria_weights:
        return {
            "rankings": [],
            "weighted_scores": {},
            "total_weight": 0,
            "scoring_explanation": "Insufficient data to compute weighted decision matrix."
        }

    total_weight = sum(criteria_weights.values())
    if total_weight <= 0:
        total_weight = 1

    results = {}
    rankings = []

    for option, scores in candidates_evaluations.items():
        weighted_sum = 0.0
        breakdown = {}
        
        for crit, weight in criteria_weights.items():
            score = float(scores.get(crit, 3.0))
            # Clamp score between 1.0 and 5.0
            score = max(1.0, min(5.0, score))
            breakdown[crit] = {
                "score": round(score, 2),
                "weight": weight,
                "weighted_contribution": round(score * weight, 2)
            }
            weighted_sum += score * weight

        overall_score = round(weighted_sum / total_weight, 2)
        
        results[option] = {
            "option": option,
            "overall_score": overall_score,
            "breakdown": breakdown
        }
        
        rankings.append({
            "option": option,
            "overall_score": overall_score
        })

    # Sort rankings descending by overall_score
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)

    explanation = (
        f"Scores are normalized on a 1.0–5.0 scale using user criterion weights (total weight = {total_weight}). "
        "Scores reflect LLM-assisted evaluation grounded in retrieved search snippets."
    )

    return {
        "rankings": rankings,
        "weighted_scores": results,
        "total_weight": total_weight,
        "scoring_explanation": explanation
    }

def format_decision_matrix_markdown(
    candidates_evaluations: Dict[str, Dict[str, float]],
    criteria_weights: Dict[str, int]
) -> str:
    """
    Renders a GitHub-Flavored Markdown table of the Weighted Decision Matrix.
    """
    calculation = calculate_weighted_decision(candidates_evaluations, criteria_weights)
    rankings = calculation["rankings"]
    weighted_scores = calculation["weighted_scores"]

    if not rankings:
        return "No evaluation matrix available."

    criteria_names = list(criteria_weights.keys())
    
    # Table Header
    header = "| Candidate Option | " + " | ".join([f"{c} (w={criteria_weights[c]})" for c in criteria_names]) + " | **Overall Score (1-5)** | Rank |\n"
    divider = "| :--- | " + " | ".join([":---:" for _ in criteria_names]) + " | :---: | :---: |\n"

    rows = []
    for rank_idx, rank_item in enumerate(rankings, start=1):
        opt = rank_item["option"]
        opt_data = weighted_scores[opt]
        overall = opt_data["overall_score"]
        
        row_scores = []
        for c in criteria_names:
            score = opt_data["breakdown"].get(c, {}).get("score", "-")
            row_scores.append(str(score))

        badge = "🏆 1st" if rank_idx == 1 else f"#{rank_idx}"
        row = f"| **{opt}** | " + " | ".join(row_scores) + f" | **{overall} / 5.0** | {badge} |"
        rows.append(row)

    matrix_md = header + divider + "\n".join(rows) + "\n\n"
    matrix_md += f"_*Scoring Method*: {calculation['scoring_explanation']}_\n"
    return matrix_md
