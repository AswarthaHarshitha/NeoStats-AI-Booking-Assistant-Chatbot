from booking_logic import extract_booking_state


def test_delegation_and_mapping():
    msgs = [
        {"role": "user", "content": "Book an appointment for a facial in Vijayawada in the morning - you decide"}
    ]
    state = extract_booking_state(msgs)
    assert state.get("delegated") is True
    # appointment should be mapped to facial
    assert state.get("service") == "facial"
    # explicit location should be captured
    assert "vijayawada" in state.get("location")
    # fuzzy morning should be resolved to a concrete time (either via slot lookup or default 10:00 AM)
    assert state.get("time") is not None
