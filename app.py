# import streamlit as st
# import os
# from dotenv import load_dotenv
# from openai import OpenAI
# from booking_logic import extract_booking_state

# load_dotenv()

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# st.set_page_config(page_title="AI Booking Assistant")
# st.title("🤖 AI Booking Assistant")

# SYSTEM_PROMPT = """
# You are an AI Booking Assistant.
# Ask only ONE question at a time.
# Do not assume missing details.
# Collect service, date, location, and time.
# Confirm booking once all details are collected.
# """

# if "messages" not in st.session_state:
#     st.session_state.messages = []

# user_input = st.chat_input("Enter your booking request")

# if user_input:
#     st.session_state.messages.append(
#         {"role": "user", "content": user_input}
#     )

#     booking_state = extract_booking_state(st.session_state.messages)
#     missing = [k for k, v in booking_state.items() if v is None]

#     if not missing:
#         result = {
#             "service": booking_state["service"],
#             "date": booking_state["date"],
#             "location": booking_state["location"],
#             "time": booking_state["time"],
#             "status": "confirmed"
#         }
#         st.json(result)
#     else:
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 *st.session_state.messages
#             ]
#         )

#         reply = response.choices[0].message.content
#         st.session_state.messages.append(
#             {"role": "assistant", "content": reply}
#         )

#         st.chat_message("assistant").markdown(reply)
import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
from booking_logic import extract_booking_state
from slot_engine import check_availability, book_slot, find_next_available, list_bookings, attempt_resolve, auto_book_alternative
from bookings_store import reset_bookings, seed_demo_bookings
from pricing import calculate_price
# lazy import receipts at runtime so the app still starts when optional deps are missing
from i18n import detect_language, translate_text
from signals import detect_urgency_and_style
from explainability import compute_explainability_score
from clarifier import generate_clarifying_question
from logger import get_logger
import io
import traceback
import uuid

logger = get_logger()

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Advanced AI Booking Assistant")
st.title("🤖 Advanced AI Booking Assistant")

 # UI polish: pill-style chat input, softer border and spacing
st.markdown(
    """
    <style>
    /* pill style chat input */
    .stTextInput>div>div>input, .stTextArea>div>textarea {
        box-shadow: none !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 28px !important;
        padding: 14px 56px 14px 20px !important;
        background: rgba(255,255,255,0.02) !important;
        color: #e6e6e6 !important;
        font-size: 18px !important;
    }
    /* leave bottom space so input doesn't overlap content */
    .block-container { padding-bottom: 120px; }
    /* rounded send button look for download/send buttons */
    .stButton>button { border-radius: 12px !important; }
    .stDownloadButton>button { border-radius: 12px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

SYSTEM_PROMPT = """
You are an advanced AI booking assistant.

Rules:
- Ask only one question at a time
- Never assume missing data
- Help users modify or cancel bookings
- Be polite, professional, and precise
"""

if "messages" not in st.session_state:
    st.session_state.messages = []

user_input = st.chat_input("How can I help you today?")

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    state = extract_booking_state(st.session_state.messages)
    missing = [k for k in ["service", "date", "time", "location"] if not state[k]]

    # use signals to adapt tone/urgency
    is_urgent, preferred_style = detect_urgency_and_style(st.session_state.messages[-1]["content"]) if st.session_state.messages else (False, "friendly")

    # detect user language preference from last message
    try:
        user_lang = detect_language(st.session_state.messages[-1]["content"]) if st.session_state.messages else None
    except Exception:
        user_lang = None
    target_lang = user_lang if user_lang in ("te", "hi") else "en"

    # show confidence and explanations (only show internal reasoning for English UI)
    if target_lang == "en":
        if state.get("confidences"):
            # make confidences human readable (percent)
            pretty_conf = {k: (f"{int(round(v*100))}%" if isinstance(v, float) else v) for k, v in state.get("confidences", {}).items()}
            st.caption(f"Confidences: {pretty_conf}")
        if state.get("explanation"):
            st.caption(f"Explanation: {state.get('explanation')}")
    else:
        # keep user-facing language clean in non-English UIs (e.g., Telugu)
        pass

    # compute explainability score
    expl = compute_explainability_score(state)
    st.caption(f"Explainability Score: {expl.get('score')} (breakdown: {expl})")

    # if any low confidence, ask clarification (skip if user delegated decision-making)
    low_conf = [k for k, v in state.get("confidences", {}).items() if v and v < 0.7]
    if low_conf and not state.get("delegated"):
        st.warning(f"I need clarification on: {', '.join(low_conf)}")
        # generate a single clarifying question and show helper button
        question = generate_clarifying_question(state)
        if question:
            st.info(f"Suggested clarification: {question}")
            if st.button("Append clarifying question to conversation"):
                st.session_state.messages.append({"role": "assistant", "content": question})
                logger.info(f"Appended clarifying question: {question}")
                st.success("Clarifying question appended to the conversation.")
                # Stop further execution to allow the UI to refresh on the next interaction
                try:
                    st.stop()
                except Exception:
                    # Older/newer streamlit versions may not have stop; fall back to a no-op
                    pass
        # we stop here so human/assistant can clarify in the chat
    
    # MODIFY / CANCEL
    if state["intent"] == "modify":
        st.warning("🔄 You want to modify an existing booking.")
        st.write("Please specify what you want to change.")
    
    # CONFIRM BOOKING
    elif not missing:
        # Check availability for requested service/date/time
        available, slots = check_availability(state["service"], state["date"], state["time"])

        booking = None

        # If the user delegated, show a one-click confirmation and prefer the assistant-chosen slot
        if state.get("delegated"):
            # ensure there is a chosen time (booking_logic should have attempted to pick one)
            suggested_time = state.get("time")
            if not suggested_time:
                try:
                    res = find_next_available(state["service"], state["date"])
                    if res:
                        suggested_time = res[0]
                        state["time"] = suggested_time
                except Exception:
                    suggested_time = None

            st.info(f"You delegated choices to the assistant. Suggested booking: {state.get('service')} on {state.get('date')} at {suggested_time} in {state.get('location')}.")
            if st.button("Confirm auto-booking", key="confirm_auto_book"):
                # proceed to booking using the suggested_time
                try:
                    booking = book_slot(state["service"], state["date"], state.get("time"), state.get("location"))
                except Exception as e:
                    st.error(f"Could not create booking: {e}")
                    booking = None
            else:
                booking = None

        elif not available:
            # attempt automatic resolution
            st.error(f"❌ Selected time unavailable. Considering alternatives...")
            resolution = attempt_resolve(state["service"], state["date"], state["time"], allow_nearby=True)
            st.write(resolution)
            if resolution.get("suggestion"):
                if st.button(f"Auto-book suggested slot {resolution.get('suggestion')}"):
                    try:
                        new_booking = auto_book_alternative(state["service"], state["date"], state["time"])
                        st.success(f"Auto-booked {new_booking.get('time')} (id={new_booking.get('id')})")
                        # ensure the unified post-booking flow runs for this auto-booking
                        booking = new_booking
                        logger.info(f"Auto-booked suggested slot, booking id={new_booking.get('id')}")
                    except Exception as e:
                        st.error(f"Auto-book failed: {e}")
        else:
            # Book the slot immediately (non-delegated confirmed booking)
            try:
                booking = book_slot(state["service"], state["date"], state["time"], state.get("location"))
            except Exception as e:
                st.error(f"Could not create booking: {e}")
                booking = None

        # If a booking was created by any branch, run the post-booking flow
        if booking:
            try:
                confidence = round(100 - (len(st.session_state.messages) * 2), 2)

                # pricing (currency-aware)
                price, discount, currency = calculate_price(booking.get("service"), confidence, booking.get("meta"), location=booking.get("location"))
                symbol = "₹" if currency == "INR" else "$"

                st.success("✅ Booking Confirmed!")

                # enrich booking dict for receipts
                booking["price"] = price
                booking["currency"] = currency
                booking["discount_percent"] = discount
                booking["delegated"] = state.get("delegated", False)
                booking["explanation"] = state.get("explanation", "")[:1000]
                # carry over auto-selection flags from state so UI can label them
                booking["location_auto_selected"] = state.get("location_auto_selected", False)
                booking["service_auto_selected"] = state.get("service_auto_selected", False)

                # ensure a booking id exists so receipts always include an ID
                if not booking.get("id"):
                    booking["id"] = str(uuid.uuid4())

                # prepare booking info dict and human summary
                booking_info = {
                    "id": booking.get("id") or str(uuid.uuid4()),
                    "service": booking.get("service"),
                    "date": booking.get("date"),
                    "time": booking.get("time"),
                    "location": booking.get("location"),
                    "confidence_score": f"{confidence}%",
                    "price": f"{symbol}{price}",
                    "discount_percent": f"{discount}%",
                    "currency": currency,
                    "delegated": booking.get("delegated", False),
                    "explanation": booking.get("explanation", "")[:1000],
                    "status": "confirmed"
                }
                st.json(booking_info)

                # Format date for human readability (Weekday, dd Mon YYYY) when possible
                try:
                    from datetime import datetime as _dt
                    d = booking.get('date')
                    if d:
                        try:
                            display_date = _dt.fromisoformat(d).strftime('%A, %d %b %Y')
                        except Exception:
                            display_date = d
                    else:
                        display_date = ""
                except Exception:
                    display_date = booking.get('date', '')

                display_location = booking_info.get('location') or ''
                if booking.get('location_auto_selected'):
                    display_location = f"{display_location} (auto-selected)"
                display_service = booking_info.get('service') or ''
                if booking.get('service_auto_selected'):
                    display_service = f"{display_service} (auto-selected)"

                summary_en = (
                    f"Booking ID: {booking_info['id']}\n"
                    f"Service: {display_service}\n"
                    f"Date: {display_date}\n"
                    f"Time: {booking_info['time']}\n"
                    f"Location: {display_location}\n"
                    f"AI Confidence: {confidence}%\n"
                    f"Price: {symbol}{price} (Discount: {discount}%)\n"
                    f"Delegated: {booking_info.get('delegated')}\n"
                    f"Explanation: {booking_info.get('explanation')}\n"
                    f"Currency: {booking_info.get('currency')}"
                )

                # translate summary if needed
                try:
                    translated_summary = translate_text(summary_en, dest=target_lang) if target_lang != "en" else summary_en
                except Exception:
                    translated_summary = summary_en

                st.markdown("### 📄 Booking Summary")
                st.text(translated_summary)

                # Generate PDF receipt and offer a download (lazy import so missing optional deps don't break the app)
                try:
                    # Prefer in-memory PDF generation (no filesystem). Fallback to file-based if needed.
                    try:
                        from receipts import generate_pdf_bytes
                        pdf_bytes = generate_pdf_bytes(booking)
                        st.download_button("Download PDF receipt", data=pdf_bytes, file_name=f"receipt_{booking.get('id')}.pdf", mime="application/pdf")
                    except Exception:
                        try:
                            from receipts import generate_pdf_receipt
                            pdf_path = generate_pdf_receipt(booking)
                            with open(pdf_path, "rb") as f:
                                pdf_bytes = f.read()
                            st.download_button("Download PDF receipt", data=pdf_bytes, file_name=os.path.basename(pdf_path), mime="application/pdf")
                        except Exception as imp_e:
                            # re-raise to outer handler which will show debug info
                            raise RuntimeError(f"Receipts module unavailable or generation failed: {imp_e}") from imp_e

                    # Try generating voice confirmation (TTS) if available
                    try:
                        from gtts import gTTS
                        mp3_io = io.BytesIO()
                        tts_lang = target_lang if target_lang in ("en", "hi", "te") else "en"
                        tts = gTTS(text=translated_summary, lang=tts_lang)
                        tts.write_to_fp(mp3_io)
                        mp3_io.seek(0)
                        st.audio(mp3_io.getvalue())
                        st.download_button("Download voice confirmation (mp3)", data=mp3_io.getvalue(), file_name=f"confirmation_{booking.get('id')}.mp3", mime="audio/mpeg")
                    except Exception:
                        # TTS not available or failed; continue silently
                        pass

                except Exception as e:
                    # Log exception and show detailed debug info in UI to help diagnose missing libs / data issues
                    logger.exception("Receipt generation failed")
                    st.warning(f"Could not generate PDF receipt: {e}")
                    st.caption("Booking object (for debugging):")
                    try:
                        st.json(booking)
                    except Exception:
                        st.text(str(booking))
                    st.caption("Traceback:")
                    st.text(traceback.format_exc())

                    # Fallback: produce a simple text receipt for download
                    try:
                        txt_lines = [
                            f"Booking ID: {booking.get('id')}",
                            f"Service: {booking.get('service')}",
                            f"Date: {booking.get('date')}",
                            f"Time: {booking.get('time')}",
                            f"Location: {booking.get('location')}",
                            f"Price: {booking.get('currency', '')} {booking.get('price')}",
                            f"Total Amount: {booking.get('currency', '')} {booking.get('price')}",
                            "\nThank you for your booking!"
                        ]
                        txt = "\n".join(txt_lines).encode("utf-8")
                        st.download_button("Download text receipt", data=txt, file_name=f"receipt_{booking.get('id')}.txt", mime="text/plain")
                    except Exception:
                        st.error("Failed to create fallback receipt")

                # Always offer a plain-text receipt as a guaranteed download option (safe fallback)
                try:
                    txt_lines = [
                        f"Booking ID: {booking.get('id')}",
                        f"Service: {booking.get('service')}",
                        f"Date: {booking.get('date')}",
                        f"Time: {booking.get('time')}",
                        f"Location: {booking.get('location')}",
                        f"Price: {booking.get('currency', '')} {booking.get('price')}",
                        f"Total Amount: {booking.get('currency', '')} {booking.get('price')}",
                        "\nThank you for your booking!"
                    ]
                    txt = "\n".join(txt_lines).encode("utf-8")
                    st.download_button("Download text receipt", data=txt, file_name=f"receipt_{booking.get('id')}.txt", mime="text/plain")
                except Exception:
                    # if even text fallback fails, silently continue
                    pass

            except Exception as e:
                st.error(f"Post-booking processing failed: {e}")

    # CONTINUE CONVERSATION
    else:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *st.session_state.messages
            ]
        )

        reply = response.choices[0].message.content
        st.session_state.messages.append(
            {"role": "assistant", "content": reply}
        )
        st.chat_message("assistant").markdown(reply)

# UNIQUE: Admin Debug Panel
with st.expander("🔧 Debug / Admin Panel"):
    st.json(st.session_state.messages)
    st.markdown("### Current bookings")
    try:
        bookings = list_bookings()
        st.json(bookings)
    except Exception as e:
        st.warning(f"Could not load bookings: {e}")
    st.markdown("---")
    st.write("Admin actions (use with care):")
    if st.button("Reset bookings database (delete all bookings)"):
        try:
            reset_bookings()
            st.success("All bookings have been deleted (bookings reset).")
            logger.info("Admin reset: bookings cleared")
        except Exception as e:
            st.error(f"Failed to reset bookings: {e}")

    if st.button("Seed demo bookings"):
        try:
            seed_demo_bookings()
            st.success("Demo bookings have been added.")
            logger.info("Admin action: demo bookings seeded")
        except Exception as e:
            st.error(f"Failed to seed demo bookings: {e}")
