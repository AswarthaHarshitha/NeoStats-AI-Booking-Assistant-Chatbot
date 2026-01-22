"""Simple dynamic pricing engine.

Rules implemented:
- Base price per service.
- Confidence score reduces price via discount tiers.
- Simple promo/loyalty placeholders in meta.
"""
from typing import Tuple, Optional
import os
import requests

# simple in-memory cache for exchange rates
_FX_CACHE = {}

BASE_PRICES = {
    "spa": 50.0,
    "salon": 40.0,
    "doctor": 100.0,
    "head spa": 60.0,
    "facial": 27.0,
    "dental": 80.0,
    "hotel": 150.0,
    "travel": 80.0,
    "appointment": 30.0,
    "flight": 200.0,
}


def calculate_price(service: str, confidence_pct: float, meta: Optional[dict] = None, location: Optional[str] = None) -> Tuple[float, float, str]:
    """Return (final_price, discount_percent)

    - confidence_pct: 0-100
    - higher confidence -> better discount (simulated business rule)
    """
    base = BASE_PRICES.get(service, 50.0)
    # discount tiers: >90 -> 15%, >75 -> 10%, >50 -> 5%, else 0
    if confidence_pct >= 90:
        discount = 15.0
    elif confidence_pct >= 75:
        discount = 10.0
    elif confidence_pct >= 50:
        discount = 5.0
    else:
        discount = 0.0

    # meta-based loyalty (example)
    if meta and meta.get("loyalty_tier") == "gold":
        discount += 5.0

    final_usd = round(base * (1 - discount / 100.0), 2)

    # Simple currency selection: if location appears to be in India, convert to INR
    INDIAN_CITIES = {
        "bangalore", "bengaluru", "delhi", "mumbai", "chennai", "hyderabad",
        "vijayawada", "mangalagiri", "kolkata", "pune", "ahmedabad"
    }
    # if meta explicitly specifies currency, honor it
    currency = "USD"
    if meta and meta.get("currency"):
        currency = meta.get("currency").upper()
    elif location and location.lower() in INDIAN_CITIES:
        currency = "INR"

    if currency == "INR":
        # try to get a live rate if an API key is configured, otherwise fallback to a demo static rate
        def _get_rate():
            # prefer a cached value
            if "INR" in _FX_CACHE:
                return _FX_CACHE["INR"]
            # optional: external API if FX_API env var set (e.g., https://exchangerate-api.com)
            api_key = os.getenv("FX_API_KEY")
            if api_key:
                try:
                    resp = requests.get(f"https://open.er-api.com/v6/latest/USD", timeout=3)
                    data = resp.json()
                    rate = data.get("rates", {}).get("INR")
                    if rate:
                        _FX_CACHE["INR"] = float(rate)
                        return float(rate)
                except Exception:
                    pass
            # fallback static demo rate
            _FX_CACHE["INR"] = 82.0
            return 82.0

        EXCHANGE_RATE = _get_rate()
        final = round(final_usd * EXCHANGE_RATE, 2)
    else:
        final = final_usd

    return final, discount, currency
