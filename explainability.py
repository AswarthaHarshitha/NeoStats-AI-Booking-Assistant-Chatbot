from typing import Dict, Any


def compute_explainability_score(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a simple explainability score and breakdown from booking `state`.

    Score is 0-100 where higher is more explainable / lower risk.
    Components:
    - average confidence (weighted)
    - ambiguity penalty per ambiguous token
    - missing fields penalty
    """
    confidences = state.get("confidences", {}) or {}
    ambiguities = state.get("ambiguities", []) or []

    # average confidence across known fields
    if confidences:
        vals = [v for v in confidences.values() if isinstance(v, (int, float))]
        avg_conf = sum(vals) / len(vals) if vals else 0.0
    else:
        avg_conf = 0.0

    # penalties
    ambiguity_penalty = min(len(ambiguities) * 0.15, 0.45)  # up to 45% penalty
    missing = [k for k, v in state.items() if k in ("service", "date", "time", "location") and not v]
    missing_penalty = min(len(missing) * 0.1, 0.3)

    # compute raw score in 0-1
    raw = avg_conf * (1.0 - ambiguity_penalty - missing_penalty)
    score = max(0.0, min(1.0, raw)) * 100.0

    breakdown = {
        "avg_confidence": round(avg_conf * 100, 2),
        "ambiguity_count": len(ambiguities),
        "ambiguity_penalty_pct": round(ambiguity_penalty * 100, 2),
        "missing_count": len(missing),
        "missing_penalty_pct": round(missing_penalty * 100, 2),
        "score": round(score, 2)
    }

    return breakdown
