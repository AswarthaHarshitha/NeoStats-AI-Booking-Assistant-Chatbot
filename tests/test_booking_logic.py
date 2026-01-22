from booking_logic import extract_booking_state


def test_extract_exact_time_and_date():
    messages = [{"role": "user", "content": "I want a spa on 2099-01-01 at 9am in Bangalore"}]
    state = extract_booking_state(messages)
    assert state["service"] == "spa"
    assert state["date"] == "2099-01-01"
    assert state["time"] in ("9:00 AM", "9:00 am") or state["time"] == "9 AM"
    assert state["location"] == "bangalore"
    assert state["confidences"]["service"] >= 0.9


def test_fuzzy_time_detection():
    messages = [{"role": "user", "content": "Book me a salon tomorrow evening"}]
    state = extract_booking_state(messages)
    assert state["service"] == "salon"
    assert state["date"] is not None
    assert state["time"] == "evening"
    assert state["confidences"]["time"] < 0.8
    assert "evening" in state["ambiguities"]
