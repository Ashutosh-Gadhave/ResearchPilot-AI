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
    candidates_evaluations: Dict[str, Dict[str, Any]],
    criteria_weights: Dict[str, int]
) -> Dict[str, Any]:
    """
    Calculates deterministic normalized weighted scores for candidate options.
    
    Formula:
      Weighted Score (O) = Sum(Weight(c) * Score(O, c)) / Sum(Weight(c))
      where Weight(c) in [1, 5] and Score(O, c) in [1.0, 5.0].
      
    If evidence for a criterion is missing, it is explicitly flagged with a baseline estimate.
    """
    if not candidates_evaluations or not criteria_weights:
        return {
            "rankings": [],
            "weighted_scores": {},
            "total_weight": 0,
            "missing_evidence_summary": {},
            "scoring_explanation": "Insufficient data to compute weighted decision matrix."
        }

    total_weight = sum(criteria_weights.values())
    if total_weight <= 0:
        total_weight = 1

    results = {}
    rankings = []
    missing_evidence_summary = {}

    for option, scores in candidates_evaluations.items():
        weighted_sum = 0.0
        breakdown = {}
        missing_criteria = []
        
        for crit, weight in criteria_weights.items():
            raw_score = scores.get(crit) if isinstance(scores, dict) else None
            
            if raw_score is None:
                has_evidence = False
                score = 3.0  # Neutral baseline estimate for missing evidence
                missing_criteria.append(crit)
            else:
                has_evidence = True
                try:
                    score = float(raw_score)
                except (ValueError, TypeError):
                    score = 3.0
                    has_evidence = False
                    missing_criteria.append(crit)

            # Clamp score between 1.0 and 5.0
            score = max(1.0, min(5.0, score))
            
            breakdown[crit] = {
                "score": round(score, 2),
                "weight": weight,
                "has_evidence": has_evidence,
                "weighted_contribution": round(score * weight, 2)
            }
            weighted_sum += score * weight

        overall_score = round(weighted_sum / total_weight, 2)
        
        results[option] = {
            "option": option,
            "overall_score": overall_score,
            "breakdown": breakdown,
            "has_missing_evidence": len(missing_criteria) > 0,
            "missing_criteria": missing_criteria
        }
        
        if missing_criteria:
            missing_evidence_summary[option] = missing_criteria

        rankings.append({
            "option": option,
            "overall_score": overall_score,
            "has_missing_evidence": len(missing_criteria) > 0
        })

    # Sort rankings deterministically descending by overall_score
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)

    has_any_missing = len(missing_evidence_summary) > 0
    missing_note = " ⚠️ Some criterion ratings indicate limited search snippet evidence and rely on baseline estimates." if has_any_missing else ""

    explanation = (
        f"Weighted overall scores calculated deterministically in Python on a 1.0–5.0 scale (total criteria weight = {total_weight})."
        f"{missing_note}"
    )

    return {
        "rankings": rankings,
        "weighted_scores": results,
        "total_weight": total_weight,
        "missing_evidence_summary": missing_evidence_summary,
        "scoring_explanation": explanation
    }

def format_decision_matrix_markdown(
    candidates_evaluations: Dict[str, Dict[str, Any]],
    criteria_weights: Dict[str, int]
) -> str:
    """
    Renders a GitHub-Flavored Markdown table of the Weighted Decision Matrix with explicit evidence flags.
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
            crit_info = opt_data["breakdown"].get(c, {})
            score = crit_info.get("score", 3.0)
            has_ev = crit_info.get("has_evidence", True)
            
            display_str = f"{score}" if has_ev else f"{score}*"
            row_scores.append(display_str)

        badge = "🏆 1st" if rank_idx == 1 else f"#{rank_idx}"
        row = f"| **{opt}** | " + " | ".join(row_scores) + f" | **{overall} / 5.0** | {badge} |"
        rows.append(row)

    matrix_md = header + divider + "\n".join(rows) + "\n\n"
    matrix_md += f"_*Scoring Methodology*: {calculation['scoring_explanation']}_\n"
    
    if calculation.get("missing_evidence_summary"):
        matrix_md += "\n_*Note*: Criteria values marked with `*` indicate baseline estimates due to unverified search snippet evidence._\n"

    return matrix_md
