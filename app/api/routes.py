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
    TOOL_REGISTRY
)

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
        "has_api_key": bool(config.GEMINI_API_KEY),
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

async def handle_demo_chat(query: str) -> Dict[str, Any]:
    text = query.strip().lower()
    actions_taken = []

    # 1. Identity & Persona ("Who are you", "What is your name", "Who is Jack")
    if any(p in text for p in ["who are you", "what is your name", "what's your name", "who is jack", "tell me about yourself", "your name", "introduce yourself"]):
        return {
            "reply": f"Hello! My name is {config.RECEPTIONIST_NAME}, the AI Front Desk Concierge and Executive Receptionist for {config.COMPANY_NAME}. I am here to assist you with booking doctor consultations, checking executive staff schedules, guiding you around our corporate offices, answering company inquiries, or logging messages. How may I assist you today?",
            "actions": []
        }

    # 2. Capabilities & Help ("What can you do", "Help me", "How does this work")
    if any(p in text for p in ["what can you do", "help me", "how do you work", "how does this work", "what are your features", "what can i do", "what are my options"]):
        return {
            "reply": f"At {config.COMPANY_NAME}, I can help you with: 1) Searching and booking consultations with our 10 specialist doctors across Cardiology, Dermatology, Orthopedics, Pediatrics, Neurology, and more. 2) Checking staff availability and scheduling business meetings with our leadership team. 3) Providing office hours, guest Wi-Fi, visitor parking validation, and directions. 4) Leaving urgent messages and voicemails. How can I help you right now?",
            "actions": []
        }

    # 3. About Company ("What is HR Enterprises", "About the company", "What do you do", "Services")
    if any(p in text for p in ["what is hr enterprises", "about hr enterprises", "about the company", "what company is this", "tell me about hr enterprises", "what do you do", "what services", "what products", "company info"]):
        return {
            "reply": f"{config.COMPANY_NAME} provides enterprise cloud infrastructure, AI orchestration platforms, and high-performance business solutions for global organizations, alongside our dedicated Healthcare & Medical Consultation Centre featuring 10 top specialist doctors. Our corporate headquarters is located at {config.COMPANY_LOCATION}. How can I assist you further?",
            "actions": [{"tool": "get_company_info", "args": {"topic": "about"}}]
        }

    # 4. CEO & Executive Leadership Inquiries
    if any(p in text for p in ["who is the ceo", "who is the boss", "founder", "head of company", "president", "ananya sharma"]):
        return {
            "reply": f"Dr. Ananya Sharma is the Chief Executive Officer of {config.COMPANY_NAME}. She oversees strategic direction, investor relations, and enterprise partnerships. Would you like me to check her availability or leave a message for her office?",
            "actions": [{"tool": "lookup_directory", "args": {"query": "Ananya Sharma"}}]
        }

    # 5. Pleasantries & Conversational Etiquette
    if any(p in text for p in ["how are you", "how are you doing", "how's it going", "how do you do"]):
        return {
            "reply": f"I'm doing wonderful, thank you for asking! I'm ready to assist you with any questions, appointments, or medical consultations at {config.COMPANY_NAME}. What can I do for you?",
            "actions": []
        }

    if any(p in text for p in ["thank you", "thanks", "appreciate it", "thank u", "many thanks", "thanks a lot"]):
        return {
            "reply": f"You're very welcome! It's always my pleasure to assist you at {config.COMPANY_NAME}. Please let me know if there is anything else I can do for you.",
            "actions": []
        }

    if any(p in text for p in ["bye", "goodbye", "see you", "have a good day", "have a nice day", "good night", "take care"]):
        return {
            "reply": f"Thank you for contacting {config.COMPANY_NAME}. Have a wonderful day ahead, and please reach out anytime you need assistance!",
            "actions": []
        }

    if any(p in text for p in ["are you human", "are you an ai", "are you a bot", "are you real"]):
        return {
            "reply": f"I am {config.RECEPTIONIST_NAME}, an AI-powered conversational receptionist built for {config.COMPANY_NAME}. I understand voice commands, schedule appointments, and coordinate front-desk logistics in real time.",
            "actions": []
        }

    # 6. Basic Greetings (word boundaries)
    is_greeting = any(re.search(r'\b' + re.escape(w) + r'\b', text) for w in ["hello", "hi", "hey", "good morning", "good afternoon", "greetings"])
    has_specific_intent = any(w in text for w in ["doctor", "dr.", "dr ", "specialist", "appointment", "book", "available", "schedule", "hours", "parking", "where", "location", "wifi", "message", "directory", "fee", "pain", "fever", "sick"])
    if is_greeting and (len(text.split()) <= 3 or not has_specific_intent):
        return {
            "reply": f"Good day! Welcome to {config.COMPANY_NAME}. My name is {config.RECEPTIONIST_NAME}. How may I direct your call or assist you today?",
            "actions": []
        }

    # 7. Hours & Schedule
    if any(w in text for w in ["hour", "open", "close", "timing", "when are you open"]):
        res = await get_company_info(topic="hours")
        return {
            "reply": f"Our corporate office is open Monday to Friday from 8:30 AM to 5:30 PM EST. We are closed on weekends. How else may I assist you?",
            "actions": [{"tool": "get_company_info", "args": {"topic": "hours"}}]
        }

    def get_info_detail(info_res: Dict[str, Any], fallback: str = "") -> str:
        if isinstance(info_res, dict) and info_res.get("results") and len(info_res["results"]) > 0:
            return info_res["results"][0].get("details", fallback)
        return fallback

    # 8. Cafeteria, Dining & Amenities
    if any(w in text for w in ["cafeteria", "canteen", "coffee", "cafe", "bistro", "food", "lunch", "breakfast", "eat", "dining", "tea"]):
        res = await get_company_info(topic="amenities")
        detail = get_info_detail(res, "The 4th Floor Sky Lounge Bistro offers artisan coffee, breakfast, and lunch from 7:30 AM to 3:00 PM.")
        return {
            "reply": f"{detail} It is open to all visitors and staff.",
            "actions": [{"tool": "get_company_info", "args": {"topic": "amenities"}}]
        }

    # 9. Location, Address, Parking & Transit
    if any(w in text for w in ["location", "address", "where", "direction", "directions", "parking", "garage", "subway", "metro", "transit"]):
        topic = "parking" if "parking" in text or "garage" in text else "location"
        res = await get_company_info(topic=topic)
        detail = get_info_detail(res, f"{config.COMPANY_NAME} is located at {config.COMPANY_LOCATION}.")
        return {
            "reply": f"{detail} How may I help you further?",
            "actions": [{"tool": "get_company_info", "args": {"topic": topic}}]
        }

    # 10. Wi-Fi & Guest Badges / Security
    if any(w in text for w in ["wifi", "wi-fi", "internet", "password", "network", "badge", "security", "pass", "id required"]):
        topic = "wifi" if any(k in text for k in ["wifi", "wi-fi", "internet", "password", "network"]) else "visitor_policy"
        res = await get_company_info(topic=topic)
        detail = get_info_detail(res, "High-speed guest Wi-Fi is available across all floors. Network name: 'HR-Guest'. Password: 'HRGuest2026!'.")
        return {
            "reply": detail,
            "actions": [{"tool": "get_company_info", "args": {"topic": topic}}]
        }

    # 11. Courier, Deliveries & Packages
    if any(w in text for w in ["courier", "delivery", "deliveries", "package", "mail", "fedex", "ups", "dhl", "dropoff"]):
        res = await get_company_info(topic="deliveries")
        detail = get_info_detail(res, "Deliveries should be directed to the Central Loading Dock on B1 between 8:00 AM and 4:30 PM.")
        return {
            "reply": detail,
            "actions": [{"tool": "get_company_info", "args": {"topic": "deliveries"}}]
        }

    # 12. View / Check Existing Appointments
    is_view_appointments = (
        any(w in text for w in ["appointment", "appointments", "booking", "bookings"]) and
        any(w in text for w in ["show", "view", "list", "check", "see", "status", "all", "upcoming", "scheduled", "my", "any", "what are"]) and
        not any(w in text for w in ["cancel", "book", "reserve"])
    )
    if is_view_appointments:
        db = await get_db()
        try:
            async with db.execute("SELECT visitor_name, staff_name, date, time_slot, status FROM appointments WHERE status != 'Cancelled' ORDER BY date ASC LIMIT 4") as cur:
                rows = await cur.fetchall()
            if rows:
                appts_text = "; ".join([f"{r['visitor_name']} with {r['staff_name']} on {r['date']} at {r['time_slot']}" for r in rows])
                return {
                    "reply": f"Here are the scheduled appointments: {appts_text}. You can view and manage all bookings in the Appointments tab on the right.",
                    "actions": [{"tool": "list_appointments", "args": {}}]
                }
            else:
                return {
                    "reply": "There are currently no active appointments scheduled. Would you like me to book one for you?",
                    "actions": []
                }
        finally:
            await db.close()

    # 13. Cancel Appointment
    if any(w in text for w in ["cancel appointment", "cancel booking", "cancel my", "cancel an appointment"]):
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

    # 14. Doctor Lookup, Symptom Guidance & Appointment Booking (Prioritized)
    all_doctors = [
        ("Dr. Arun Prakash Sharma", ["arun", "sharma", "cardiologist", "cardiology", "heart", "chest pain", "bp", "blood pressure", "cholesterol"]),
        ("Dr. Priyanka Venkatesh", ["priyanka", "venkatesh", "dermatologist", "dermatology", "skin", "acne", "rash", "pimples", "hair fall", "hair loss"]),
        ("Dr. Rajiv Malhotra", ["rajiv", "malhotra", "orthopedic", "orthopedics", "bone", "joint", "knee", "knee pain", "back pain", "fracture"]),
        ("Dr. Kavitha Raghunathan", ["kavitha", "raghunathan", "pediatric", "pediatrician", "pediatrics", "child", "children", "baby", "infant", "vaccination"]),
        ("Dr. Siddharth Joshi", ["siddharth", "joshi", "neurologist", "neurology", "brain", "spine", "headache", "migraine", "seizure", "paralysis"]),
        ("Dr. Meenakshi Sundaram", ["meenakshi", "sundaram", "gynecologist", "gynecology", "women", "obstetrics", "pregnancy", "period", "periods"]),
        ("Dr. Harsh Vardhan Patel", ["harsh", "patel", "gastro", "gastroenterologist", "gastroenterology", "stomach", "liver", "acidity", "indigestion", "gas"]),
        ("Dr. Anjali Krishnamurthy", ["anjali", "krishnamurthy", "ophthalmologist", "ophthalmology", "eye", "eyes", "vision", "glasses", "cataract", "lasik"]),
        ("Dr. Nikhil Banerjee", ["nikhil", "banerjee", "psychiatrist", "psychiatry", "mental", "wellness", "therapy", "depression", "anxiety", "stress", "sleep"]),
        ("Dr. Lakshmi Narayanan Iyer", ["lakshmi", "iyer", "general physician", "physician", "general medicine", "fever", "checkup", "cold", "cough", "diabetes", "sugar", "sick", "weak", "tooth", "toothache", "teeth", "gum", "gums", "dentist", "dental", "throat", "pain"])
    ]

    doctor_keywords = [
        "doctor", "doctors", "dr.", "dr ", "specialist", "physician", "cardiologist", "dermatologist",
        "orthopedic", "pediatric", "pediatrician", "neurologist", "gynecologist", "gastro",
        "gastroenterologist", "ophthalmologist", "psychiatrist", "general physician",
        "consult", "consultation", "patient", "clinic", "hospital", "treatment",
        "headache", "fever", "chest pain", "back pain", "knee pain", "cough", "cold", "stomach", "acne", "rash", "migraine",
        "tooth", "toothache", "teeth", "gum", "gums", "throat"
    ]

    is_list_doctors = (
        any(p in text for p in ["which doctors", "who are the doctors", "list doctors", "all doctors", "available doctors", "what doctors", "show doctors", "view doctors", "names of doctors"]) or
        ("doctor" in text and "available" in text and not any(w in text for w in ["book", "reserve"]))
    )

    if is_list_doctors:
        return {
            "reply": f"At {config.COMPANY_NAME}, we have 10 top specialist doctors available:\n• Dr. Arun Prakash Sharma (Cardiologist)\n• Dr. Priyanka Venkatesh (Dermatologist)\n• Dr. Rajiv Malhotra (Orthopedic Surgeon)\n• Dr. Kavitha Raghunathan (Pediatrician)\n• Dr. Siddharth Joshi (Neurologist)\n• Dr. Meenakshi Sundaram (Gynecologist)\n• Dr. Harsh Vardhan Patel (Gastroenterologist)\n• Dr. Anjali Krishnamurthy (Ophthalmologist)\n• Dr. Nikhil Banerjee (Psychiatrist)\n• Dr. Lakshmi Narayanan Iyer (General Physician)\n\nYou can browse full profiles in the Doctors tab. Which specialist would you like to consult?",
            "actions": [{"tool": "search_doctors", "args": {"query": "all"}}]
        }

    # First extract patient name if present (e.g. "for Rahul Verma" or "for Vikram Sharma")
    patient_name = "Guest Patient"
    name_match = re.search(r'(?:for|patient|name is)\s+([A-Za-z\s]+?)(?:\s+tomorrow|\s+today|\s+at|\s+on|\s*$)', query, re.IGNORECASE)
    if name_match:
        extracted = name_match.group(1).strip()
        if extracted.lower() not in ["an appointment", "appointment", "doctor", "consultation", "me", "him", "her"]:
            patient_name = extracted.title()

    searchable_text = text
    if patient_name.lower() in searchable_text:
        searchable_text = searchable_text.replace(patient_name.lower(), "")

    matched_doc = None
    # 1. Exact full doctor name
    for doc_name, keywords in all_doctors:
        if doc_name.lower() in searchable_text:
            matched_doc = doc_name
            break

    # 2. Check doctor's specific first/last name
    if not matched_doc:
        for doc_name, keywords in all_doctors:
            for kw in keywords[:2]:
                if re.search(r'\b' + re.escape(kw) + r'\b', searchable_text):
                    matched_doc = doc_name
                    break
            if matched_doc:
                break

    # 3. Check medical symptoms / specialization
    if not matched_doc:
        for doc_name, keywords in all_doctors:
            for kw in keywords[2:]:
                if re.search(r'\b' + re.escape(kw) + r'\b', searchable_text):
                    matched_doc = doc_name
                    break
            if matched_doc:
                break

    is_booking = (
        any(w in text for w in ["book", "reserve"]) or
        any(p in text for p in ["take an appointment", "make an appointment", "schedule an appointment", "fix an appointment"])
    )

    is_doctor_query = matched_doc is not None or any(w in text for w in doctor_keywords)

    if is_doctor_query:
        # Check if user wants to book an appointment with a doctor
        if is_booking:
            target_doctor = matched_doc or "Dr. Arun Prakash Sharma"

            appt_date = date.today().isoformat()
            if "tomorrow" in text:
                appt_date = (date.today() + timedelta(days=1)).isoformat()
            else:
                date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
                if date_match:
                    appt_date = date_match.group(1)

            slot = "10:00 AM"
            for s in ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "01:00 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM"]:
                if s.lower() in text:
                    slot = s
                    break
            else:
                t_match = re.search(r'\b(0?[1-9]|1[0-2])(?::([0-5][0-9]))?\s*(am|pm)\b', text)
                if t_match:
                    hr = int(t_match.group(1))
                    mn = t_match.group(2) or "00"
                    period = t_match.group(3).upper()
                    slot = f"{hr:02d}:{mn} {period}"

            res = await book_appointment(
                visitor_name=patient_name,
                contact_info="patient@health.in",
                staff_or_department=target_doctor,
                date_str=appt_date,
                time_slot=slot,
                purpose=f"Medical consultation with {target_doctor}"
            )
            actions_taken.append({"tool": "book_appointment", "args": {"patient": patient_name, "doctor": target_doctor, "date": appt_date, "slot": slot}})

            if res.get("status") == "confirmed":
                date_display = "tomorrow" if appt_date == (date.today() + timedelta(days=1)).isoformat() else f"on {appt_date}"
                return {
                    "reply": f"Your appointment for {patient_name} with {target_doctor} has been confirmed {date_display} at {slot}. Please arrive 10 minutes early at reception with ID. You can view this booking anytime in the Appointments tab.",
                    "actions": actions_taken
                }
            else:
                return {
                    "reply": f"I apologize, but {target_doctor} already has an appointment booked at {slot} on {appt_date}. Would you like me to check other available slots or suggest another specialist?",
                    "actions": actions_taken
                }

        # Query doctors information / Symptom guidance
        db = await get_db()
        try:
            if matched_doc:
                async with db.execute(
                    "SELECT * FROM doctors WHERE name = ? OR name LIKE ?",
                    (matched_doc, f"%{matched_doc.split()[-1]}%")
                ) as cur:
                    rows = await cur.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM doctors WHERE name LIKE ? OR specialization LIKE ? OR department LIKE ? OR bio LIKE ? ORDER BY rating DESC LIMIT 3",
                    (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
                ) as cur:
                    rows = await cur.fetchall()

            doctors_found = [dict(r) for r in rows]
            actions_taken.append({"tool": "search_doctors", "args": {"query": query}})

            if doctors_found:
                doc = doctors_found[0]
                others = ""
                if len(doctors_found) > 1:
                    other_names = ", ".join([d["name"] for d in doctors_found[1:3]])
                    others = f" We also have {other_names} available in our Medical Centre."

                return {
                    "reply": f"I found {doc['name']}, specialist in {doc['specialization']} ({doc['department']}). {doc['qualification']} with {doc['experience_years']} years experience, rated {doc['rating']}/5 ⭐ ({doc['total_reviews']} reviews). Consultation fee is {doc['consultation_fee']}, available {doc['available_days']}. Status: {doc['status']}.{others} Would you like me to book an appointment with {doc['name']} for you?",
                    "actions": actions_taken
                }
            else:
                return {
                    "reply": f"At {config.COMPANY_NAME}, we have 10 top specialist doctors available across Cardiology, Dermatology, Orthopedics, Pediatrics, Neurology, Gynecology, Gastroenterology, Ophthalmology, Psychiatry, and General Medicine. You can browse all doctor profiles in the Doctors tab. Which specialist would you like to consult?",
                    "actions": actions_taken
                }
        finally:
            await db.close()

    # 15. Corporate Staff Availability Check
    if any(w in text for w in ["available", "availability", "free", "slot"]):
        staff = "Rajesh Krishnamurthy"
        for name in ["Dr. Ananya Sharma", "Rajesh Krishnamurthy", "Meera Iyer", "Vikram Desai", "Priya Nair", "Arjun Mehta", "Kavitha Sundaram", "Rohit Agarwal"]:
            if name.lower() in text or name.split()[-1].lower() in text:
                staff = name
                break
        today_str = date.today().isoformat()
        res = await check_availability(staff_or_department=staff, date_str=today_str)
        actions_taken.append({"tool": "check_availability", "args": {"staff_or_department": staff, "date_str": today_str}})
        slots = res.get("available_slots", [])[:4]
        if slots:
            slots_str = ", ".join(slots)
            return {
                "reply": f"{staff} has open time slots today at: {slots_str}. Would you like me to book one of these for you?",
                "actions": actions_taken
            }
        else:
            return {
                "reply": f"{staff} has no available slots remaining today. Would you like to leave a message for them?",
                "actions": actions_taken
            }

    # 16. Corporate Staff Book appointment
    if any(w in text for w in ["book", "reserve", "schedule"]):
        staff = "Rajesh Krishnamurthy"
        for name in ["Dr. Ananya Sharma", "Rajesh Krishnamurthy", "Meera Iyer", "Vikram Desai", "Priya Nair", "Arjun Mehta", "Kavitha Sundaram", "Rohit Agarwal"]:
            if name.lower() in text or name.split()[-1].lower() in text:
                staff = name
                break
        today_str = date.today().isoformat()
        slot = "02:00 PM"
        for s in ["09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM"]:
            if s.lower() in text or s.split()[0].lower() in text:
                slot = s
                break
        res = await book_appointment(
            visitor_name="Guest Caller",
            contact_info="caller@guest.com",
            staff_or_department=staff,
            date_str=today_str,
            time_slot=slot,
            purpose="Front Desk Consultation"
        )
        actions_taken.append({"tool": "book_appointment", "args": {"staff": staff, "slot": slot}})
        return {
            "reply": f"I have booked an appointment with {staff} for you today at {slot}. Your confirmation has been recorded in the Appointments tab.",
            "actions": actions_taken
        }

    # 17. Leave message
    if any(w in text for w in ["message", "voicemail", "note"]):
        staff = "Arjun Mehta"
        for name in ["Dr. Ananya Sharma", "Rajesh Krishnamurthy", "Meera Iyer", "Vikram Desai", "Priya Nair", "Arjun Mehta", "Kavitha Sundaram", "Rohit Agarwal"]:
            if name.lower() in text or name.split()[-1].lower() in text:
                staff = name
                break
        res = await leave_message(
            caller_name="Guest Caller",
            contact_info="caller@guest.com",
            recipient_name=staff,
            message=query,
            urgency="Normal"
        )
        actions_taken.append({"tool": "leave_message", "args": {"recipient": staff}})
        return {
            "reply": f"I have recorded your message for {staff}. They will be notified and will follow up with you as soon as possible.",
            "actions": actions_taken
        }

    # 18. Staff directory lookup
    if any(w in text for w in ["directory", "who is", "extension", "contact", "ceo", "engineer", "sales", "hr", "finance", "support", "product", "it"]):
        res = await lookup_directory(query=query)
        actions_taken.append({"tool": "lookup_directory", "args": {"query": query}})
        staff_list = res.get("staff", []) if isinstance(res.get("staff"), list) else res.get("directory", [])
        if staff_list:
            p = staff_list[0]
            return {
                "reply": f"{p['name']} is our {p['title']} in {p['department']}. Their status is currently '{p.get('current_status', p.get('status', 'Unknown'))}' at extension {p.get('extension', p.get('phone_extension', 'N/A'))}. Would you like me to connect you or check their availability?",
                "actions": actions_taken
            }

    # 19. Semantic Database Search Fallback
    db = await get_db()
    try:
        # Check company info
        async with db.execute("SELECT title, content FROM company_info WHERE title LIKE ? OR content LIKE ?", (f"%{query}%", f"%{query}%")) as cur:
            ci = await cur.fetchone()
        if ci:
            return {
                "reply": f"{ci['content']}. Is there anything else I can help you with at {config.COMPANY_NAME}?",
                "actions": [{"tool": "get_company_info", "args": {"query": query}}]
            }

        # Check staff directory
        async with db.execute("SELECT name, title, department, status, bio FROM staff_directory WHERE name LIKE ? OR department LIKE ? OR bio LIKE ?", (f"%{query}%", f"%{query}%", f"%{query}%")) as cur:
            st = await cur.fetchone()
        if st:
            return {
                "reply": f"{st['name']} is our {st['title']} in {st['department']}. Status: {st['status']}. {st['bio']}",
                "actions": [{"tool": "lookup_directory", "args": {"query": query}}]
            }
    finally:
        await db.close()

    # Intelligent Conversational Fallback
    return {
        "reply": f"Thank you for contacting {config.COMPANY_NAME}. I am Jack, your front desk concierge. I can help you book appointments with our 10 specialist doctors across all departments, schedule meetings with our corporate team, check office directions and hours, or take a detailed message. How may I best assist you?",
        "actions": []
    }

# 7. Text Chat & Fallback Endpoint
@router.post("/chat")
async def text_chat_endpoint(chat_req: TextChatRequest):
    active_key = (chat_req.api_key or config.GEMINI_API_KEY).strip()
    if not active_key:
        # Fall back to built-in front-desk knowledge engine instead of failing
        return await handle_demo_chat(chat_req.message)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=active_key)
        
        # Build prompt with reception context
        prompt_instruction = f"""You are {config.RECEPTIONIST_NAME}, the AI Executive Receptionist for {config.COMPANY_NAME}.
You represent a premier corporate front desk and medical consultation centre.
You are professional, articulate, warm, and highly efficient.
Today's date is {date.today().isoformat()}.

Your duties:
1. Greet guests and callers warmly.
2. Answer inquiries about the company, address ({config.COMPANY_LOCATION}), office hours ({config.COMPANY_HOURS}), visitor badges, and Wi-Fi using `get_company_info`.
3. Check doctor and staff availability using `check_availability` and book appointments using `book_appointment`.
4. Search for doctors, medical specialists, and departments using `search_doctors`.
5. If a requested staff member is unavailable, in a meeting, or out of office, offer to take a detailed message with `leave_message`.
6. Look up team members or departments using `lookup_directory`.
7. Transfer callers when appropriate using `transfer_call`.

Keep your answers conversational, concise, and polite as a front-desk professional would speak. Avoid lengthy monologues. Mention that callers can view all appointments and available doctors in the Appointments and Doctors tabs on the dashboard.
"""

        # We can call the model with tools enabled
        response = client.models.generate_content(
            model=config.GEMINI_FALLBACK_MODEL,
            contents=chat_req.message,
            config=types.GenerateContentConfig(
                system_instruction=prompt_instruction,
                tools=[
                    search_doctors,
                    check_availability,
                    book_appointment,
                    cancel_appointment,
                    leave_message,
                    lookup_directory,
                    get_company_info,
                    transfer_call
                ]
            )
        )

        actions_taken = []
        reply_text = ""

        # Handle function calls if any
        if response.function_calls:
            for fc in response.function_calls:
                fn_name = fc.name
                fn_args = fc.args
                actions_taken.append({"tool": fn_name, "args": fn_args})
                
                # Execute tool
                if fn_name in TOOL_REGISTRY:
                    tool_fn = TOOL_REGISTRY[fn_name]
                    tool_result = await tool_fn(**(fn_args or {}))
                    
                    # Generate follow-up answer
                    follow_up = client.models.generate_content(
                        model=config.GEMINI_FALLBACK_MODEL,
                        contents=[
                            types.Content(role="user", parts=[types.Part.from_text(text=chat_req.message)]),
                            types.Content(role="model", parts=[types.Part.from_function_call(name=fn_name, args=fn_args or {})]),
                            types.Content(role="user", parts=[types.Part.from_function_response(name=fn_name, response={"result": tool_result})])
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=prompt_instruction
                        )
                    )
                    reply_text = follow_up.text or ""
        else:
            reply_text = response.text or ""

        return {
            "reply": reply_text,
            "actions": actions_taken
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))