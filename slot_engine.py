from typing import Tuple, List, Optional
from bookings_store import add_booking, find_bookings, load_bookings, update_booking, remove_booking

# Standardized available slots (times in H:MM AM/PM)
AVAILABLE_SLOTS = {
    "spa": ["9:00 AM", "10:00 AM", "11:00 AM", "4:00 PM"],
    "salon": ["10:00 AM", "12:00 PM", "3:00 PM"],
    "facial": ["10:00 AM", "11:00 AM", "3:00 PM"],
    "dental": ["9:00 AM", "11:00 AM", "2:00 PM"],
    "doctor": ["9:00 AM", "1:00 PM", "6:00 PM"],
    "head spa": ["10:00 AM", "2:00 PM"],
    "hotel": ["Anytime"],
    "travel": ["Morning", "Evening"]
}


def check_availability(service: str, date: Optional[str], time: Optional[str]) -> Tuple[bool, List[str]]:
    """Return (available, slots) for a service on a particular date/time.

    If service not listed, treat as available with 'Anytime'.
    If slots include 'Anytime', always available.
    If a specific time is requested, check existing bookings for conflicts.
    """
    if service not in AVAILABLE_SLOTS:
        return True, ["Anytime"]

    slots = AVAILABLE_SLOTS[service]
    if "Anytime" in slots:
        return True, slots

    if not time:
        return True, slots

    # If someone already booked this service/date/time, it's unavailable
    existing = find_bookings(service=service, date=date, time=time)
    if existing:
        # not available; return alternatives (other slots for the day)
        alternatives = [s for s in slots if s != time]
        return False, alternatives

    return True, slots


def book_slot(service: str, date: str, time: str, location: Optional[str] = None, meta: Optional[dict] = None) -> dict:
    """Attempt to book a slot; returns the booking entry on success.
    Raises ValueError if slot unavailable.
    """
    available, slots = check_availability(service, date, time)
    if not available:
        raise ValueError("Requested time is not available")

    booking = add_booking({
        "service": service,
        "date": date,
        "time": time,
        "location": location,
        "meta": meta or {}
    })
    return booking


def attempt_resolve(service: str, date: str, time: str, allow_nearby: bool = True) -> dict:
    """Try to produce a set of resolution actions when booking fails.

    Returns a dict with keys: available (bool), suggestion (time or None), alternatives (list)
    """
    available, slots = check_availability(service, date, time)
    if available:
        return {"available": True, "suggestion": time, "alternatives": slots}

    # Suggest next available on same date
    nxt = find_next_available(service, date, after_time=time)
    alternatives = slots
    suggestion = None
    if nxt:
        suggestion = nxt[0]

    # Optionally, suggest same time at other services (simple nearby logic)
    other_options = []
    if allow_nearby:
        for s, s_slots in AVAILABLE_SLOTS.items():
            if s == service:
                continue
            if time in s_slots:
                other_options.append({"service": s, "time": time})

    return {"available": False, "suggestion": suggestion, "alternatives": alternatives, "other_options": other_options}


def auto_book_alternative(service: str, date: str, time: Optional[str] = None) -> dict:
    """Auto-book the next available slot for service/date. Returns booking or raises."""
    if time:
        # try the next available after requested time
        nxt = find_next_available(service, date, after_time=time)
    else:
        nxt = find_next_available(service, date)

    if not nxt:
        raise ValueError("No alternative slots available")

    chosen_time = nxt[0]
    return book_slot(service, date, chosen_time)


def find_next_available(service: str, date: str, after_time: Optional[str] = None) -> Optional[Tuple[str, List[str]]]:
    """Return the next free slot (time, slots) after a given time on a date, or None.
    """
    if service not in AVAILABLE_SLOTS:
        return None
    slots = AVAILABLE_SLOTS[service]
    # if after_time not provided, return first free
    for s in slots:
        if after_time and s == after_time:
            continue
        # check bookings
        booked = find_bookings(service=service, date=date, time=s)
        if not booked:
            return s, slots
    return None


def modify_booking(booking_id: str, new_date: Optional[str] = None, new_time: Optional[str] = None) -> Optional[dict]:
    bookings = load_bookings()
    for b in bookings:
        if b.get("id") == booking_id:
            service = b.get("service")
            date = new_date or b.get("date")
            time = new_time or b.get("time")
            # check availability
            available, _ = check_availability(service, date, time)
            if not available:
                raise ValueError("Requested new time is not available")
            b["date"] = date
            b["time"] = time
            save = update_booking(booking_id, {"date": date, "time": time})
            return save
    return None


def cancel_booking(booking_id: str) -> bool:
    return remove_booking(booking_id)


def list_bookings():
    return load_bookings()

