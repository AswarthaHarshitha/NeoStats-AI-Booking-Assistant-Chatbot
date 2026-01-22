"""Lightweight signal detectors: urgency/emotion and preferred response style.

These are small heuristics suitable for demos. They return a style tag and urgency flag.
"""
from typing import Tuple


def detect_urgency_and_style(text: str) -> Tuple[bool, str]:
    """Return (is_urgent, style) where style is one of: 'concise','formal','friendly'.

    Simple keyword-based heuristics.
    """
    t = (text or "").lower()
    urgent_words = ["urgent", "asap", "now", "immediately", "need a", "emergency"]
    polite_words = ["please", "thank you", "thanks"]

    is_urgent = any(w in t for w in urgent_words)

    # style heuristics
    if len(t.split()) < 4:
        style = "concise"
    elif any(w in t for w in polite_words):
        style = "formal"
    else:
        style = "friendly"

    return is_urgent, style
