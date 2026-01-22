# NeoStats AI Booking Assistant

A small, modular AI-powered booking assistant built with Streamlit. It demonstrates conversational booking flows, delegation/autonomy behavior, fuzzy-time resolution, explainability, resilient receipt generation (PDF and text fallbacks), and simple persistence (SQLite primary, JSON fallback).

This repository was developed as an advanced version of a NeoStats assignment and includes practical fallbacks for environments that lack optional libraries (PDF/QR/TTS).

## Highlights

- Conversational booking flow with NLU-like extraction (service, date, time, location).
- Delegation/autonomy rules: when the user delegates the decision, the assistant can auto-fill reasonable defaults and complete bookings.
- Fuzzy-time resolution: maps tokens like "morning"/"evening" to concrete slots and uses a slot engine for next-available times.
- Explainability & confidence: per-field confidence and an explainability score are computed and shown in the admin/debug panel.
- Receipts: attempts to generate a PDF receipt in-memory (ReportLab) and falls back to a guaranteed text receipt. Optionally includes QR images and TTS if libraries are installed.
- Persistence: primary storage in SQLite (`bookings.db`) with a JSON fallback (`bookings.json`) for portability.

## Repo structure

- `app.py` — Streamlit UI and orchestration
- `booking_logic.py` — NLU parsing, fuzzy-time resolution, delegation defaults
- `slot_engine.py` — availability and next-available slot logic
- `bookings_store.py` — persistence helpers, seed/reset demo data
- `pricing.py` — pricing and currency logic
- `receipts.py` — in-memory PDF / file fallback + text receipt fallback
- `explainability.py` — compute explainability/confidence
- `requirements.txt` — required libraries (core)

Optional extras implemented (not required): PDF receipts, QR codes, and TTS.

## Quick start (macOS / zsh)

1. Create and activate a Python venv (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Upgrade pip and install core dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. (Optional) Install extras for receipts & multimedia:

```bash
python -m pip install reportlab qrcode[pil] pillow gTTS
```

4. Run the app:

```bash
streamlit run app.py
```

Open the local Streamlit URL shown in your terminal.

## Admin / Debug Panel

The app includes a debug/admin panel (within the Streamlit app) where you can:

- Inspect raw booking JSON and tracebacks for receipt generation failures.
- Reset or seed demo bookings (useful for testing delegated flows).
- View explainability and per-field confidences.

Admin UI remains English-only; user-facing outputs attempt to respect language detection (Telugu support partially implemented).

## Receipt behavior & troubleshooting

- The app prefers to generate an in-memory PDF using ReportLab. If `reportlab` is not installed the app will:
  - Fall back to a guaranteed text receipt (always available), and
  - Print the full booking JSON + traceback in the Admin panel to help debug why PDF generation failed.
- If you want full PDF + QR + TTS functionality, install the optional extras listed above.

Typical issues and fixes:

- "No PDF receipt": install `reportlab` and `qrcode[pil]`; then retry the booking.
- "Receipt generation traceback shown": copy the traceback and booking JSON from the Admin panel and open an issue or paste it here for help.

## Tests

This project includes some unit tests. To run them:

```bash
python -m pip install pytest
pytest -q
```

If tests fail locally, please paste the `pytest` output and I'll help fix them.

## Contributing

Contributions are welcome. Recommended workflow:

1. Fork the repo and create a feature branch.
2. Run and test locally.
3. Open a PR with a clear description and run CI (if added).

If you'd like, I can add a CI workflow (GitHub Actions) to run tests and lint on push.

## Notes for maintainers

- Booking IDs are UUID-based and should remain so for cross-backend consistency.
- Optional libs are intentionally lazy-imported; the app degrades gracefully when they are missing.
- The `bookings.db` and `bookings.json` files are in `.gitignore` by default; avoid committing generated data.

---

If you'd like any changes to the README (more screenshots, examples of conversation flows, or a quick demo video), tell me what to include and I'll update it.

License: MIT (or change as appropriate)
