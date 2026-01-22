from typing import Dict, Any, Optional


def generate_clarifying_question(state: Dict[str, Any]) -> Optional[str]:
    """Generate a single concise clarifying question from booking state.

    Looks at ambiguities, low confidence fields, and missing fields to form one question.
    """
    # prioritize ambiguous tokens
    ambiguities = state.get("ambiguities", []) or []
    if ambiguities:
        # for common fuzzy words map to ranges
        fuzzy_map = {
            "morning": "between 7 AM and 11 AM",
            "afternoon": "between 12 PM and 4 PM",
            "evening": "between 4 PM and 9 PM",
            "night": "after 9 PM",
            "noon": "around 12 PM",
            "after lunch": "between 2 PM and 4 PM",
        }
        token = ambiguities[0]
        if token in fuzzy_map:
            return f"When you say '{token}', do you mean {fuzzy_map[token]}?"
        return f"Could you clarify what you mean by '{token}' for the time?"

    # next, low confidence fields
    confidences = state.get("confidences", {}) or {}
    low = [k for k, v in confidences.items() if isinstance(v, (int, float)) and v < 0.7]
    if low:
        field = low[0]
        if field == "location":
            return "Which city or location do you prefer for this booking?"
        if field == "service":
            return "Which service would you like (e.g., spa, salon, doctor)?"
        if field == "time":
            return "What time of day do you prefer? (e.g., 9 AM, afternoon, evening)"
        if field == "date":
            return "On which date would you like the booking?"

    # finally, missing fields
    for f in ("service", "date", "time", "location"):
        if not state.get(f):
            if f == "service":
                return "Which service do you want to book? (spa, salon, doctor, etc.)"
            if f == "date":
                return "Which date would you prefer for this booking?"
            if f == "time":
                return "What time would you like?"
            if f == "location":
                return "Which city or location should I use for this booking?"

    return None
