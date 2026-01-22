from clarifier import generate_clarifying_question


def test_clarify_fuzzy_time():
    state = {"ambiguities": ["evening"], "confidences": {}}
    q = generate_clarifying_question(state)
    assert q is not None
    assert "evening" in q or "do you mean" in q


def test_clarify_low_confidence_location():
    state = {"ambiguities": [], "confidences": {"location": 0.5}}
    q = generate_clarifying_question(state)
    assert q is not None
    assert "location" in q.lower() or "city" in q.lower()
