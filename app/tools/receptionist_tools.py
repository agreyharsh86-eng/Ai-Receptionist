"""Receptionist Tools for Gemini Live and Text Models.

These tools are callable directly by Gemini to interact with the corporate
database: checking availability, booking appointments, taking caller messages,
looking up the staff directory, providing company information, and routing calls.
"""

import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from app.database_mongo import (
    list_doctors,
    list_staff,
    find_staff_match,
    get_booked_slots,
    create_appointment_record,
    find_and_cancel_appointment,
    create_message_record,
    list_company_info,
)

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

def _doctor_to_resolved(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "found": True,
        "kind": "doctor",
        "id": str(doc.get("_id") or doc.get("id") or ""),
        "name": doc["name"],
        "department": f"{doc['specialization']} ({doc['department']})",
        "specialization": doc["specialization"],
        "available_slots": [s.strip() for s in (doc.get("available_slots") or "").split(",") if s.strip()],
        "available_days": doc.get("available_days", ""),
        "status": doc.get("status", "Available"),
    }


async def resolve_doctor_or_staff(identifier: str) -> Dict[str, Any]:
    """Resolve an identifier (doctor name, specialty, symptom, staff name, department)
    to a concrete doctor or staff record."""
    clean = (identifier or "").strip()
    all_docs = await list_doctors()

    if not clean:
        if all_docs:
            return _doctor_to_resolved(all_docs[0])
        return {"found": False, "name": clean, "department": "General", "kind": "unknown"}

    clean_lower = clean.lower()

    # 1. Exact or partial match on doctor name / specialization / department
    for doc in all_docs:
        if (
            clean_lower in doc["name"].lower()
            or clean_lower in doc["specialization"].lower()
            or clean_lower in doc["department"].lower()
        ):
            return _doctor_to_resolved(doc)

    # 2. Tokenized search for doctor names (e.g. 'Dr. Arun Sharma' -> matches 'Dr. Arun Prakash Sharma')
    tokens = [t.lower().replace(".", "") for t in clean.split() if t.lower().replace(".", "") not in ("dr", "doctor", "specialist", "md")]
    if tokens:
        for doc in all_docs:
            doc_name_lower = doc["name"].lower()
            if all(tok in doc_name_lower for tok in tokens):
                return _doctor_to_resolved(doc)

    # 3. Symptom or specialization mapping
    mapped_spec = None
    for symptom, spec in SYMPTOM_SPEC_MAP.items():
        if symptom in clean_lower:
            mapped_spec = spec
            break
    if mapped_spec:
        spec_docs = await list_doctors(specialization=mapped_spec)
        if spec_docs:
            return _doctor_to_resolved(spec_docs[0])

    # 4. Search staff directory
    staff = await find_staff_match(clean)
    if staff:
        return {
            "found": True,
            "kind": "staff",
            "id": str(staff.get("_id") or staff.get("id") or ""),
            "name": staff["name"],
            "department": staff["department"],
            "specialization": "",
            "available_slots": ALL_SLOTS,
            "available_days": "Monday - Friday",
            "status": staff.get("status", "Available"),
        }

    return {
        "found": False,
        "kind": "unknown",
        "id": "",
        "name": clean,
        "department": "General",
        "specialization": "",
        "available_slots": ALL_SLOTS,
        "available_days": "Monday - Friday",
        "status": "Available",
    }

async def search_doctors(query: str = "", specialization: str = "", **kwargs) -> Dict[str, Any]:
    """Search available doctors by name, medical specialization, department, or symptoms.

    Args:
        query: Doctor name, medical problem, or symptom (e.g. 'Dr. Arun', 'heart', 'skin', 'chest pain').
        specialization: Medical field (e.g. 'Cardiology', 'Dermatology', 'Orthopedics', 'Pediatrics', 'Neurology', 'General Medicine').
    """
    clean_q = (query or kwargs.get("name") or kwargs.get("doctor") or kwargs.get("doctor_name") or kwargs.get("symptom") or kwargs.get("problem") or "").strip()
    clean_spec = (specialization or kwargs.get("dept") or kwargs.get("department") or kwargs.get("specialty") or "").strip()

    if clean_q.lower() in ("all", "any", "doctor", "doctors", "specialist", "specialists", "list"):
        clean_q = ""

    rows = await list_doctors(specialization=clean_spec or None, query=clean_q or None)

    # If no direct match on query, check if query matched a known symptom
    if not rows and clean_q:
        mapped_spec = None
        q_lower = clean_q.lower()
        for symptom, spec in SYMPTOM_SPEC_MAP.items():
            if symptom in q_lower:
                mapped_spec = spec
                break
        if mapped_spec:
            rows = await list_doctors(specialization=mapped_spec)

    doctors = []
    for r in rows:
        doctors.append({
            "id": r.get("id") or r.get("_id"),
            "name": r["name"],
            "specialization": r["specialization"],
            "department": r["department"],
            "qualification": r["qualification"],
            "experience_years": r["experience_years"],
            "consultation_fee": r["consultation_fee"],
            "available_days": r["available_days"],
            "available_slots": r["available_slots"],
            "rating": r["rating"],
            "status": r["status"],
        })

    return {
        "status": "success",
        "count": len(doctors),
        "doctors": doctors,
    }

async def check_availability(staff_or_department: str = "", date_str: str = "", **kwargs) -> Dict[str, Any]:
    """Check open appointment time slots for a staff member, doctor, or department on a specific date.

    Args:
        staff_or_department: Name of the employee/doctor (e.g. 'Dr. Arun Prakash Sharma', 'Rajesh Krishnamurthy') or department ('Cardiology', 'Enterprise Sales').
        date_str: The requested date in YYYY-MM-DD format (e.g. '2026-09-15' or 'tomorrow').
    """
    target = (staff_or_department or kwargs.get("doctor") or kwargs.get("doctor_name") or kwargs.get("staff_name") or kwargs.get("name") or kwargs.get("department") or "").strip()
    raw_date = date_str or kwargs.get("date") or kwargs.get("appointment_date") or kwargs.get("day") or ""
    clean_date = normalize_date_str(raw_date)

    resolved = await resolve_doctor_or_staff(target)
    matched_name = resolved["name"]
    matched_dept = resolved["department"]
    staff_status = resolved["status"]

    if not resolved["found"] and target:
        return {
            "status": "not_found",
            "message": f"No staff member or doctor matching '{target}' was found.",
            "available_slots": []
        }

    booked_slots = await get_booked_slots(matched_name, matched_dept, clean_date)

    candidate_slots = resolved.get("available_slots") or ALL_SLOTS
    available = [slot for slot in candidate_slots if slot not in booked_slots]

    result_payload = {
        "status": "success",
        "doctor_name": matched_name,
        "staff_name": matched_name,
        "department": matched_dept,
        "current_status": staff_status,
        "date": clean_date,
        "available_slots": available[:6],
        "total_open_slots": len(available)
    }
    if resolved.get("available_days"):
        result_payload["available_days"] = resolved["available_days"]

    return result_payload

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

    resolved = await resolve_doctor_or_staff(target)
    staff_name = resolved["name"]
    dept_name = resolved["department"]
    doctor_id = resolved.get("id") if resolved.get("kind") == "doctor" else None
    staff_id = resolved.get("id") if resolved.get("kind") == "staff" else None
    user_id = kwargs.get("user_id")

    result = await create_appointment_record(
        visitor_name=patient,
        contact_info=contact,
        provider_name=staff_name,
        department=dept_name,
        date_str=clean_date,
        time_slot=clean_slot,
        purpose=booking_purpose,
        doctor_id=doctor_id,
        staff_id=staff_id,
        user_id=user_id,
    )

    if result.get("conflict"):
        return {
            "status": "conflict",
            "doctor_name": staff_name,
            "date": clean_date,
            "time_slot": clean_slot,
            "message": f"Sorry, {staff_name} already has an appointment booked at {clean_slot} on {clean_date}. Please choose another available slot."
        }

    verified_row = result.get("appointment")
    if not verified_row:
        return {
            "status": "error",
            "message": "Database write verification failed: Appointment could not be retrieved after insert."
        }

    booking_id = verified_row.get("id") or verified_row.get("_id")
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

async def cancel_appointment(visitor_name: str = "", date_str: str = "", **kwargs) -> Dict[str, Any]:
    """Cancel an upcoming appointment for a visitor on a given date.

    Args:
        visitor_name: Name of the visitor.
        date_str: Date of the scheduled appointment in YYYY-MM-DD format.
    """
    patient = (visitor_name or kwargs.get("name") or kwargs.get("patient_name") or kwargs.get("patient") or "").strip()
    raw_date = date_str or kwargs.get("date") or kwargs.get("appointment_date") or ""
    clean_date = normalize_date_str(raw_date)

    appointment = await find_and_cancel_appointment(patient, clean_date)

    if not appointment:
        return {
            "status": "not_found",
            "message": f"No active appointment found for {patient} on {clean_date}."
        }

    return {
        "status": "cancelled",
        "appointment_id": appointment.get("id") or appointment.get("_id"),
        "message": f"Appointment with {appointment['staff_name']} on {clean_date} at {appointment['time_slot']} has been successfully cancelled."
    }

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

    staff = await find_staff_match(recipient)
    if staff:
        target_name = staff["name"]
    else:
        docs = await list_doctors(query=recipient)
        target_name = docs[0]["name"] if docs else recipient

    saved_msg = await create_message_record(
        caller_name=caller,
        contact_info=contact,
        recipient_name=target_name,
        message=msg_body,
        urgency=urgency_level,
    )

    return {
        "status": "message_logged",
        "message_id": saved_msg.get("id") or saved_msg.get("_id"),
        "recipient": target_name,
        "caller": caller,
        "urgency": urgency_level,
        "confirmation": f"Message recorded for {target_name}. A notification has been routed to their inbox."
    }

async def lookup_directory(query: str = "", **kwargs) -> Dict[str, Any]:
    """Search the staff directory for employees, titles, departments, extensions, or availability status.

    Args:
        query: Name, title, department, or skill to search for (e.g. 'Engineering', 'Marcus', 'Billing', 'CEO').
    """
    clean_q = (query or kwargs.get("name") or kwargs.get("department") or "").strip()
    rows = await list_staff(clean_q or None)

    results = []
    for r in rows:
        results.append({
            "name": r["name"],
            "title": r["title"],
            "department": r["department"],
            "extension": r["phone_extension"],
            "email": r["email"],
            "current_status": r["status"],
            "bio": r.get("bio", "")
        })

    return {
        "status": "success",
        "query": clean_q,
        "total_matches": len(results),
        "directory": results
    }

async def get_company_info(topic: str = "general", **kwargs) -> Dict[str, Any]:
    """Retrieve corporate information regarding office hours, building address, parking, directions, guest Wi-Fi, deliveries, or visitor security policy.

    Args:
        topic: Topic to look up: 'hours', 'location', 'parking', 'wifi', 'visitor_policy', 'deliveries', 'amenities', or 'about'.
    """
    topic_clean = (topic or kwargs.get("subject") or "general").lower().strip()
    rows = await list_company_info(topic_clean)
    info = [{"topic": r["key"], "title": r["title"], "details": r["content"]} for r in rows]

    return {
        "status": "success",
        "results": info
    }

async def transfer_call(recipient_or_department: str = "", **kwargs) -> Dict[str, Any]:
    """Simulate initiating a direct phone call transfer to an extension or department.

    Args:
        recipient_or_department: Target employee name, extension number, or department.
    """
    clean_target = (recipient_or_department or kwargs.get("recipient") or kwargs.get("department") or kwargs.get("name") or "").strip()
    staff = await find_staff_match(clean_target)

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

