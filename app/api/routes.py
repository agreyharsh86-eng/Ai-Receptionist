import inspect
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import re
from app.database import get_db
import app.config as config
from app.tools.receptionist_tools import (
    search_doctors,
    check_availability,
    book_appointment,
    cancel_appointment,
    leave_message,
    lookup_directory,
    get_company_info,
    transfer_call,
    TOOL_REGISTRY,
    RECEPTIONIST_TOOL_FUNCTIONS
)

logger = logging.getLogger("api_routes")
router = APIRouter(prefix="/api")

# Models
class AppointmentCreate(BaseModel):
    visitor_name: str
    contact_info: str
    staff_or_department: str
    date: str
    time_slot: str
    purpose: Optional[str] = "Business Consultation"

class MessageCreate(BaseModel):
    caller_name: str
    contact_info: str
    recipient_name: str
    message: str
    urgency: Optional[str] = "Normal"

class TextChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    api_key: Optional[str] = None

class ApiKeyUpdate(BaseModel):
    api_key: str

# 1. Company Info Endpoints
@router.get("/company")
async def get_company_details():
    db = await get_db()
    try:
        async with db.execute("SELECT key, category, title, content FROM company_info") as cursor:
            rows = await cursor.fetchall()
            info = [dict(r) for r in rows]

        return {
            "name": config.COMPANY_NAME,
            "industry": config.COMPANY_INDUSTRY,
            "location": config.COMPANY_LOCATION,
            "hours": config.COMPANY_HOURS,
            "receptionist_name": config.RECEPTIONIST_NAME,
            "knowledge_base": info
        }
    finally:
        await db.close()

# 2. Staff Directory Endpoints
@router.get("/directory")
async def get_staff_directory(q: Optional[str] = None):
    db = await get_db()
    try:
        if q:
            async with db.execute(
                """SELECT id, name, title, department, email, phone_extension, status, bio
                   FROM staff_directory
                   WHERE name LIKE ? OR title LIKE ? OR department LIKE ?""",
                (f"%{q}%", f"%{q}%", f"%{q}%")
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT id, name, title, department, email, phone_extension, status, bio FROM staff_directory ORDER BY department, name"
            ) as cursor:
                rows = await cursor.fetchall()

        return [dict(r) for r in rows]
    finally:
        await db.close()

# 3. Appointments Endpoints
@router.get("/appointments")
async def list_appointments(status: Optional[str] = None):
    db = await get_db()
    try:
        if status:
            async with db.execute(
                "SELECT * FROM appointments WHERE status = ? ORDER BY date ASC, time_slot ASC",
                (status,)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM appointments ORDER BY date ASC, time_slot ASC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()

@router.post("/appointments")
async def create_appointment_endpoint(app_data: AppointmentCreate):
    res = await book_appointment(
        visitor_name=app_data.visitor_name,
        contact_info=app_data.contact_info,
        staff_or_department=app_data.staff_or_department,
        date_str=app_data.date,
        time_slot=app_data.time_slot,
        purpose=app_data.purpose or "General Business Consultation"
    )
    if res.get("status") == "conflict":
        raise HTTPException(status_code=409, detail=res.get("message"))
    return res

@router.delete("/appointments/{appointment_id}")
async def cancel_appointment_by_id(appointment_id: int):
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Appointment not found")

        await db.execute(
            "UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appointment_id,)
        )
        await db.commit()
        return {"status": "success", "message": f"Appointment #{appointment_id} marked as cancelled."}
    finally:
        await db.close()

# 4. Caller Messages Endpoints
@router.get("/messages")
async def list_messages(unread_only: bool = False):
    db = await get_db()
    try:
        if unread_only:
            async with db.execute(
                "SELECT * FROM caller_messages WHERE is_read = 0 ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM caller_messages ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()

@router.post("/messages")
async def create_message_endpoint(msg: MessageCreate):
    res = await leave_message(
        caller_name=msg.caller_name,
        contact_info=msg.contact_info,
        recipient_name=msg.recipient_name,
        message=msg.message,
        urgency=msg.urgency or "Normal"
    )
    return res

@router.patch("/messages/{message_id}/read")
async def mark_message_read(message_id: int):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE caller_messages SET is_read = 1 WHERE id = ?", (message_id,)
        )
        await db.commit()
        return {"status": "success"}
    finally:
        await db.close()

@router.delete("/messages/{message_id}")
async def delete_message(message_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM caller_messages WHERE id = ?", (message_id,))
        await db.commit()
        return {"status": "success"}
    finally:
        await db.close()

# 5. Call Logs
@router.get("/call-logs")
async def list_call_logs():
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM call_logs ORDER BY started_at DESC LIMIT 30"
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()

# 5.5 Doctors Directory
@router.get("/doctors")
async def list_doctors(specialization: Optional[str] = None, q: Optional[str] = None):
    db = await get_db()
    try:
        if q:
            async with db.execute(
                """SELECT * FROM doctors
                   WHERE name LIKE ? OR specialization LIKE ? OR department LIKE ? OR bio LIKE ?
                   ORDER BY rating DESC""",
                (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
            ) as cursor:
                rows = await cursor.fetchall()
        elif specialization:
            async with db.execute(
                "SELECT * FROM doctors WHERE specialization LIKE ? ORDER BY rating DESC",
                (f"%{specialization}%",)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM doctors ORDER BY rating DESC"
            ) as cursor:
                rows = await cursor.fetchall()

        return [dict(r) for r in rows]
    finally:
        await db.close()

@router.get("/doctors/specializations")
@router.get("/doctors/specializations/list")
async def list_specializations():
    db = await get_db()
    try:
        async with db.execute("SELECT DISTINCT specialization FROM doctors ORDER BY specialization") as cursor:
            rows = await cursor.fetchall()
        return [row["specialization"] for row in rows]
    finally:
        await db.close()

@router.get("/doctors/{doctor_id}")
async def get_doctor(doctor_id: int):
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Doctor not found")
            return dict(row)
    finally:
        await db.close()

# 6. Configuration Endpoints
@router.get("/config")
async def get_config():
    return {
        "has_api_key": config.has_valid_api_key(),
        "receptionist_name": config.RECEPTIONIST_NAME,
        "company_name": config.COMPANY_NAME,
        "live_model": config.GEMINI_LIVE_MODEL,
        "fallback_model": config.GEMINI_FALLBACK_MODEL,
        "default_voice": config.DEFAULT_VOICE,
        "available_voices": ["Aoede", "Puck", "Charon", "Fenrir", "Kore"]
    }

@router.post("/config/key")
async def set_api_key(data: ApiKeyUpdate):
    if not data.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    config.GEMINI_API_KEY = data.api_key.strip()
    return {"status": "success", "message": "API key updated successfully"}

async def handle_conversational_chat(query: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Conversational AI Reasoning Engine for Healthcare Front-Desk Concierge.
    
    Provides natural multi-turn dialogue, symptom matching, doctor directory search,
    live calendar slot inspection, missing-info collection, explicit confirmation checks,
    and actual database booking execution.
    """
    raw_query = query.strip()
    text = raw_query.lower()
    actions_taken = []
    hist = history or []

    # Specialist Doctor Directory definition
    doctor_catalog = [
        {
            "name": "Dr. Arun Prakash Sharma",
            "specialization": "Cardiology",
            "department": "Heart & Vascular Centre",
            "keywords": ["arun", "sharma", "cardiology", "cardiologist", "heart", "chest pain", "bp", "blood pressure", "cholesterol", "cardio", "angina"]
        },
        {
            "name": "Dr. Priyanka Venkatesh",
            "specialization": "Dermatology",
            "department": "Skin & Aesthetic Clinic",
            "keywords": ["priyanka", "venkatesh", "dermatology", "dermatologist", "skin", "acne", "rash", "pimples", "hair fall", "hair loss", "eczema", "allergy"]
        },
        {
            "name": "Dr. Rajiv Malhotra",
            "specialization": "Orthopedics",
            "department": "Bone & Joint Institute",
            "keywords": ["rajiv", "malhotra", "orthopedics", "orthopedic", "bone", "joint", "knee", "knee pain", "back pain", "fracture", "spine", "arthritis"]
        },
        {
            "name": "Dr. Kavitha Raghunathan",
            "specialization": "Pediatrics",
            "department": "Children's Health Centre",
            "keywords": ["kavitha", "raghunathan", "pediatrics", "pediatrician", "pediatric", "child", "children", "baby", "infant", "vaccination", "kids"]
        },
        {
            "name": "Dr. Siddharth Joshi",
            "specialization": "Neurology",
            "department": "Brain & Neuroscience Institute",
            "keywords": ["siddharth", "joshi", "neurology", "neurologist", "brain", "headache", "migraine", "seizure", "paralysis", "nerve", "neurological"]
        },
        {
            "name": "Dr. Meenakshi Sundaram",
            "specialization": "Gynecology & Obstetrics",
            "department": "Women's Health Centre",
            "keywords": ["meenakshi", "sundaram", "gynecology", "gynecologist", "obstetrics", "women", "pregnancy", "pregnant", "period", "periods", "maternity"]
        },
        {
            "name": "Dr. Harsh Vardhan Patel",
            "specialization": "Gastroenterology",
            "department": "Digestive Health Centre",
            "keywords": ["harsh", "patel", "gastroenterology", "gastroenterologist", "gastro", "stomach", "liver", "acidity", "indigestion", "gas", "digestive", "gut"]
        },
        {
            "name": "Dr. Anjali Krishnamurthy",
            "specialization": "Ophthalmology",
            "department": "Vision & Eye Care Centre",
            "keywords": ["anjali", "krishnamurthy", "ophthalmology", "ophthalmologist", "eye", "eyes", "vision", "glasses", "cataract", "lasik", "sight"]
        },
        {
            "name": "Dr. Nikhil Banerjee",
            "specialization": "Psychiatry",
            "department": "Mental Health & Wellness Centre",
            "keywords": ["nikhil", "banerjee", "psychiatry", "psychiatrist", "mental", "wellness", "therapy", "depression", "anxiety", "stress", "sleep", "counseling"]
        },
        {
            "name": "Dr. Lakshmi Narayanan Iyer",
            "specialization": "General Medicine",
            "department": "Internal Medicine & Diagnostics",
            "keywords": ["lakshmi", "iyer", "general medicine", "general physician", "physician", "fever", "checkup", "cold", "cough", "diabetes", "sugar", "sick", "weakness", "pain", "flu"]
        }
    ]

    # Combine context across history
    combined_user_text = ""
    last_model_message = ""
    for h in hist:
        role = h.get("role", "")
        content = h.get("text") or h.get("content") or ""
        if role in ("user", "human"):
            combined_user_text += " " + content.lower()
        elif role in ("model", "assistant"):
            last_model_message = content

    combined_user_text += " " + text

    # Check if the previous model message was an explicit confirmation prompt
    is_confirm_prompt = False
    if last_model_message:
        lmm_lower = last_model_message.lower()
        if any(p in lmm_lower for p in [
            "would you like me to confirm", "confirm this booking", "shall i confirm",
            "shall i go ahead and book", "confirm and finalize", "should i proceed with booking",
            "would you like me to book this", "shall i finalize"
        ]):
            is_confirm_prompt = True

    # -------------------------------------------------------------------------
    # Entity Extraction (Doctor, Date, Slot, Name, Contact, Purpose)
    # -------------------------------------------------------------------------

    # 1. Doctor Detection
    detected_doctor = None
    # Check if last model message proposed a doctor
    if last_model_message:
        for doc in doctor_catalog:
            if doc["name"].lower() in last_model_message.lower():
                detected_doctor = doc
                break

    # If user mentioned a new doctor or specialty in current turn, prioritize that
    for doc in doctor_catalog:
        if doc["name"].lower() in text:
            detected_doctor = doc
            break
        for kw in doc["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                detected_doctor = doc
                break
        if detected_doctor:
            break

    # Otherwise check combined user text
    if not detected_doctor:
        for doc in doctor_catalog:
            if doc["name"].lower() in combined_user_text:
                detected_doctor = doc
                break
            for kw in doc["keywords"]:
                if re.search(r'\b' + re.escape(kw) + r'\b', combined_user_text):
                    detected_doctor = doc
                    break
            if detected_doctor:
                break

    # 2. Date Detection
    detected_date = None
    if "tomorrow" in text:
        detected_date = (date.today() + timedelta(days=1)).isoformat()
    elif "today" in text:
        detected_date = date.today().isoformat()
    elif "day after tomorrow" in text:
        detected_date = (date.today() + timedelta(days=2)).isoformat()
    else:
        # Check for explicit ISO date (YYYY-MM-DD)
        date_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', text)
        if date_match:
            detected_date = date_match.group(1)
        elif "tomorrow" in combined_user_text:
            detected_date = (date.today() + timedelta(days=1)).isoformat()
        elif "today" in combined_user_text:
            detected_date = date.today().isoformat()
        else:
            date_match_hist = re.search(r'\b(202\d-\d{2}-\d{2})\b', combined_user_text + " " + last_model_message)
            if date_match_hist:
                detected_date = date_match_hist.group(1)
            else:
                detected_date = (date.today() + timedelta(days=1)).isoformat()

    # 3. Time Slot Detection
    standard_slots = [
        "08:30 AM", "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
        "11:00 AM", "11:30 AM", "01:00 PM", "01:30 PM", "02:00 PM",
        "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM"
    ]
    detected_slot = None
    for s in standard_slots:
        if s.lower() in text:
            detected_slot = s
            break

    if not detected_slot:
        t_match = re.search(r'\b(0?[1-9]|1[0-2])(?::([0-5][0-9]))?\s*(am|pm)\b', text)
        if t_match:
            hr = int(t_match.group(1))
            mn = t_match.group(2) or "00"
            period = t_match.group(3).upper()
            detected_slot = f"{hr:02d}:{mn} {period}"

    if not detected_slot:
        for s in standard_slots:
            if s.lower() in combined_user_text:
                detected_slot = s
                break

    if not detected_slot and last_model_message:
        for s in standard_slots:
            if s.lower() in last_model_message.lower():
                detected_slot = s
                break

    # 4. Patient Name Detection
    detected_name = None
    name_patterns = [
        r"(?:my name is|i am|patient name is|name is|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:my name is|i am|patient name is|name is|this is)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        r"(?:for patient|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:for patient|for)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
    ]
    for pat in name_patterns:
        m = re.search(pat, raw_query, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            if cand.lower() not in [
                "an appointment", "appointment", "doctor", "consultation", "cardiologist",
                "dermatologist", "today", "tomorrow", "me", "him", "her", "cardiology", "general"
            ]:
                detected_name = cand.title()
                break

    if not detected_name:
        for h in reversed(hist):
            if h.get("role") in ("user", "human"):
                u_text = h.get("text") or h.get("content") or ""
                for pat in name_patterns:
                    m = re.search(pat, u_text, re.IGNORECASE)
                    if m:
                        cand = m.group(1).strip()
                        if cand.lower() not in [
                            "an appointment", "appointment", "doctor", "consultation",
                            "tomorrow", "today", "me", "him", "her"
                        ]:
                            detected_name = cand.title()
                            break
                if detected_name:
                    break

    # If last model message explicitly asked for patient name and user provided "FirstName LastName"
    if not detected_name and last_model_message and ("name" in last_model_message.lower()):
        parts = raw_query.split(",")
        first_part = parts[0].strip()
        words = first_part.split()
        if 1 <= len(words) <= 3 and all(w.replace("-", "").isalpha() for w in words):
            if words[0].lower() not in ["yes", "no", "sure", "ok", "okay", "cancel", "tomorrow", "today", "book", "hi", "hello"]:
                detected_name = first_part.title()

    # 5. Patient Contact Detection (Phone or Email)
    detected_contact = None
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10}\b|\b\d{5}[-.\s]?\d{5}\b', raw_query)
    if phone_match:
        detected_contact = phone_match.group(0).strip()
    if not detected_contact:
        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_query)
        if email_match:
            detected_contact = email_match.group(0).strip()
    if not detected_contact:
        for h in reversed(hist):
            if h.get("role") in ("user", "human"):
                u_text = h.get("text") or h.get("content") or ""
                p_m = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10}\b|\b\d{5}[-.\s]?\d{5}\b', u_text)
                if p_m:
                    detected_contact = p_m.group(0).strip()
                    break
                e_m = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', u_text)
                if e_m:
                    detected_contact = e_m.group(0).strip()
                    break

    # -------------------------------------------------------------------------
    # Confirmation Flow Handling (Step 8 & 9 of Core Protocol)
    # -------------------------------------------------------------------------
    is_affirmative = any(re.search(r'\b' + re.escape(w) + r'\b', text) for w in [
        "yes", "yeah", "yep", "sure", "confirm", "proceed", "go ahead", "book it",
        "please do", "ok", "okay", "correct", "sounds good", "do it", "finalize"
    ])
    is_negative = any(re.search(r'\b' + re.escape(w) + r'\b', text) for w in [
        "no", "cancel", "wait", "stop", "don't", "not", "change", "rebook"
    ])

    if is_confirm_prompt and is_affirmative and not is_negative:
        # Patient explicitly confirmed booking!
        target_doc = detected_doctor["name"] if detected_doctor else "Dr. Arun Prakash Sharma"
        spec = detected_doctor["specialization"] if detected_doctor else "Specialist Consultation"
        pat_name = detected_name or "Guest Patient"
        pat_contact = detected_contact or "+91-98765-43210"
        appt_date = detected_date or (date.today() + timedelta(days=1)).isoformat()
        slot = detected_slot or "10:00 AM"

        # Execute booking through verified database tool
        res = await book_appointment(
            visitor_name=pat_name,
            contact_info=pat_contact,
            staff_or_department=target_doc,
            date_str=appt_date,
            time_slot=slot,
            purpose=f"Medical consultation ({spec})"
        )
        actions_taken.append({
            "tool": "book_appointment",
            "args": {
                "visitor_name": pat_name,
                "contact_info": pat_contact,
                "staff_or_department": target_doc,
                "date": appt_date,
                "time_slot": slot
            }
        })

        if res.get("status") == "confirmed":
            b_id = res.get("booking_id")
            display_date = "tomorrow" if appt_date == (date.today() + timedelta(days=1)).isoformat() else f"on {appt_date}"
            return {
                "reply": f"Your appointment has been successfully booked and confirmed! Your Booking ID is #{b_id}. You are scheduled with {target_doc} {display_date} at {slot} for {pat_name}. A confirmed appointment record has been saved to the hospital registry. Please arrive 10 minutes early at our front desk with a photo ID.",
                "actions": actions_taken
            }
        else:
            return {
                "reply": f"I apologize, but {res.get('message', 'that time slot is no longer available')}. Would you like me to check other available slots for {target_doc}?",
                "actions": actions_taken
            }

    elif is_confirm_prompt and is_negative:
        return {
            "reply": "Understood, I have cancelled the pending booking request. Would you like to select a different doctor, change the date, or pick another time slot?",
            "actions": []
        }

    # -------------------------------------------------------------------------
    # Doctor Directory Listing Inquiry
    # -------------------------------------------------------------------------
    is_list_doctors = (
        any(p in text for p in [
            "which doctors", "who are the doctors", "list doctors", "all doctors",
            "available doctors", "what doctors", "show doctors", "view doctors", "names of doctors"
        ]) or (
            "doctor" in text and "available" in text and not any(w in text for w in ["book", "reserve", "schedule"])
        )
    )
    if is_list_doctors:
        res = await search_doctors(query="")
        actions_taken.append({"tool": "search_doctors", "args": {"query": ""}})
        doc_list = res.get("doctors", [])
        doc_lines = "\n".join([f"• {d['name']} ({d['specialization']}) — {d['qualification']}, rated {d['rating']}/5 ⭐" for d in doc_list[:10]])
        return {
            "reply": f"At {config.COMPANY_NAME}, we have 10 specialist doctors available across all departments:\n{doc_lines}\n\nWhich doctor or medical specialty would you like to consult?",
            "actions": actions_taken
        }

    # -------------------------------------------------------------------------
    # Conversational Appointment Booking Workflow (Steps 1 to 7)
    # -------------------------------------------------------------------------
    is_booking_intent = any(w in text for w in [
        "book", "reserve", "appointment", "schedule", "consult", "see a doctor", "doctor"
    ]) or (detected_doctor is not None and any(w in text for w in ["yes", "want", "like", "need", "please", "can i", "could i", "slot", "tomorrow", "today", "am", "pm"]))

    if detected_doctor or is_booking_intent:
        target_doc = detected_doctor or doctor_catalog[0]
        doc_name = target_doc["name"]
        spec = target_doc["specialization"]
        dept = target_doc["department"]
        appt_date = detected_date or (date.today() + timedelta(days=1)).isoformat()
        date_label = "tomorrow" if appt_date == (date.today() + timedelta(days=1)).isoformat() else f"on {appt_date}"

        # Step 4 & 5: Check real availability from database
        avail_res = await check_availability(staff_or_department=doc_name, date_str=appt_date)
        actions_taken.append({
            "tool": "check_availability",
            "args": {"staff_or_department": doc_name, "date_str": appt_date}
        })
        open_slots = avail_res.get("available_slots", [])

        has_slot = detected_slot is not None
        has_name = detected_name is not None
        has_contact = detected_contact is not None

        # Step 8: If all details are collected, ASK FOR EXPLICIT CONFIRMATION
        if has_slot and has_name and has_contact:
            return {
                "reply": f"Thank you, {detected_name}. I have an appointment ready with {doc_name} ({spec}) {date_label} at {detected_slot} for {detected_name} (contact: {detected_contact}). Would you like me to confirm this booking for you?",
                "actions": actions_taken
            }

        # Step 6: Present available slots and ask for missing details
        slots_str = ", ".join(open_slots[:4]) if open_slots else "no open slots"

        if not has_slot:
            if not has_name and not has_contact:
                return {
                    "reply": f"We have {doc_name}, our specialist in {spec} at the {dept}. Available slots {date_label} are {slots_str}. Which time slot works best for you, and could you please provide your full name and phone number?",
                    "actions": actions_taken
                }
            elif not has_name:
                return {
                    "reply": f"Available slots for {doc_name} {date_label} are {slots_str}. Which time slot would you like, and could I please have your full name?",
                    "actions": actions_taken
                }
            elif not has_contact:
                return {
                    "reply": f"Available slots for {doc_name} {date_label} are {slots_str}. Which time slot would you like to book for {detected_name}, and what is your contact phone number?",
                    "actions": actions_taken
                }
            else:
                return {
                    "reply": f"Available slots for {doc_name} {date_label} are {slots_str}. Which time slot would you like me to reserve for {detected_name}?",
                    "actions": actions_taken
                }

        # If slot is present, ask for missing name/contact
        if not has_name and not has_contact:
            return {
                "reply": f"I've noted the {detected_slot} slot with {doc_name} {date_label}. To complete your booking, could you please provide your full name and a phone number or email?",
                "actions": actions_taken
            }
        elif not has_name:
            return {
                "reply": f"I have the {detected_slot} slot reserved with {doc_name} {date_label}. Could you please provide your full name?",
                "actions": actions_taken
            }
        elif not has_contact:
            return {
                "reply": f"Thank you, {detected_name}. Could you please share a callback phone number or email so I can finalize your reservation with {doc_name} at {detected_slot}?",
                "actions": actions_taken
            }

    # -------------------------------------------------------------------------
    # View Existing Appointments
    # -------------------------------------------------------------------------
    if any(w in text for w in ["appointment", "appointments", "booking", "bookings"]) and any(w in text for w in ["show", "view", "list", "check", "my", "upcoming", "status"]):
        db = await get_db()
        try:
            async with db.execute("SELECT visitor_name, staff_name, date, time_slot, status FROM appointments WHERE status != 'Cancelled' ORDER BY date ASC LIMIT 4") as cur:
                rows = await cur.fetchall()
            actions_taken.append({"tool": "list_appointments", "args": {}})
            if rows:
                appts_text = "; ".join([f"{r['visitor_name']} with {r['staff_name']} on {r['date']} at {r['time_slot']}" for r in rows])
                return {
                    "reply": f"Here are the active appointments: {appts_text}. You can also view all bookings in the Appointments tab.",
                    "actions": actions_taken
                }
            else:
                return {
                    "reply": "There are currently no active appointments scheduled. Would you like me to book one for you with one of our specialist doctors?",
                    "actions": actions_taken
                }
        finally:
            await db.close()

    # -------------------------------------------------------------------------
    # Cancel Appointment
    # -------------------------------------------------------------------------
    if any(w in text for w in ["cancel appointment", "cancel booking", "cancel my appointment"]):
        db = await get_db()
        try:
            async with db.execute("SELECT id, visitor_name, staff_name, date, time_slot FROM appointments WHERE status = 'Confirmed' ORDER BY id DESC LIMIT 1") as cur:
                row = await cur.fetchone()
            if row:
                await db.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (row['id'],))
                await db.commit()
                actions_taken.append({"tool": "cancel_appointment", "args": {"id": row['id']}})
                return {
                    "reply": f"The appointment for {row['visitor_name']} with {row['staff_name']} on {row['date']} at {row['time_slot']} has been successfully cancelled.",
                    "actions": actions_taken
                }
            else:
                return {
                    "reply": "I couldn't find an active confirmed appointment to cancel. You can view all bookings in the Appointments tab.",
                    "actions": []
                }
        finally:
            await db.close()

    # -------------------------------------------------------------------------
    # Corporate & Facility Info (Hours, Address, Parking, Wi-Fi, Cafeteria)
    # -------------------------------------------------------------------------
    if any(w in text for w in ["hour", "open", "close", "timing"]):
        res = await get_company_info(topic="hours")
        actions_taken.append({"tool": "get_company_info", "args": {"topic": "hours"}})
        return {
            "reply": f"Our corporate and medical offices are open Monday to Friday from 8:30 AM to 5:30 PM EST. We are closed on weekends. How else may I assist you?",
            "actions": actions_taken
        }

    if any(w in text for w in ["location", "address", "where", "direction", "directions", "parking", "garage"]):
        topic = "parking" if "parking" in text or "garage" in text else "location"
        res = await get_company_info(topic=topic)
        actions_taken.append({"tool": "get_company_info", "args": {"topic": topic}})
        details = res.get("results", [{}])[0].get("details", f"{config.COMPANY_NAME} is located at {config.COMPANY_LOCATION}.")
        return {
            "reply": f"{details} How may I assist you further?",
            "actions": actions_taken
        }

    if any(w in text for w in ["wifi", "wi-fi", "internet", "password", "network", "badge", "security"]):
        topic = "wifi" if any(k in text for k in ["wifi", "wi-fi", "internet", "password"]) else "visitor_policy"
        res = await get_company_info(topic=topic)
        actions_taken.append({"tool": "get_company_info", "args": {"topic": topic}})
        details = res.get("results", [{}])[0].get("details", "Guest Wi-Fi: 'HR-Guest', password: 'HRGuest2026!'.")
        return {
            "reply": details,
            "actions": actions_taken
        }

    # -------------------------------------------------------------------------
    # Corporate Staff Directory & Messages
    # -------------------------------------------------------------------------
    if any(w in text for w in ["message", "voicemail", "note"]):
        staff = "Arjun Mehta"
        for name in ["Dr. Ananya Sharma", "Rajesh Krishnamurthy", "Meera Iyer", "Vikram Desai", "Priya Nair", "Arjun Mehta", "Kavitha Sundaram"]:
            if name.lower() in text or name.split()[-1].lower() in text:
                staff = name
                break
        res = await leave_message(caller_name="Guest Caller", contact_info="caller@guest.com", recipient_name=staff, message=raw_query)
        actions_taken.append({"tool": "leave_message", "args": {"recipient": staff}})
        return {
            "reply": f"I have recorded your message for {staff}. They will be notified and will follow up with you as soon as possible.",
            "actions": actions_taken
        }

    if any(w in text for w in ["who is", "extension", "contact", "ceo", "director", "directory"]):
        res = await lookup_directory(query=raw_query)
        actions_taken.append({"tool": "lookup_directory", "args": {"query": raw_query}})
        staff_list = res.get("directory", [])
        if staff_list:
            p = staff_list[0]
            return {
                "reply": f"{p['name']} is our {p['title']} in {p['department']}. Their status is currently '{p.get('current_status', 'Available')}' at extension {p.get('extension', 'N/A')}. Would you like me to connect you or check their availability?",
                "actions": actions_taken
            }

    # -------------------------------------------------------------------------
    # Greetings, Identity & Etiquette
    # -------------------------------------------------------------------------
    if any(p in text for p in ["who are you", "what is your name", "what's your name", "who is jack", "tell me about yourself"]):
        return {
            "reply": f"Hello! My name is {config.RECEPTIONIST_NAME}, the AI Voice Receptionist for {config.COMPANY_NAME}. I assist patients with discovering specialist doctors, checking real appointment slots, and completing verified medical bookings, as well as office directions and corporate logistics. How may I assist you today?",
            "actions": []
        }

    if any(re.search(r'\b' + re.escape(w) + r'\b', text) for w in ["hello", "hi", "hey", "good morning", "good afternoon", "greetings"]):
        return {
            "reply": f"Good day! Welcome to {config.COMPANY_NAME}. My name is {config.RECEPTIONIST_NAME}. How may I assist you with your appointment or inquiry today?",
            "actions": []
        }

    if any(p in text for p in ["thank you", "thanks", "appreciate it"]):
        return {
            "reply": f"You're very welcome! It's always my pleasure to assist you at {config.COMPANY_NAME}. Please let me know if there's anything else you need.",
            "actions": []
        }

    if any(p in text for p in ["bye", "goodbye", "see you", "have a nice day"]):
        return {
            "reply": f"Thank you for contacting {config.COMPANY_NAME}. Have a wonderful day ahead, and please reach out anytime!",
            "actions": []
        }

    # Conversational Fallback
    return {
        "reply": f"Thank you for contacting {config.COMPANY_NAME}. I am Jack, your AI Voice Receptionist. I can help you search and book appointments with our 10 specialist doctors across Cardiology, Dermatology, Orthopedics, Pediatrics, Neurology, and more, or assist with office directions and messages. How may I assist you today?",
        "actions": []
    }

# Keep handle_demo_chat for backwards compatibility
handle_demo_chat = handle_conversational_chat

# 7. Text Chat & Fallback Endpoint
@router.post("/chat")
async def text_chat_endpoint(chat_req: TextChatRequest):
    active_key = (chat_req.api_key or config.GEMINI_API_KEY).strip()
    if not config.is_valid_gemini_key(active_key):
        # Fall back to built-in front-desk knowledge and conversational booking engine
        return await handle_conversational_chat(chat_req.message, chat_req.history)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=active_key)
        
        # Build prompt with reception context
        prompt_instruction = f"""You are {config.RECEPTIONIST_NAME}, the AI Executive Healthcare & Hospital Receptionist for {config.COMPANY_NAME}.
You represent a premier medical centre and hospital consultation clinic.
You are professional, articulate, empathetic, and highly efficient.
Today's date is {date.today().isoformat()}.

MANDATORY HEALTHCARE APPOINTMENT BOOKING PROTOCOL:
When a patient expresses an intent to book an appointment (e.g. "book an appointment with a cardiologist", "I need to see a doctor for skin rash"):
1. Search actual doctors from the database using `search_doctors(query=..., specialization=...)`.
2. Check real doctor availability using `check_availability(staff_or_department=doctor_name, date_str=...)`.
3. Present available doctors and appointment slots verbally (e.g. "We have Dr. Arun Prakash Sharma, our specialist in Cardiology at the Heart & Vascular Centre. Available slots for tomorrow are 10:00 AM, 11:00 AM, and 2:00 PM. What time works best for you?").
4. Collect all required patient information: patient's full name, contact phone/email, and preferred slot.
5. EXPLICIT CONFIRMATION (CRITICAL):
   Before booking, ALWAYS ask for explicit patient confirmation:
   "I have an appointment with [Doctor] on [Date] at [Time] for [Patient Name] (contact: [Contact]). Would you like me to confirm this booking for you?"
6. EXECUTE & VERIFY:
   ONLY after the patient explicitly confirms (e.g. "Yes", "Confirm", "Yes please", "Go ahead"), execute `book_appointment(...)`.
7. Verify that the appointment was successfully saved from the tool result, then speak the final confirmed booking ID and arrival instructions.
- NEVER claim an appointment is booked unless the database confirms successful booking.
- NEVER invent doctors, availability or appointment slots.
"""

        # Build contents list supporting conversation history
        contents: List[types.Content] = []
        if chat_req.history:
            for h in chat_req.history:
                role = "user" if h.get("role") in ("user", "human") else "model"
                text = h.get("text") or h.get("content") or ""
                if text:
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=chat_req.message)]))

        # Explicitly disable SDK automatic function calling to allow manual async await execution
        gen_config = types.GenerateContentConfig(
            system_instruction=prompt_instruction,
            tools=RECEPTIONIST_TOOL_FUNCTIONS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        actions_taken = []
        reply_text = ""
        max_tool_turns = 5

        for _ in range(max_tool_turns):
            response = await client.aio.models.generate_content(
                model=config.GEMINI_FALLBACK_MODEL,
                contents=contents,
                config=gen_config,
            )

            # If no function calls requested by model, we have the final textual response
            if not response.function_calls:
                reply_text = response.text or ""
                break

            # Append the model turn containing function calls to conversation history
            if response.candidates and response.candidates[0].content:
                contents.append(response.candidates[0].content)
            else:
                fc_parts = [
                    types.Part.from_function_call(name=fc.name, args=dict(fc.args) if fc.args else {})
                    for fc in response.function_calls
                ]
                contents.append(types.Content(role="model", parts=fc_parts))

            # Execute all tool calls asynchronously and gather responses
            tool_response_parts = []
            for fc in response.function_calls:
                fn_name = fc.name
                fn_args = dict(fc.args) if fc.args else {}
                actions_taken.append({"tool": fn_name, "args": fn_args})

                tool_result = {"error": f"Tool '{fn_name}' not recognized"}
                if fn_name in TOOL_REGISTRY:
                    tool_fn = TOOL_REGISTRY[fn_name]
                    try:
                        if inspect.iscoroutinefunction(tool_fn):
                            tool_result = await tool_fn(**fn_args)
                        elif callable(tool_fn):
                            res = tool_fn(**fn_args)
                            if inspect.iscoroutine(res):
                                tool_result = await res
                            else:
                                tool_result = res
                    except Exception as ex:
                        logger.error(f"Manual tool execution failed for {fn_name}: {ex}", exc_info=True)
                        tool_result = {"error": str(ex)}

                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": tool_result}
                    )
                )

            # Feed tool results back to AI assistant
            contents.append(types.Content(role="tool", parts=tool_response_parts))

        if not reply_text and response and response.text:
            reply_text = response.text

        return {
            "reply": reply_text or "Your request has been processed successfully.",
            "actions": actions_taken
        }
    except Exception as e:
        logger.error(f"Gemini API chat error: {e}", exc_info=True)
        # Graceful fallback to conversational chat engine if network/key issues occur
        try:
            return await handle_conversational_chat(chat_req.message, chat_req.history)
        except Exception as inner_ex:
            logger.error(f"Conversational fallback error: {inner_ex}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
