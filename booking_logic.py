# def extract_booking_state(messages):
#     state = {
#         "service": None,
#         "date": None,
#         "location": None,
#         "time": None
#     }

#     for msg in messages:
#         text = msg["content"].lower()

#         if any(word in text for word in ["hotel", "flight", "appointment"]):
#             state["service"] = text

#         if any(word in text for word in ["today", "tomorrow", "jan", "feb", "mar", "202"]):
#             state["date"] = text

#         if "am" in text or "pm" in text or ":" in text:
#             state["time"] = text

#         if any(city in text for city in ["bangalore", "delhi", "mumbai", "chennai"]):
#             state["location"] = text

#     return state
import re
from datetime import datetime, timedelta
from typing import Optional
from time_utils import normalize_time
from slot_engine import find_next_available

SERVICES = [
    "hotel", "flight", "appointment", "spa",
    "salon", "head spa", "hospital", "doctor", "travel"
]

CITIES = [
    "bangalore", "delhi", "mumbai",
    "chennai", "hyderabad", "mangalagiri", "vijayawada"
]


def _parse_date(text: str) -> Optional[str]:
    text = text.lower()
    today = datetime.now().date()
    if "today" in text:
        return today.isoformat()
    if "tomorrow" in text:
        return (today + timedelta(days=1)).isoformat()

    # common formats: dd/mm/yyyy, dd/mm/yy, yyyy-mm-dd
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", text)
    if m:
        for fmt in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(m.group(1), fmt).date().isoformat()
            except Exception:
                continue

    m2 = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", text)
    if m2:
        try:
            return datetime.strptime(m2.group(1), "%Y-%m-%d").date().isoformat()
        except Exception:
            pass

    return None


def extract_booking_state(messages):
    """Extract booking state from a list of message dicts.

    Returns a dict with keys: service, date (ISO), time (H:MM AM/PM), location, intent
    """
    state = {
        "service": None,
        "date": None,
        "time": None,
        "location": None,
        "intent": "book",
        "delegated": False,
        # flags to indicate assistant-made defaults (do not silently pretend these were user-provided)
        "location_auto_selected": False,
        "service_auto_selected": False,
    }

    # We'll collect short explanations and confidence scores per entity
    confidences = {"service": 0.0, "date": 0.0, "time": 0.0, "location": 0.0}
    ambiguities = []
    explanations = []

    for msg in messages:
        text = msg.get("content", "").lower()

        # capture explicit 'in <city>' patterns even if city is not in our known list
        m_loc = re.search(r"in\s+([a-zA-Z ]{3,30})", text)
        if m_loc:
            candidate = m_loc.group(1).strip().lower()
            # prefer exact known city names, otherwise record as explicit_location
            if candidate in CITIES:
                if not state.get("location"):
                    state["location"] = candidate
                    confidences["location"] = 0.9
                    explanations.append(f"Location matched via pattern: {candidate}")
            else:
                # record an explicit freeform location for later use
                explicit_location = candidate
                explanations.append(f"Explicit location mentioned: {candidate}")

        # Detect explicit delegation phrases where the user delegates decisions to the assistant
        # e.g. "you decide", "book it", "go ahead", "surprise me", "anything works"
        delegation_phrases = [
            "you decide",
            "you pick",
            "you choose",
            "book it",
            "do it",
            "go ahead",
            "surprise me",
            "anything works",
            "i don't care",
            "i dont care",
            "up to you",
            "whatever you think",
        ]
        if any(p in text for p in delegation_phrases):
            state["delegated"] = True
            explanations.append("User delegated decision-making to assistant")

        # Intent detection
        if any(word in text for word in ["cancel", "cancelled", "delete"]):
            state["intent"] = "cancel"
        elif any(word in text for word in ["change", "modify", "reschedule"]):
            state["intent"] = "modify"

        # Service detection (prefer first matched service)
        for s in SERVICES:
            if s in text and not state["service"]:
                state["service"] = s
                confidences["service"] = 0.95
                explanations.append(f"Service matched by keyword '{s}'")

        # If the user said generic 'appointment' but later specified sub-type like 'facial', map it
        if state.get("service") == "appointment":
            if any(k in text for k in ["facial", "face", "skincare", "cleaning", "derma"]):
                state["service"] = "facial"
                confidences["service"] = 0.9
                explanations.append("Mapped generic 'appointment' to specific 'facial' based on user text")
            elif any(k in text for k in ["dental", "dentist"]):
                state["service"] = "dental"
                confidences["service"] = 0.9
                explanations.append("Mapped generic 'appointment' to specific 'dental' based on user text")

        # Date detection
        if not state["date"]:
            parsed = _parse_date(text)
            if parsed:
                state["date"] = parsed
                confidences["date"] = 0.9
                explanations.append(f"Date parsed as {parsed}")

        # Time detection (supports fuzzy expressions like 'morning', 'evening')
        if not state["time"]:
            # exact time
            time_value = normalize_time(text)
            if time_value:
                state["time"] = time_value
                confidences["time"] = 0.95
                explanations.append(f"Time normalized to {time_value}")
            else:
                # fuzzy time words -> resolve to concrete times (per policy)
                fuzzy_map = {
                    "morning": "10:00 AM",
                    "afternoon": "02:00 PM",
                    "evening": "06:00 PM",
                    "night": "08:00 PM",
                    "noon": "12:00 PM",
                    "after lunch": "02:00 PM",
                    "before lunch": "11:30 AM",
                }
                for w, resolved in fuzzy_map.items():
                    if w in text:
                        state["time"] = resolved
                        confidences["time"] = 0.7
                        explanations.append(f"Fuzzy time '{w}' resolved to {resolved}")
                        break

        # Location detection
        for city in CITIES:
            if city in text and not state["location"]:
                state["location"] = city
                confidences["location"] = 0.9
                explanations.append(f"Location matched: {city}")

    # attach confidences, ambiguities and explanation summary
    # If the user explicitly delegated and some fields are missing, infer reasonable defaults
    if state.get("delegated"):
        today_iso = datetime.now().date().isoformat()
        # default service
        if not state.get("service"):
            # prefer a service that fits the spa/salon domain rather than a generic 'appointment'
            state["service"] = "facial"
            state["service_auto_selected"] = True
            confidences["service"] = 0.6
            explanations.append("Defaulted service to 'facial' due to delegation")
        # default date
        if not state.get("date"):
            state["date"] = today_iso
            confidences["date"] = 0.6
            explanations.append(f"Defaulted date to {today_iso} due to delegation")
        # default time: prefer the next actually available slot for the chosen service/date
        if not state.get("time"):
            try:
                if state.get("service"):
                    nxt = find_next_available(state["service"], state["date"])
                    if nxt:
                        chosen_time = nxt[0]
                        state["time"] = chosen_time
                        confidences["time"] = 0.75
                        explanations.append(f"Auto-selected next available slot {chosen_time} for service {state.get('service')}")
                    else:
                        # fallback to conservative default
                        state["time"] = "10:00 AM"
                        confidences["time"] = 0.6
                        explanations.append("Defaulted time to 10:00 AM due to delegation (no available slots found)")
                else:
                    state["time"] = "10:00 AM"
                    confidences["time"] = 0.6
                    explanations.append("Defaulted time to 10:00 AM due to delegation")
            except Exception:
                # if slot_engine fails for any reason, keep a safe static default
                state["time"] = "10:00 AM"
                confidences["time"] = 0.6
                explanations.append("Defaulted time to 10:00 AM due to delegation (slot lookup failed)")
        # default location: prefer any explicit_location captured earlier, then CITIES[0]
        if not state.get("location"):
            if 'explicit_location' in locals() and explicit_location:
                state["location"] = explicit_location
                confidences["location"] = 0.8
                explanations.append(f"Used earlier mentioned location '{explicit_location}' due to delegation")
            else:
                state["location"] = CITIES[0]
                state["location_auto_selected"] = True
                confidences["location"] = 0.5
                explanations.append(f"Auto-selected location {CITIES[0]} due to delegation (assistant-chosen)")

    state["confidences"] = confidences
    state["ambiguities"] = ambiguities
    state["explanation"] = "; ".join(explanations) if explanations else ""
    return state
