"""Bookings store with SQLite backend (falls back to JSON file if sqlite unavailable).

This module exposes the same functions used elsewhere in the project:
- load_bookings()
- add_booking(booking: dict) -> dict
- update_booking(booking_id: str, updates: dict) -> dict | None
- remove_booking(booking_id: str) -> bool
- find_bookings(service=None, date=None, time=None)

The SQLite DB is located at `bookings.db` next to this module.
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "bookings.db")
JSON_FALLBACK = os.path.join(os.path.dirname(__file__), "bookings.json")


def _use_sqlite() -> bool:
    try:
        import sqlite3  # noqa: F401
        return True
    except Exception:
        return False


if _use_sqlite():
    import sqlite3

    def _conn():
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db():
        conn = _conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                service TEXT,
                date TEXT,
                time TEXT,
                location TEXT,
                created_at TEXT,
                meta TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    _ensure_db()

    def load_bookings() -> List[Dict]:
        conn = _conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM bookings ORDER BY created_at")
        rows = cur.fetchall()
        conn.close()
        out = []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r["meta"]) if r["meta"] else {}
            except Exception:
                meta = {}
            out.append({
                "id": r["id"],
                "service": r["service"],
                "date": r["date"],
                "time": r["time"],
                "location": r["location"],
                "created_at": r["created_at"],
                "meta": meta,
            })
        return out


    from uuid import uuid4


    def generate_booking_id() -> str:
        # Use UUID4 strings for robust unique ids across processes
        return f"bkg_{uuid4().hex}"


    def add_booking(booking: dict) -> dict:
        conn = _conn()
        cur = conn.cursor()
        booking_id = generate_booking_id()
        created_at = datetime.utcnow().isoformat() + "Z"
        meta = json.dumps(booking.get("meta", {}))
        cur.execute(
            "INSERT INTO bookings (id, service, date, time, location, created_at, meta) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (booking_id, booking.get("service"), booking.get("date"), booking.get("time"), booking.get("location"), created_at, meta),
        )
        conn.commit()
        conn.close()
        return {
            "id": booking_id,
            "service": booking.get("service"),
            "date": booking.get("date"),
            "time": booking.get("time"),
            "location": booking.get("location"),
            "created_at": created_at,
            "meta": booking.get("meta", {}),
        }


    def reset_bookings() -> None:
        """Delete all bookings from the database (admin action)."""
        conn = _conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM bookings")
        conn.commit()
        conn.close()


    def seed_demo_bookings():
        """Insert a few demo bookings for presentation/testing.

        Demos include itemized services, currency, and salon contact info. Dates are
        relative to today so seeded rows look current.
        """
        from datetime import datetime, timedelta

        today = datetime.now().date()
        demos = [
            {
                "service": "facial + manicure",
                "date": (today + timedelta(days=1)).isoformat(),
                "time": "10:00 AM",
                "location": "vijayawada",
                "salon": "Salon A",
                "meta": {
                    "demo": True,
                    "salon_contact": "+91-90000-00001",
                    "items": [{"name": "Cleansing Facial", "price": 1200.0}, {"name": "Manicure", "price": 800.0}],
                    "total": 2000.0,
                    "currency": "INR",
                },
            },
            {
                "service": "spa",
                "date": (today + timedelta(days=2)).isoformat(),
                "time": "11:00 AM",
                "location": "mumbai",
                "salon": "Urban Spa",
                "meta": {
                    "demo": True,
                    "salon_contact": "+91-90000-00002",
                    "items": [{"name": "Full Body Spa", "price": 2500.0}],
                    "total": 2500.0,
                    "currency": "INR",
                },
            },
            {
                "service": "doctor",
                "date": (today + timedelta(days=3)).isoformat(),
                "time": "01:00 PM",
                "location": "delhi",
                "salon": "City Clinic",
                "meta": {
                    "demo": True,
                    "salon_contact": "+91-90000-00003",
                    "items": [{"name": "Consultation", "price": 500.0}],
                    "total": 500.0,
                    "currency": "INR",
                },
            },
        ]
        for d in demos:
            # attach items and total to top-level booking where helpful
            b = {
                "service": d.get("service"),
                "date": d.get("date"),
                "time": d.get("time"),
                "location": d.get("location"),
                "meta": d.get("meta", {}),
            }
            # also set top-level items/total for receipts convenience
            if "items" in d["meta"]:
                b["items"] = d["meta"]["items"]
            if "total" in d["meta"]:
                b["total"] = d["meta"]["total"]
            add_booking(b)


    def update_booking(booking_id: str, updates: dict) -> Optional[dict]:
        conn = _conn()
        cur = conn.cursor()
        # build set clause
        fields = []
        vals = []
        for k, v in updates.items():
            if k == "meta":
                fields.append("meta = ?")
                vals.append(json.dumps(v or {}))
            else:
                fields.append(f"{k} = ?")
                vals.append(v)
        if not fields:
            conn.close()
            return None
        vals.append(booking_id)
        cur.execute(f"UPDATE bookings SET {', '.join(fields)} WHERE id = ?", tuple(vals))
        conn.commit()
        conn.close()
        # return updated booking
        matches = find_bookings()
        for b in matches:
            if b.get("id") == booking_id:
                return b
        return None


    def remove_booking(booking_id: str) -> bool:
        conn = _conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        changed = cur.rowcount
        conn.commit()
        conn.close()
        return changed > 0


    def find_bookings(service=None, date=None, time=None) -> List[Dict]:
        conn = _conn()
        cur = conn.cursor()
        query = "SELECT * FROM bookings"
        clauses = []
        vals = []
        if service:
            clauses.append("service = ?")
            vals.append(service)
        if date:
            clauses.append("date = ?")
            vals.append(date)
        if time:
            clauses.append("time = ?")
            vals.append(time)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        cur.execute(query, tuple(vals))
        rows = cur.fetchall()
        conn.close()
        out = []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r["meta"]) if r["meta"] else {}
            except Exception:
                meta = {}
            out.append({
                "id": r["id"],
                "service": r["service"],
                "date": r["date"],
                "time": r["time"],
                "location": r["location"],
                "created_at": r["created_at"],
                "meta": meta,
            })
        return out


else:
    # Fallback to JSON file if sqlite3 not available
    from uuid import uuid4
    def _ensure_file():
        if not os.path.exists(JSON_FALLBACK):
            with open(JSON_FALLBACK, "w") as f:
                json.dump([], f)


    def load_bookings():
        _ensure_file()
        with open(JSON_FALLBACK, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []


    def save_bookings(bookings):
        _ensure_file()
        with open(JSON_FALLBACK, "w") as f:
            json.dump(bookings, f, indent=2, default=str)


    def generate_booking_id(bookings=None):
        # Use UUIDs for JSON fallback as well to keep id format consistent
        return f"bkg_{uuid4().hex}"


    def add_booking(booking: dict) -> dict:
        bookings = load_bookings()
        booking_id = generate_booking_id(bookings)
        booking_entry = {
            "id": booking_id,
            "service": booking.get("service"),
            "date": booking.get("date"),
            "time": booking.get("time"),
            "location": booking.get("location"),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "meta": booking.get("meta", {})
        }
        bookings.append(booking_entry)
        save_bookings(bookings)
        return booking_entry


    def update_booking(booking_id: str, updates: dict) -> Optional[dict]:
        bookings = load_bookings()
        for b in bookings:
            if b.get("id") == booking_id:
                b.update(updates)
                save_bookings(bookings)
                return b
        return None


    def remove_booking(booking_id: str) -> bool:
        bookings = load_bookings()
        new = [b for b in bookings if b.get("id") != booking_id]
        if len(new) == len(bookings):
            return False
        save_bookings(new)
        return True


    def find_bookings(service=None, date=None, time=None):
        bookings = load_bookings()
        out = []
        for b in bookings:
            if service and b.get("service") != service:
                continue
            if date and b.get("date") != date:
                continue
            if time and b.get("time") != time:
                continue
            out.append(b)
        return out


    # Admin helpers for JSON fallback
    def reset_bookings() -> None:
        """Reset the JSON bookings file (delete all bookings)."""
        save_bookings([])


    def seed_demo_bookings():
        from datetime import datetime, timedelta

        today = datetime.now().date()
        demos = [
            {
                "service": "facial + manicure",
                "date": (today + timedelta(days=1)).isoformat(),
                "time": "10:00 AM",
                "location": "vijayawada",
                "salon": "Salon A",
                "meta": {
                    "demo": True,
                    "salon_contact": "+91-90000-00001",
                    "items": [{"name": "Cleansing Facial", "price": 1200.0}, {"name": "Manicure", "price": 800.0}],
                    "total": 2000.0,
                    "currency": "INR",
                },
            },
            {
                "service": "spa",
                "date": (today + timedelta(days=2)).isoformat(),
                "time": "11:00 AM",
                "location": "mumbai",
                "salon": "Urban Spa",
                "meta": {
                    "demo": True,
                    "salon_contact": "+91-90000-00002",
                    "items": [{"name": "Full Body Spa", "price": 2500.0}],
                    "total": 2500.0,
                    "currency": "INR",
                },
            },
            {
                "service": "doctor",
                "date": (today + timedelta(days=3)).isoformat(),
                "time": "01:00 PM",
                "location": "delhi",
                "salon": "City Clinic",
                "meta": {
                    "demo": True,
                    "salon_contact": "+91-90000-00003",
                    "items": [{"name": "Consultation", "price": 500.0}],
                    "total": 500.0,
                    "currency": "INR",
                },
            },
        ]
        for d in demos:
            b = {
                "service": d.get("service"),
                "date": d.get("date"),
                "time": d.get("time"),
                "location": d.get("location"),
                "meta": d.get("meta", {}),
            }
            if "items" in d["meta"]:
                b["items"] = d["meta"]["items"]
            if "total" in d["meta"]:
                b["total"] = d["meta"]["total"]
            add_booking(b)
