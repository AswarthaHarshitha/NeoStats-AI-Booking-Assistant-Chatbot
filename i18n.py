"""Simple internationalization helpers: language detection and translation.

Uses `langdetect` for language detection and `googletrans` for translation.
If these are unavailable at runtime the functions will fall back to identity.
"""
from typing import Optional
try:
    from langdetect import detect
except Exception:
    detect = None

try:
    from googletrans import Translator
    _translator = Translator()
except Exception:
    _translator = None


def detect_language(text: str) -> Optional[str]:
    if not text:
        return None
    if detect is None:
        return None
    try:
        return detect(text)
    except Exception:
        return None


def translate_text(text: str, dest: str) -> str:
    if not text or not dest:
        return text
    if _translator is None:
        return text
    try:
        res = _translator.translate(text, dest=dest)
        return res.text
    except Exception:
        return text
