import os
from slot_engine import book_slot, check_availability, cancel_booking, list_bookings


def test_booking_flow():
    service = "spa"
    date = "2099-01-01"  # far future date to avoid collisions
    time = "9:00 AM"

    # Ensure available
    available, slots = check_availability(service, date, time)
    assert available

    # Book it
    booking = book_slot(service, date, time, location="bangalore")
    assert booking["service"] == service
    assert booking["date"] == date
    assert booking["time"] == time
    booking_id = booking["id"]

    # Now it should be unavailable
    available, _ = check_availability(service, date, time)
    assert not available

    # Cancel the booking
    ok = cancel_booking(booking_id)
    assert ok

    # After cancellation it should be available again
    available, _ = check_availability(service, date, time)
    assert available
