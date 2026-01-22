# 🤖 NeoStats AI Booking Assistant

An advanced, modular **AI-powered booking assistant** built with **Streamlit**.  
It demonstrates **conversational booking**, **AI delegation/autonomy**, **fuzzy-time resolution**, **explainability**, **resilient receipt generation**, and **lightweight persistence**.

This repository was developed as an **advanced version of a NeoStats assignment**, focusing on **AI reasoning and decision-making** rather than simple CRUD workflows.  
It includes practical fallbacks for environments that lack optional libraries (PDF / QR / TTS).

---

## ✨ Highlights

- Conversational booking with NLU-like extraction (service, date, time, location)
- Delegation & autonomy rules — the AI can **auto-decide** when the user delegates
- Fuzzy-time resolution (e.g., *morning*, *evening*, *after lunch*)
- AI calendar conflict resolution & best-slot selection
- Explainability & confidence scoring per field
- Resilient receipt generation (PDF → text fallback)
- Lightweight persistence with SQLite + JSON fallback

---

## 📁 Repository Structure

- `app.py` — Streamlit UI and orchestration  
- `booking_logic.py` — Intent parsing, delegation logic, fuzzy-time handling  
- `slot_engine.py` — Availability checks & conflict resolution  
- `pricing.py` — Pricing rules and smart discounts  
- `explainability.py` — Confidence & explainability scoring  
- `receipts.py` — PDF/text receipt generation with fallbacks  
- `bookings_store.py` — SQLite storage with JSON fallback  
- `requirements.txt` — Core dependencies  

Additional : PDF receipts, QR codes, Text-to-Speech (TTS)

---

## ⚙️ Tech Stack

- Python 3.9+
- Streamlit
- SQLite (primary storage)
- JSON (fallback storage)

Optional libraries:
- ReportLab (PDF)
- qrcode / pillow
- gTTS

---

## 🚀 Quick Start (macOS / zsh)

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

---

## 🔧 Admin / Debug Panel

- Inspect detected intent & entities  
- View explainability & confidence scores  
- Understand autonomous decisions  
- Debug slot resolution & receipt generation  

Admin output is always in English.

---

## 🧪 Example Prompts

```
Book a facial next week in Vijayawada.
I prefer mornings but may have a meeting.
Resolve conflicts automatically.
Pick the best available slot.
Confirm and generate the receipt.
```

```
Book facial, spa, and dental appointments.
You decide everything and finalize.
```

```
నాకు హెడ్ స్పా కావాలి.
మీరు టైమ్, డేట్ నిర్ణయించి బుకింగ్ పూర్తి చేయండి.
```

---

## 🎯 Evaluation Focus

- AI autonomy & delegation
- Conflict resolution
- Explainability
- Robust handling of ambiguity

MongoDB is intentionally not used.

---
