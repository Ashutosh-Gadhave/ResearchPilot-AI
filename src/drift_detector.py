import logging
from typing import Dict, Any, List, Optional, Set

from src.scorer import calculate_weighted_decision

logger = logging.getLogger(__name__)

# Explicit Drift Severity Constants
SEVERITY_NONE = "NONE"
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"

def extract_urls_and_snippets(organic_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Extracts a mapping of URL -> {title, snippet} from search organic results.
    """
    url_map = {}
    for item in organic_results or []:
        url = item.get("link", "#")
        if url and url != "#":
            url_map[url] = {
                "title": item.get("title", "Untitled"),
                "snippet": item.get("snippet", "")
            }
    return url_map

def extract_numeric_score(val: Any) -> Optional[float]:
    """
    Safely extracts a numeric float score from various possible score types:
    - float / int
    - string representing a float (e.g. "4.5")
    - dict containing keys like 'overall_score', 'score', 'weighted_score', 'value'
    Returns None if score is missing, malformed, or unparseable.
    """
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except (ValueError, TypeError):
            return None
    if isinstance(val, dict):
        for key in ["overall_score", "score", "weighted_score", "value"]:
            if key in val:
                score = extract_numeric_score(val[key])
                if score is not None:
                    return score
        for v in val.values():
            score = extract_numeric_score(v)
            if score is not None:
                return score
    return None

def compute_option_scores_from_evaluations(
    evaluations: Dict[str, Dict[str, Any]],
    criteria_weights: Optional[Dict[str, int]] = None
) -> Dict[str, float]:
    """
    Computes overall weighted scores for options using src/scorer.py logic.
    Returns a dict mapping option_name -> numeric overall float score.
    """
    if not evaluations or not isinstance(evaluations, dict):
        return {}

    if not criteria_weights:
        # Extract criteria list from first option
        first_opt = next(iter(evaluations.values()), {})
        criteria_weights = {k: 3 for k in first_opt.keys()} if isinstance(first_opt, dict) else {}

    calc_res = calculate_weighted_decision(evaluations, criteria_weights)
    raw_weighted = calc_res.get("weighted_scores", {})
    scores = {}
    if isinstance(raw_weighted, dict):
        for opt, item in raw_weighted.items():
            num_s = extract_numeric_score(item)
            if num_s is not None:
                scores[opt] = num_s
    return scores

def extract_run_scores(
    run_data: Optional[Dict[str, Any]],
    criteria_weights: Optional[Dict[str, int]] = None
) -> Dict[str, Optional[float]]:
    """
    Extracts a mapping of option_name -> numeric_score (or None if invalid/missing)
    from a research run dict.
    Checks `weighted_scores` first; falls back to computing from `evaluations`.
    """
    if not run_data or not isinstance(run_data, dict):
        return {}

    scores: Dict[str, Optional[float]] = {}
    raw_weighted = run_data.get("weighted_scores")

    if isinstance(raw_weighted, dict) and raw_weighted:
        for opt, val in raw_weighted.items():
            scores[opt] = extract_numeric_score(val)
    elif isinstance(raw_weighted, list) and raw_weighted:
        for item in raw_weighted:
            if isinstance(item, dict) and "option" in item:
                opt_name = str(item["option"])
                scores[opt_name] = extract_numeric_score(item)

    # If no valid numeric scores extracted from weighted_scores, fallback to evaluations
    if not scores or all(v is None for v in scores.values()):
        evals = run_data.get("evaluations", {})
        if isinstance(evals, dict) and evals:
            computed = compute_option_scores_from_evaluations(evals, criteria_weights)
            for opt, val in computed.items():
                scores[opt] = extract_numeric_score(val)

    return scores

def detect_evidence_drift(
    baseline_run: Optional[Dict[str, Any]],
    latest_run: Dict[str, Any],
    criteria_weights: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Compares baseline research evidence and decision scores against latest research run.
    Returns deterministic drift metrics, deltas, rank flips, and severity level.
    """
    if not baseline_run or not baseline_run.get("organic_results"):
        return {
            "is_first_run": True,
            "severity": SEVERITY_NONE,
            "summary": "Baseline run established; no prior data to compare.",
            "url_drift": {"new_urls": [], "removed_urls": [], "retained_urls": []},
            "snippet_drift": [],
            "score_drift": {},
            "rank_flip": False,
            "top_candidate_baseline": None,
            "top_candidate_latest": None
        }

    # 1. URL & Evidence Source Drift
    base_url_map = extract_urls_and_snippets(baseline_run.get("organic_results", []))
    latest_url_map = extract_urls_and_snippets(latest_run.get("organic_results", []))

    base_urls = set(base_url_map.keys())
    latest_urls = set(latest_url_map.keys())

    new_urls = list(latest_urls - base_urls)
    removed_urls = list(base_urls - latest_urls)
    retained_urls = list(base_urls.intersection(latest_urls))

    # 2. Snippet Text Content Drift
    snippet_drift = []
    for url in retained_urls:
        base_snip = base_url_map[url]["snippet"]
        latest_snip = latest_url_map[url]["snippet"]
        if base_snip.strip() != latest_snip.strip():
            snippet_drift.append({
                "url": url,
                "title": latest_url_map[url]["title"],
                "baseline_snippet": base_snip,
                "latest_snippet": latest_snip,
                "note": "Search Engine Snippet Update (Not verified real-world factual change)"
            })

    # 3. Decision Matrix Score & Rank Drift
    base_scores = extract_run_scores(baseline_run, criteria_weights)
    latest_scores = extract_run_scores(latest_run, criteria_weights)

    all_options = sorted(list(set(base_scores.keys()).union(set(latest_scores.keys()))))
    score_drift = {}
    max_score_abs_delta = 0.0

    for opt in all_options:
        base_s = base_scores.get(opt)
        latest_s = latest_scores.get(opt)

        if base_s is not None and latest_s is not None:
            delta = round(latest_s - base_s, 3)
            score_drift[opt] = {
                "baseline_score": base_s,
                "latest_score": latest_s,
                "delta": delta
            }
            if abs(delta) > max_score_abs_delta:
                max_score_abs_delta = abs(delta)
        else:
            score_drift[opt] = {
                "baseline_score": base_s if base_s is not None else "N/A",
                "latest_score": latest_s if latest_s is not None else "N/A",
                "delta": "N/A"
            }

    # Determine Top Candidate Rank Flip (using only options with valid numeric scores)
    valid_base_scores = {k: v for k, v in base_scores.items() if v is not None}
    valid_latest_scores = {k: v for k, v in latest_scores.items() if v is not None}

    top_base = max(valid_base_scores.items(), key=lambda x: x[1])[0] if valid_base_scores else None
    top_latest = max(valid_latest_scores.items(), key=lambda x: x[1])[0] if valid_latest_scores else None
    rank_flip = (top_base is not None and top_latest is not None and top_base != top_latest)

    # 4. Deterministic Severity Threshold Classification
    # HIGH: Recommendation flipped OR max score delta > 0.50
    if rank_flip or max_score_abs_delta > 0.50:
        severity = SEVERITY_HIGH
        if rank_flip:
            summary = f"HIGH DRIFT: Top recommendation changed from '{top_base}' to '{top_latest}'."
        else:
            summary = f"HIGH DRIFT: Significant score shift detected (max delta: {max_score_abs_delta:+.3f} pts)."
    # MEDIUM: Moderate score shift (0.0 < delta <= 0.50)
    elif max_score_abs_delta > 0.0:
        severity = SEVERITY_MEDIUM
        summary = f"MEDIUM DRIFT: Score shift detected (max delta: {max_score_abs_delta:+.3f} pts)."
    # LOW: URL or snippet changes, but zero score change
    elif len(new_urls) > 0 or len(removed_urls) > 0 or len(snippet_drift) > 0:
        severity = SEVERITY_LOW
        summary = f"LOW DRIFT: Source URL or snippet updates detected ({len(new_urls)} new, {len(removed_urls)} removed), scores unchanged."
    # NONE: Zero score changes and zero URL/snippet changes
    else:
        severity = SEVERITY_NONE
        summary = "NO DRIFT: Search evidence and decision scores remain identical to baseline."

    return {
        "is_first_run": False,
        "severity": severity,
        "summary": summary,
        "url_drift": {
            "new_urls": new_urls,
            "removed_urls": removed_urls,
            "retained_urls": retained_urls,
            "count_new": len(new_urls),
            "count_removed": len(removed_urls)
        },
        "snippet_drift": snippet_drift,
        "score_drift": score_drift,
        "max_score_abs_delta": round(max_score_abs_delta, 3),
        "rank_flip": rank_flip,
        "top_candidate_baseline": top_base,
        "top_candidate_latest": top_latest
    }
