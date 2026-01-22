import os
from datetime import datetime
from typing import Optional, List, Dict
import tempfile
from io import BytesIO


def _currency_symbol(code: str) -> str:
    return "₹" if code and code.upper() == "INR" else "$"


def generate_pdf_receipt(booking: dict, out_dir: Optional[str] = None) -> str:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    except Exception as e:
        raise ImportError("reportlab is required to generate PDF receipts. Install with 'pip install reportlab'.") from e

    # write PDFs to a safe temporary directory by default to avoid permission issues
    if out_dir is None:
        out_dir = tempfile.gettempdir()
    os.makedirs(out_dir, exist_ok=True)

    # Optional QR generation placeholder (generate_pdf_bytes will also attempt QR if available)
    pdf_bytes = generate_pdf_bytes(booking)
    booking_id = booking.get("id", f"bkg_{datetime.utcnow().timestamp()}")
    filename = f"receipt_{booking_id}.pdf"
    path = os.path.join(out_dir, filename)
    with open(path, "wb") as _f:
        _f.write(pdf_bytes)
    return path


def generate_pdf_bytes(booking: dict) -> bytes:
    """Generate a PDF in-memory and return bytes. Uses ReportLab; raises ImportError if missing."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    except Exception as e:
        raise ImportError("reportlab is required to generate PDF receipts. Install with 'pip install reportlab'.") from e

    # Optional QR generation
    qr_png = None
    try:
        import qrcode
        bio_qr = BytesIO()
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(booking.get("id", ""))
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(bio_qr, format="PNG")
        bio_qr.seek(0)
        qr_png = bio_qr
    except Exception:
        qr_png = None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story: List = []

    # Header
    title = Paragraph("<b>Booking Receipt</b>", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 6))

    # Basic meta
    created = booking.get("created_at") or datetime.utcnow().isoformat() + "Z"
    meta_table_data = [
        ["Booking ID:", booking.get("id", f"bkg_{datetime.utcnow().timestamp()}")],
        ["Created:", created],
        ["Salon:", booking.get("salon") or booking.get("location") or "-"],
        ["Location:", booking.get("location") or "-"],
        ["Date:", booking.get("date") or "-"],
        ["Time:", booking.get("time") or "-"],
    ]
    t = Table(meta_table_data, hAlign="LEFT", colWidths=[80 * mm, 80 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.darkgray),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Items: prefer booking['items'] as list of dicts; else parse service string
    items: List[Dict] = booking.get("items") or []
    if not items:
        svc = booking.get("service") or ""
        # if service contains '+', split into parts
        if "+" in svc:
            parts = [p.strip() for p in svc.split("+") if p.strip()]
            for p in parts:
                items.append({"name": p, "price": booking.get("price_per_item") or None})
        else:
            items.append({"name": svc or "Service", "price": booking.get("price")})

    # Build items table
    currency = booking.get("currency") or booking.get("meta", {}).get("currency") or ("INR" if (booking.get("location") or "").lower() in {"bangalore", "mumbai", "delhi", "hyderabad", "vijayawada"} else "USD")
    symbol = _currency_symbol(currency)

    table_data = [["Service", "Price"]]
    subtotal = 0.0
    for it in items:
        name = it.get("name")
        price = it.get("price")
        if price is None:
            # try to use booking total divided equally when only total provided
            price = booking.get("price") or booking.get("total") or 0.0
        try:
            pnum = float(price)
        except Exception:
            pnum = 0.0
        subtotal += pnum
        table_data.append([name, f"{symbol}{pnum:,.2f}"])

    # totals
    taxes = booking.get("taxes", 0.0)
    total = booking.get("total") or booking.get("price") or round(subtotal + taxes, 2)
    table_data.append(["Subtotal", f"{symbol}{subtotal:,.2f}"])
    table_data.append(["Taxes", f"{symbol}{taxes:,.2f}"])
    table_data.append(["Total", f"{symbol}{float(total):,.2f}"])

    tbl = Table(table_data, hAlign="LEFT", colWidths=[110 * mm, 40 * mm])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 12))

    # Explanation / delegated flag
    if booking.get("delegated") is True:
        story.append(Paragraph("<i>Note: Booking choices were delegated to the assistant.</i>", styles["Normal"]))
        story.append(Spacer(1, 6))
    expl = booking.get("explanation") or booking.get("meta", {}).get("explanation")
    if expl:
        story.append(Paragraph(f"<b>Explanation:</b> {expl}", styles["Normal"]))
        story.append(Spacer(1, 8))

    # QR code image if available
    if qr_png:
        try:
            img = Image(qr_png, width=40 * mm, height=40 * mm)
            story.append(img)
        except Exception:
            pass

    # Footer
    story.append(Spacer(1, 12))
    story.append(Paragraph("Thank you for your booking! For changes, contact the salon directly.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


if __name__ == "__main__":
    # produce a sample receipt using the example provided by the user
    sample = {
        "id": "bkg_sample_001",
        "service": "Cleansing Facial + Manicure",
        "salon": "Salon A",
        "location": "Vijayawada",
        "date": "Wednesday",
        "time": "10:00 AM",
        "items": [
            {"name": "Cleansing Facial", "price": 1200.0},
            {"name": "Manicure", "price": 800.0},
        ],
        "total": 2000.0,
        "currency": "INR",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "delegated": False,
        "explanation": "Sample receipt generated for demo.",
    }
    out = generate_pdf_receipt(sample)
    print("Generated sample receipt:", out)
