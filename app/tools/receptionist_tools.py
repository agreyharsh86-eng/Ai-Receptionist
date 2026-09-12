"""Receptionist Tools for Gemini Live and Text Models.

These tools are callable directly by Gemini to interact with the corporate
database: checking availability, booking appointments, taking caller messages,
looking up the staff directory, providing company information, and routing calls.
"""

import json
from datetime import datetime, date
from typing import Dict, Any, List
from app.database import get_db

ALL_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "01:00 PM", "01:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM"
]

async def check_availability(staff_or_department: str, date_str: str) -> Dict[str, Any]:
    """Check open appointment time slots for a staff member or department on a specific date.

    Args:
        staff_or_department: Name of the employee (e.g. 'Marcus Sterling') or department ('Enterprise Sales').
        date_str: The requested date in YYYY-MM-DD format (e.g. '2026-09-15').
    """
    db = await get_db()
    try:
        # Search staff first
        async with db.execute(
            "SELECT name, department, status FROM staff_directory WHERE name LIKE ? OR department LIKE ?",
            (f"%{staff_or_department}%", f"%{staff_or_department}%")
        ) as cursor:
            staff_rows = await cursor.fetchall()

        if not staff_rows:
            return {
                "status": "not_found",
                "message": f"No staff member or department matching '{staff_or_department}' was found.",
                "available_slots": []
            }

        matched_name = staff_rows[0]["name"]
        matched_dept = staff_rows[0]["department"]
        staff_status = staff_rows[0]["status"]

        # Check existing appointments on this date
        async with db.execute(
            """SELECT time_slot FROM appointments
               WHERE (staff_name = ? OR department = ?) AND date = ? AND status != 'Cancelled'""",
            (matched_name, matched_dept, date_str)
        ) as cursor:
            booked_rows = await cursor.fetchall()
            booked_slots = {row["time_slot"] for row in booked_rows}

        available = [slot for slot in ALL_SLOTS if slot not in booked_slots]

        return {
            "status": "success",
            "staff_name": matched_name,
            "department": matched_dept,
            "current_status": staff_status,
            "date": date_str,
            "available_slots": available[:6],  # Suggest up to 6 convenient slots
            "total_open_slots": len(available)
        }
    finally:
        await db.close()

async def book_appointment(
    visitor_name: str,
    contact_info: str,
    staff_or_department: str,
    date_str: str,
    time_slot: str,
    purpose: str = "General Business Consultation"
) -> Dict[str, Any]:
    """Book and confirm an appointment with a staff member or department.

    Args:
        visitor_name: Full name of the visitor or caller.
        contact_info: Phone number or email address of the visitor.
        staff_or_department: Name of the staff member or department.
        date_str: Date of appointment in YYYY-MM-DD format.
        time_slot: Time slot (e.g. '02:00 PM', '10:30 AM').
        purpose: Reason for the visit or meeting.
    """
    db = await get_db()
    try:
        # Identify staff
        async with db.execute(
            "SELECT name, department FROM staff_directory WHERE name LIKE ? OR department LIKE ?",
            (f"%{staff_or_department}%", f"%{staff_or_department}%")
        ) as cursor:
            staff = await cursor.fetchone()

        staff_name = staff["name"] if staff else staff_or_department
        dept_name = staff["department"] if staff else "General"

        # Check for conflicts
        async with db.execute(
            """SELECT id FROM appointments
               WHERE staff_name = ? AND date = ? AND time_slot = ? AND status != 'Cancelled'""",
            (staff_name, date_str, time_slot)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return {
                    "status": "conflict",
                    "message": f"Sorry, {staff_name} already has an appointment booked at {time_slot} on {date_str}."
                }

        # Insert booking
        now_str = datetime.now().isoformat()
        async with db.execute(
            """INSERT INTO appointments
               (visitor_name, contact_info, staff_name, department, date, time_slot, purpose, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?)""",
            (visitor_name, contact_info, staff_name, dept_name, date_str, time_slot, purpose, now_str)
        ) as cursor:
            booking_id = cursor.lastrowid
            await db.commit()

        return {
            "status": "confirmed",
            "booking_id": booking_id,
            "visitor_name": visitor_name,
            "staff_name": staff_name,
            "department": dept_name,
            "date": date_str,
            "time_slot": time_slot,
            "purpose": purpose,
            "instructions": "Please arrive 10 minutes early with a government-issued photo ID for security check-in."
        }
    finally:
        await db.close()

async def cancel_appointment(visitor_name: str, date_str: str) -> Dict[str, Any]:
    """Cancel an upcoming appointment for a visitor on a given date.

    Args:
        visitor_name: Name of the visitor.
        date_str: Date of the scheduled appointment in YYYY-MM-DD format.
    """
    db = await get_db()
    try:
        async with db.execute(
            """SELECT id, staff_name, time_slot FROM appointments
               WHERE visitor_name LIKE ? AND date = ? AND status != 'Cancelled'""",
            (f"%{visitor_name}%", date_str)
        ) as cursor:
            appointment = await cursor.fetchone()

        if not appointment:
            return {
                "status": "not_found",
                "message": f"No active appointment found for {visitor_name} on {date_str}."
            }

        await db.execute(
            "UPDATE appointments SET status = 'Cancelled' WHERE id = ?",
            (appointment["id"],)
        )
        await db.commit()

        return {
            "status": "cancelled",
            "appointment_id": appointment["id"],
            "message": f"Appointment with {appointment['staff_name']} on {date_str} at {appointment['time_slot']} has been successfully cancelled."
        }
    finally:
        await db.close()

async def leave_message(
    caller_name: str,
    contact_info: str,
    recipient_name: str,
    message: str,
    urgency: str = "Normal"
) -> Dict[str, Any]:
    """Record a caller message or voicemail for a staff member who is away or busy.

    Args:
        caller_name: Full name of the caller.
        contact_info: Callback phone number or email address.
        recipient_name: Name of the staff member or department the message is for.
        message: The detailed content of the message or inquiry.
        urgency: Level of urgency ('Normal', 'Urgent', or 'Low').
    """
    db = await get_db()
    try:
        # Match recipient in staff directory
        async with db.execute(
            "SELECT name, title, email, phone_extension FROM staff_directory WHERE name LIKE ? OR department LIKE ?",
            (f"%{recipient_name}%", f"%{recipient_name}%")
        ) as cursor:
            staff = await cursor.fetchone()

        target_name = staff["name"] if staff else recipient_name
        now_str = datetime.now().isoformat()

        async with db.execute(
            """INSERT INTO caller_messages
               (caller_name, contact_info, recipient_name, message, urgency, is_read, created_at)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (caller_name, contact_info, target_name, message, urgency, now_str)
        ) as cursor:
            msg_id = cursor.lastrowid
            await db.commit()

        return {
            "status": "message_logged",
            "message_id": msg_id,
            "recipient": target_name,
            "caller": caller_name,
            "urgency": urgency,
            "confirmation": f"Message recorded for {target_name}. A notification has been routed to their inbox."
        }
    finally:
        await db.close()

async def lookup_directory(query: str) -> Dict[str, Any]:
    """Search the staff directory for employees, titles, departments, extensions, or availability status.

    Args:
        query: Name, title, department, or skill to search for (e.g. 'Engineering', 'Marcus', 'Billing', 'CEO').
    """
    db = await get_db()
    try:
        async with db.execute(
            """SELECT id, name, title, department, email, phone_extension, status, bio
               FROM staff_directory
               WHERE name LIKE ? OR title LIKE ? OR department LIKE ? OR bio LIKE ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
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
            "query": query,
            "total_matches": len(results),
            "directory": results
        }
    finally:
        await db.close()

async def get_company_info(topic: str = "general") -> Dict[str, Any]:
    """Retrieve corporate information regarding office hours, building address, parking, directions, guest Wi-Fi, deliveries, or visitor security policy.

    Args:
        topic: Topic to look up: 'hours', 'location', 'parking', 'wifi', 'visitor_policy', 'deliveries', 'amenities', or 'about'.
    """
    db = await get_db()
    try:
        topic_clean = topic.lower().strip()
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

async def transfer_call(recipient_or_department: str) -> Dict[str, Any]:
    """Simulate initiating a direct phone call transfer to an extension or department.

    Args:
        recipient_or_department: Target employee name, extension number, or department.
    """
    db = await get_db()
    try:
        async with db.execute(
            """SELECT name, title, department, phone_extension, status FROM staff_directory
               WHERE name LIKE ? OR department LIKE ? OR phone_extension = ?""",
            (f"%{recipient_or_department}%", f"%{recipient_or_department}%", recipient_or_department)
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
                "transfer_to": recipient_or_department,
                "department": "Operator Queue",
                "extension": "0",
                "recipient_status": "Available",
                "message": f"Transferring your call to {recipient_or_department}. Please hold."
            }
    finally:
        await db.close()

# Tool registry for dynamic execution
TOOL_REGISTRY = {
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
    check_availability,
    book_appointment,
    cancel_appointment,
    leave_message,
    lookup_directory,
    get_company_info,
    transfer_call
]
