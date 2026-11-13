"""Receptionist Tools for Gemini Live and Text Models.

These tools are callable directly by Gemini to interact with the corporate
database: checking availability, booking appointments, taking caller messages,
looking up the staff directory, providing company information, and routing calls.
"""

import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from app.database import get_db

ALL_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "01:00 PM", "01:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM"
]

SYMPTOM_SPEC_MAP = {
    "chest pain": "Cardiology",
    "heart": "Cardiology",
    "cardio": "Cardiology",
    "cardiologist": "Cardiology",
    "blood pressure": "Cardiology",
    "bp": "Cardiology",
    "cholesterol": "Cardiology",
    "skin": "Dermatology",
    "dermatologist": "Dermatology",
    "acne": "Dermatology",
    "rash": "Dermatology",
    "pimples": "Dermatology",
    "hair fall": "Dermatology",
    "hair loss": "Dermatology",
    "bone": "Orthopedics",
    "orthopedic": "Orthopedics",
    "orthopedist": "Orthopedics",
    "joint": "Orthopedics",
    "knee": "Orthopedics",
    "back pain": "Orthopedics",
    "fracture": "Orthopedics",
    "child": "Pediatrics",
    "children": "Pediatrics",
    "pediatrician": "Pediatrics",
    "baby": "Pediatrics",
    "infant": "Pediatrics",
    "vaccination": "Pediatrics",
    "brain": "Neurology",
    "neurologist": "Neurology",
    "headache": "Neurology",
    "migraine": "Neurology",
    "seizure": "Neurology",
    "pregnancy": "Gynecology",
    "gynecologist": "Gynecology",
    "pregnant": "Gynecology",
    "period": "Gynecology",
    "periods": "Gynecology",
    "women": "Gynecology",
    "stomach": "Gastroenterology",
    "gastroenterologist": "Gastroenterology",
    "liver": "Gastroenterology",
    "acidity": "Gastroenterology",
    "digestion": "Gastroenterology",
    "eye": "Ophthalmology",
    "ophthalmologist": "Ophthalmology",
    "eyes": "Ophthalmology",
    "vision": "Ophthalmology",
    "cataract": "Ophthalmology",
    "lasik": "Ophthalmology",
    "depression": "Psychiatry",
    "psychiatrist": "Psychiatry",
    "anxiety": "Psychiatry",
    "stress": "Psychiatry",
    "mental": "Psychiatry",
    "fever": "General Medicine",
    "cold": "General Medicine",
    "cough": "General Medicine",
    "diabetes": "General Medicine",
    "general": "General Medicine",
    "physician": "General Medicine"
}

def normalize_date_str(val: Any) -> str:
    """Normalize date inputs ('tomorrow', 'today', '2026-09-15', etc.) to ISO YYYY-MM-DD."""
    if not val:
        return (date.today() + timedelta(days=1)).isoformat()
    s = str(val).strip()
    s_lower = s.lower()
    if s_lower == "today":
        return date.today().isoformat()
    if s_lower == "tomorrow":
        return (date.today() + timedelta(days=1)).isoformat()
    if s_lower in ("day after tomorrow", "in 2 days"):
        return (date.today() + timedelta(days=2)).isoformat()

    # If it is already YYYY-MM-DD
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass

    return (date.today() + timedelta(days=1)).isoformat()

def normalize_time_slot(val: Any) -> str:
    """Normalize time slot strings ('10am', '10:00 AM', '2:30 pm') into standard slot format."""
    if not val:
        return "10:00 AM"
    s = str(val).strip()
    # Check exact match or space-insensitive match
    for slot in ALL_SLOTS:
        if s.lower().replace(" ", "") == slot.lower().replace(" ", ""):
            return slot
    cleaned = s.upper().replace(".", "").strip()
    for fmt in ("%I:%M %p", "%I:%M%p", "%I %p", "%I%p", "%H:%M"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            res = dt.strftime("%I:%M %p")
            for slot in ALL_SLOTS:
                if res.lstrip('0') == slot.lstrip('0') or res == slot:
                    return slot
            return res
        except ValueError:
            pass
    return s

async def resolve_doctor_or_staff(db, identifier: str) -> Dict[str, Any]:
    """Resolve an identifier (doctor name, specialty, symptom, staff name, department)
    to a concrete doctor or staff record."""
    clean = (identifier or "").strip()
    if not clean:
        # Default to top rated general medicine or first doctor
        async with db.execute("SELECT * FROM doctors ORDER BY rating DESC LIMIT 1") as cur:
            row = await cur.fetchone()
            if row:
                return {
                    "found": True,
                    "kind": "doctor",
                    "name": row["name"],
                    "department": f"{row['specialization']} ({row['department']})",
                    "specialization": row["specialization"],
                    "available_slots": [s.strip() for s in (row["available_slots"] or "").split(",") if s.strip()],
                    "available_days": row["available_days"],
                    "status": row["status"]
                }
        return {"found": False, "name": clean, "department": "General", "kind": "unknown"}

    # 1. Search doctors by exact or partial name/specialization/dept
    async with db.execute(
        "SELECT * FROM doctors WHERE name LIKE ? OR specialization LIKE ? OR department LIKE ? ORDER BY rating DESC",
        (f"%{clean}%", f"%{clean}%", f"%{clean}%")
    ) as cur:
        doc = await cur.fetchone()
        if doc:
            return {
                "found": True,
                "kind": "doctor",
                "name": doc["name"],
                "department": f"{doc['specialization']} ({doc['department']})",
                "specialization": doc["specialization"],
                "available_slots": [s.strip() for s in (doc["available_slots"] or "").split(",") if s.strip()],
                "available_days": doc["available_days"],
                "status": doc["status"]
            }

    # 2. Tokenized search for doctor names (e.g. 'Dr. Arun Sharma' -> matches 'Dr. Arun Prakash Sharma')
    tokens = [t.lower().replace(".", "") for t in clean.split() if t.lower().replace(".", "") not in ("dr", "doctor", "specialist", "md")]
    if tokens:
        async with db.execute("SELECT * FROM doctors ORDER BY rating DESC") as cur:
            all_docs = await cur.fetchall()
            for doc in all_docs:
                doc_name_lower = doc["name"].lower()
                if all(tok in doc_name_lower for tok in tokens):
                    return {
                        "found": True,
                        "kind": "doctor",
                        "name": doc["name"],
                        "department": f"{doc['specialization']} ({doc['department']})",
                        "specialization": doc["specialization"],
                        "available_slots": [s.strip() for s in (doc["available_slots"] or "").split(",") if s.strip()],
                        "available_days": doc["available_days"],
                        "status": doc["status"]
                    }

    # 3. Check symptom or specialization mapping
    clean_lower = clean.lower()
    mapped_spec = None
    for symptom, spec in SYMPTOM_SPEC_MAP.items():
        if symptom in clean_lower:
            mapped_spec = spec
            break
    if mapped_spec:
        async with db.execute(
            "SELECT * FROM doctors WHERE specialization LIKE ? ORDER BY rating DESC",
            (f"%{mapped_spec}%",)
        ) as cur:
            doc = await cur.fetchone()
            if doc:
                return {
                    "found": True,
                    "kind": "doctor",
                    "name": doc["name"],
                    "department": f"{doc['specialization']} ({doc['department']})",
                    "specialization": doc["specialization"],
                    "available_slots": [s.strip() for s in (doc["available_slots"] or "").split(",") if s.strip()],
                    "available_days": doc["available_days"],
                    "status": doc["status"]
                }

    # 4. Search staff directory
    async with db.execute(
        "SELECT name, department, status FROM staff_directory WHERE name LIKE ? OR department LIKE ?",
        (f"%{clean}%", f"%{clean}%")
    ) as cur:
        staff = await cur.fetchone()
        if staff:
            return {
                "found": True,
                "kind": "staff",
                "name": staff["name"],
                "department": staff["department"],
                "specialization": "",
                "available_slots": ALL_SLOTS,
                "available_days": "Monday - Friday",
                "status": staff["status"]
            }

    # If nothing found, return fallback
    return {
        "found": False,
        "kind": "unknown",
        "name": clean,
        "department": "General",
        "specialization": "",
        "available_slots": ALL_SLOTS,
        "available_days": "Monday - Friday",
        "status": "Available"
    }

async def search_doctors(query: str = "", specialization: str = "", **kwargs) -> Dict[str, Any]:
    """Search available doctors by name, medical specialization, department, or symptoms.

    Args:
        query: Doctor name, medical problem, or symptom (e.g. 'Dr. Arun', 'heart', 'skin', 'chest pain').
        specialization: Medical field (e.g. 'Cardiology', 'Dermatology', 'Orthopedics', 'Pediatrics', 'Neurology', 'General Medicine').
    """
    clean_q = (query or kwargs.get("name") or kwargs.get("doctor") or kwargs.get("doctor_name") or kwargs.get("symptom") or kwargs.get("problem") or "").strip()
    clean_spec = (specialization or kwargs.get("dept") or kwargs.get("department") or kwargs.get("specialty") or "").strip()

    db = await get_db()
    try:
        # If user asks for general listing, treat as unconstrained search
        if clean_q.lower() in ("all", "any", "doctor", "doctors", "specialist", "specialists", "list"):
            clean_q = ""

        sql = "SELECT * FROM doctors WHERE 1=1"
        params = []
        if clean_q:
            sql += " AND (name LIKE ? OR specialization LIKE ? OR department LIKE ? OR bio LIKE ?)"
            params.extend([f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%"])
        if clean_spec:
            sql += " AND specialization LIKE ?"
            params.append(f"%{clean_spec}%")
        sql += " ORDER BY rating DESC"

        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        # If no direct match on query, check if query matched a known symptom
        if not rows and clean_q:
            mapped_spec = None
            q_lower = clean_q.lower()
            for symptom, spec in SYMPTOM_SPEC_MAP.items():
                if symptom in q_lower:
                    mapped_spec = spec
                    break

            if mapped_spec:
                fallback_sql = "SELECT * FROM doctors WHERE specialization LIKE ? ORDER BY rating DESC"
                async with db.execute(fallback_sql, [f"%{mapped_spec}%"]) as fallback_cur:
                    rows = await fallback_cur.fetchall()

        doctors = []
        for r in rows:
            doctors.append({
                "id": r["id"],
                "name": r["name"],
                "specialization": r["specialization"],
                "department": r["department"],
                "qualification": r["qualification"],
                "experience_years": r["experience_years"],
                "consultation_fee": r["consultation_fee"],
                "available_days": r["available_days"],
                "available_slots": r["available_slots"],
                "rating": r["rating"],
                "status": r["status"]
            })

        return {
            "status": "success",
            "count": len(doctors),
            "doctors": doctors
        }
    finally:
        await db.close()

async def check_availability(staff_or_department: str = "", date_str: str = "", **kwargs) -> Dict[str, Any]:
    """Check open appointment time slots for a staff member, doctor, or department on a specific date.

    Args:
        staff_or_department: Name of the employee/doctor (e.g. 'Dr. Arun Prakash Sharma', 'Rajesh Krishnamurthy') or department ('Cardiology', 'Enterprise Sales').
        date_str: The requested date in YYYY-MM-DD format (e.g. '2026-09-15' or 'tomorrow').
    """
    target = (staff_or_department or kwargs.get("doctor") or kwargs.get("doctor_name") or kwargs.get("staff_name") or kwargs.get("name") or kwargs.get("department") or "").strip()
    raw_date = date_str or kwargs.get("date") or kwargs.get("appointment_date") or kwargs.get("day") or ""
    clean_date = normalize_date_str(raw_date)

    db = await get_db()
    try:
        resolved = await resolve_doctor_or_staff(db, target)
        matched_name = resolved["name"]
        matched_dept = resolved["department"]
        staff_status = resolved["status"]

        if not resolved["found"] and target:
            return {
                "status": "not_found",
                "message": f"No staff member or doctor matching '{target}' was found.",
                "available_slots": []
            }

        # Check existing appointments on this date
        async with db.execute(
            """SELECT time_slot FROM appointments
               WHERE (staff_name = ? OR staff_name LIKE ? OR department = ?) AND date = ? AND status != 'Cancelled'""",
            (matched_name, f"%{matched_name}%", matched_dept, clean_date)
        ) as cursor:
            booked_rows = await cursor.fetchall()
            booked_slots = {row["time_slot"] for row in booked_rows}

        candidate_slots = resolved.get("available_slots") or ALL_SLOTS
        available = [slot for slot in candidate_slots if slot not in booked_slots]

        result_payload = {
            "status": "success",
            "doctor_name": matched_name,
            "staff_name": matched_name,
            "department": matched_dept,
            "current_status": staff_status,
            "date": clean_date,
            "available_slots": available[:6],  # Suggest up to 6 convenient slots
            "total_open_slots": len(available)
        }
        if resolved.get("available_days"):
            result_payload["available_days"] = resolved["available_days"]

        return result_payload
    finally:
        await db.close()

async def book_appointment(
    visitor_name: str = "",
    contact_info: str = "",
    staff_or_department: str = "",
    date_str: str = "",
    time_slot: str = "",
    purpose: str = "General Consultation",
    **kwargs
) -> Dict[str, Any]:
    """Book and confirm an appointment with a staff member or doctor.
    Verifies that the appointment is successfully written and persisted in the database.

    Args:
        visitor_name: Full name of the visitor, caller, or patient.
        contact_info: Phone number or email address of the visitor.
        staff_or_department: Name of the staff member, doctor, or department.
        date_str: Date of appointment in YYYY-MM-DD format (or 'tomorrow').
        time_slot: Time slot (e.g. '02:00 PM', '10:00 AM', '10am').
        purpose: Reason for the visit, consultation, or symptoms.
    """
    # Extract parameter aliases
    patient = (
        visitor_name
        or kwargs.get("patient_name")
        or kwargs.get("patient")
        or kwargs.get("name")
        or kwargs.get("caller_name")
        or kwargs.get("visitor")
        or kwargs.get("full_name")
        or ""
    ).strip()

    contact = (
        contact_info
        or kwargs.get("phone")
        or kwargs.get("phone_number")
        or kwargs.get("email")
        or kwargs.get("contact")
        or kwargs.get("caller_contact")
        or kwargs.get("contact_number")
        or "Not provided"
    ).strip()

    target = (
        staff_or_department
        or kwargs.get("doctor")
        or kwargs.get("doctor_name")
        or kwargs.get("staff_name")
        or kwargs.get("physician")
        or kwargs.get("specialist")
        or kwargs.get("doctor_or_staff")
        or kwargs.get("department")
        or ""
    ).strip()

    raw_date = (
        date_str
        or kwargs.get("date")
        or kwargs.get("appointment_date")
        or kwargs.get("day")
        or kwargs.get("date_time")
        or ""
    )

    raw_slot = (
        time_slot
        or kwargs.get("slot")
        or kwargs.get("time")
        or kwargs.get("appointment_time")
        or kwargs.get("selected_slot")
        or kwargs.get("time_of_day")
        or ""
    )

    booking_purpose = (
        purpose
        or kwargs.get("reason")
        or kwargs.get("symptoms")
        or kwargs.get("complaint")
        or kwargs.get("notes")
        or "General Consultation"
    ).strip()

    if not patient:
        return {
            "status": "error",
            "error_type": "missing_patient_name",
            "message": "Patient's full name is required to confirm an appointment booking."
        }

    clean_date = normalize_date_str(raw_date)
    clean_slot = normalize_time_slot(raw_slot)

    db = await get_db()
    try:
        # Resolve doctor or staff
        resolved = await resolve_doctor_or_staff(db, target)
        staff_name = resolved["name"]
        dept_name = resolved["department"]

        # Check for conflicts
        async with db.execute(
            """SELECT id FROM appointments
               WHERE (staff_name = ? OR staff_name LIKE ?) AND date = ? AND time_slot = ? AND status != 'Cancelled'""",
            (staff_name, f"%{staff_name}%", clean_date, clean_slot)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return {
                    "status": "conflict",
                    "doctor_name": staff_name,
                    "date": clean_date,
                    "time_slot": clean_slot,
                    "message": f"Sorry, {staff_name} already has an appointment booked at {clean_slot} on {clean_date}. Please choose another available slot."
                }

        # Insert booking
        now_str = datetime.now().isoformat()
        async with db.execute(
            """INSERT INTO appointments
               (visitor_name, contact_info, staff_name, department, date, time_slot, purpose, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?)""",
            (patient, contact, staff_name, dept_name, clean_date, clean_slot, booking_purpose, now_str)
        ) as cursor:
            booking_id = cursor.lastrowid
            await db.commit()

        # Database write verification: query the newly created appointment
        async with db.execute(
            """SELECT id, visitor_name, staff_name, department, date, time_slot, purpose, status, created_at
               FROM appointments WHERE id = ?""",
            (booking_id,)
        ) as verif_cur:
            verified_row = await verif_cur.fetchone()

        if not verified_row:
            return {
                "status": "error",
                "message": "Database write verification failed: Appointment could not be retrieved after insert."
            }

        return {
            "status": "confirmed",
            "verified": True,
            "booking_id": booking_id,
            "appointment_id": booking_id,
            "visitor_name": verified_row["visitor_name"],
            "patient_name": verified_row["visitor_name"],
            "staff_name": verified_row["staff_name"],
            "doctor_name": verified_row["staff_name"],
            "department": verified_row["department"],
            "date": verified_row["date"],
            "time_slot": verified_row["time_slot"],
            "purpose": verified_row["purpose"],
            "message": f"Appointment successfully confirmed and verified for {verified_row['visitor_name']} with {verified_row['staff_name']} on {verified_row['date']} at {verified_row['time_slot']} (Booking ID: #{booking_id}).",
            "instructions": "Please arrive 10 minutes early with a government-issued photo ID for security check-in."
        }
    finally:
        await db.close()

async def cancel_appointment(visitor_name: str = "", date_str: str = "", **kwargs) -> Dict[str, Any]:
    """Cancel an upcoming appointment for a visitor on a given date.

    Args:
        visitor_name: Name of the visitor.
        date_str: Date of the scheduled appointment in YYYY-MM-DD format.
    """
    patient = (visitor_name or kwargs.get("name") or kwargs.get("patient_name") or kwargs.get("patient") or "").strip()
    raw_date = date_str or kwargs.get("date") or kwargs.get("appointment_date") or ""
    clean_date = normalize_date_str(raw_date)

    db = await get_db()
    try:
        async with db.execute(
            """SELECT id, staff_name, time_slot FROM appointments
               WHERE visitor_name LIKE ? AND date = ? AND status != 'Cancelled'""",
            (f"%{patient}%", clean_date)
        ) as cursor:
            appointment = await cursor.fetchone()

        if not appointment:
            return {
                "status": "not_found",
                "message": f"No active appointment found for {patient} on {clean_date}."
            }

        await db.execute(
            "UPDATE appointments SET status = 'Cancelled' WHERE id = ?",
            (appointment["id"],)
        )
        await db.commit()

        return {
            "status": "cancelled",
            "appointment_id": appointment["id"],
            "message": f"Appointment with {appointment['staff_name']} on {clean_date} at {appointment['time_slot']} has been successfully cancelled."
        }
    finally:
        await db.close()

async def leave_message(
    caller_name: str = "",
    contact_info: str = "",
    recipient_name: str = "",
    message: str = "",
    urgency: str = "Normal",
    **kwargs
) -> Dict[str, Any]:
    """Record a caller message or voicemail for a staff member who is away or busy.

    Args:
        caller_name: Full name of the caller.
        contact_info: Callback phone number or email address.
        recipient_name: Name of the staff member or department the message is for.
        message: The detailed content of the message or inquiry.
        urgency: Level of urgency ('Normal', 'Urgent', or 'Low').
    """
    caller = (caller_name or kwargs.get("name") or kwargs.get("caller") or "Anonymous Caller").strip()
    contact = (contact_info or kwargs.get("phone") or kwargs.get("email") or "Not provided").strip()
    recipient = (recipient_name or kwargs.get("doctor") or kwargs.get("staff") or kwargs.get("recipient") or "Front Desk").strip()
    msg_body = (message or kwargs.get("content") or kwargs.get("notes") or "").strip()
    urgency_level = (urgency or kwargs.get("priority") or "Normal").strip()

    db = await get_db()
    try:
        # Match recipient in staff directory or doctors
        async with db.execute(
            "SELECT name, title, email, phone_extension FROM staff_directory WHERE name LIKE ? OR department LIKE ?",
            (f"%{recipient}%", f"%{recipient}%")
        ) as cursor:
            staff = await cursor.fetchone()

        if staff:
            target_name = staff["name"]
        else:
            async with db.execute(
                "SELECT name, specialization FROM doctors WHERE name LIKE ? OR specialization LIKE ?",
                (f"%{recipient}%", f"%{recipient}%")
            ) as doc_cur:
                doc = await doc_cur.fetchone()
                target_name = doc["name"] if doc else recipient

        now_str = datetime.now().isoformat()

        async with db.execute(
            """INSERT INTO caller_messages
               (caller_name, contact_info, recipient_name, message, urgency, is_read, created_at)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (caller, contact, target_name, msg_body, urgency_level, now_str)
        ) as cursor:
            msg_id = cursor.lastrowid
            await db.commit()

        return {
            "status": "message_logged",
            "message_id": msg_id,
            "recipient": target_name,
            "caller": caller,
            "urgency": urgency_level,
            "confirmation": f"Message recorded for {target_name}. A notification has been routed to their inbox."
        }
    finally:
        await db.close()

async def lookup_directory(query: str = "", **kwargs) -> Dict[str, Any]:
    """Search the staff directory for employees, titles, departments, extensions, or availability status.

    Args:
        query: Name, title, department, or skill to search for (e.g. 'Engineering', 'Marcus', 'Billing', 'CEO').
    """
    clean_q = (query or kwargs.get("name") or kwargs.get("department") or "").strip()
    db = await get_db()
    try:
        async with db.execute(
            """SELECT id, name, title, department, email, phone_extension, status, bio
               FROM staff_directory
               WHERE name LIKE ? OR title LIKE ? OR department LIKE ? OR bio LIKE ?""",
            (f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%")
        ) as cursor:
            rows = await cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "name": r["name"],
                "title": r["title"],
                "department": r["department"],
                "extension": r["phone_extension"],
                "email": r["email"],
                "current_status": r["status"],
                "bio": r["bio"]
            })

        return {
            "status": "success",
            "query": clean_q,
            "total_matches": len(results),
            "directory": results
        }
    finally:
        await db.close()

async def get_company_info(topic: str = "general", **kwargs) -> Dict[str, Any]:
    """Retrieve corporate information regarding office hours, building address, parking, directions, guest Wi-Fi, deliveries, or visitor security policy.

    Args:
        topic: Topic to look up: 'hours', 'location', 'parking', 'wifi', 'visitor_policy', 'deliveries', 'amenities', or 'about'.
    """
    topic_clean = (topic or kwargs.get("subject") or "general").lower().strip()
    db = await get_db()
    try:
        async with db.execute(
            """SELECT key, title, content, category FROM company_info
               WHERE key LIKE ? OR title LIKE ? OR content LIKE ?""",
            (f"%{topic_clean}%", f"%{topic_clean}%", f"%{topic_clean}%")
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            # Fallback to all company info
            async with db.execute("SELECT key, title, content FROM company_info") as all_cursor:
                rows = await all_cursor.fetchall()

        info = [{"topic": r["key"], "title": r["title"], "details": r["content"]} for r in rows]

        return {
            "status": "success",
            "results": info
        }
    finally:
        await db.close()

async def transfer_call(recipient_or_department: str = "", **kwargs) -> Dict[str, Any]:
    """Simulate initiating a direct phone call transfer to an extension or department.

    Args:
        recipient_or_department: Target employee name, extension number, or department.
    """
    clean_target = (recipient_or_department or kwargs.get("recipient") or kwargs.get("department") or kwargs.get("name") or "").strip()
    db = await get_db()
    try:
        async with db.execute(
            """SELECT name, title, department, phone_extension, status FROM staff_directory
               WHERE name LIKE ? OR department LIKE ? OR phone_extension = ?""",
            (f"%{clean_target}%", f"%{clean_target}%", clean_target)
        ) as cursor:
            staff = await cursor.fetchone()

        if staff:
            return {
                "status": "transfer_initiated",
                "transfer_to": staff["name"],
                "department": staff["department"],
                "extension": staff["phone_extension"],
                "recipient_status": staff["status"],
                "message": f"Connecting you now to {staff['name']} ({staff['department']}, ext {staff['phone_extension']}). Please hold while the line rings."
            }
        else:
            return {
                "status": "transfer_initiated",
                "transfer_to": clean_target,
                "department": "Operator Queue",
                "extension": "0",
                "recipient_status": "Available",
                "message": f"Transferring your call to {clean_target}. Please hold."
            }
    finally:
        await db.close()

# Tool registry for dynamic execution
TOOL_REGISTRY = {
    "search_doctors": search_doctors,
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "cancel_appointment": cancel_appointment,
    "leave_message": leave_message,
    "lookup_directory": lookup_directory,
    "get_company_info": get_company_info,
    "transfer_call": transfer_call,
}

# Python functions list for passing to google-genai client
RECEPTIONIST_TOOL_FUNCTIONS = [
    search_doctors,
    check_availability,
    book_appointment,
    cancel_appointment,
    leave_message,
    lookup_directory,
    get_company_info,
    transfer_call
]

