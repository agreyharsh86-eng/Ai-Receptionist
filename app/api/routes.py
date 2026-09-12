from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from app.database import get_db
import app.config as config
from app.tools.receptionist_tools import (
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

# 7. Text Chat & Fallback Endpoint
@router.post("/chat")
async def text_chat_endpoint(chat_req: TextChatRequest):
    active_key = (chat_req.api_key or config.GEMINI_API_KEY).strip()
    if not active_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is not configured. Please enter your API key in Settings or set GEMINI_API_KEY in .env."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=active_key)
        
        # Build prompt with reception context
        prompt_instruction = f"""You are {config.RECEPTIONIST_NAME}, the AI Executive Receptionist for {config.COMPANY_NAME}.
You represent a premier corporate front desk.
You are professional, articulate, warm, and highly efficient.
Today's date is {date.today().isoformat()}.

Your duties:
1. Greet guests and callers warmly.
2. Answer inquiries about the company, address ({config.COMPANY_LOCATION}), office hours ({config.COMPANY_HOURS}), visitor badges, and Wi-Fi using `get_company_info`.
3. Check staff availability using `check_availability` and book appointments using `book_appointment`.
4. If a requested staff member is unavailable, in a meeting, or out of office, offer to take a detailed message with `leave_message`.
5. Look up team members or departments using `lookup_directory`.
6. Transfer callers when appropriate using `transfer_call`.

Keep your answers conversational, concise, and polite as a front-desk professional would speak. Avoid lengthy monologues.
"""

        # We can call the model with tools enabled
        response = client.models.generate_content(
            model=config.GEMINI_FALLBACK_MODEL,
            contents=chat_req.message,
            config=types.GenerateContentConfig(
                system_instruction=prompt_instruction,
                tools=[
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