import re
from datetime import datetime, time
from typing import Optional


def normalize_time(text: str) -> Optional[str]:
    """Normalize a time phrase into 12-hour format 'H:MM AM/PM'.

    Handles inputs like '9am', '9:30 AM', '14:00', '2 pm', etc.
    Returns None if no sensible time is found.
    """
    if not text:
        return None

    s = text.lower()

    # 12-hour with am/pm, e.g. '9am', '9:30 am'
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or "0")
        period = m.group(3).lower()
        if period == "pm" and hour != 12:
            hour = hour + 12
        if period == "am" and hour == 12:
            hour = 0
        t = time(hour=hour, minute=minute)
        return t.strftime("%I:%M %p").lstrip("0")

    # 24-hour format like '14:30' or '9:00'
    m2 = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", s)
    if m2:
        hour = int(m2.group(1))
        minute = int(m2.group(2))
        t = time(hour=hour, minute=minute)
        return t.strftime("%I:%M %p").lstrip("0")

    # fallback: single hour with am/pm separated (e.g., '9 pm' handled above), otherwise give up
    return None
