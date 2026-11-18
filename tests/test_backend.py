"""Unit and Integration Tests for AI Receptionist Backend & Healthcare Platform."""

import asyncio
import unittest
import os
import aiosqlite
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import date, timedelta
from google.genai import types

from app.main import app
from app.database import init_db, get_db
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

class TestReceptionistBackend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Run async init_db
        asyncio.run(init_db())
        cls.client = TestClient(app)

    def test_01_company_info(self):
        res = self.client.get("/api/company")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("name", data)
        self.assertIn("knowledge_base", data)
        self.assertTrue(len(data["knowledge_base"]) > 0)

    def test_02_staff_directory(self):
        res = self.client.get("/api/directory")
        self.assertEqual(res.status_code, 200)
        staff = res.json()
        self.assertTrue(len(staff) >= 5)

        # Search query matching seeded staff
        res_search = self.client.get("/api/directory?q=Rajesh")
        self.assertEqual(res_search.status_code, 200)
        found = res_search.json()
        self.assertTrue(any("Rajesh" in s["name"] for s in found))

    def test_03_lookup_directory_tool(self):
        async def run_tool():
            return await lookup_directory("Sales")
        result = asyncio.run(run_tool())
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["total_matches"] > 0)

    def test_04_check_availability_tool(self):
        async def run_tool():
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            return await check_availability("Rajesh Krishnamurthy", tomorrow)
        result = asyncio.run(run_tool())
        self.assertEqual(result["status"], "success")
        self.assertTrue(len(result["available_slots"]) > 0)

    def test_05_book_and_cancel_appointment(self):
        async def run_booking():
            target_date = (date.today() + timedelta(days=5)).isoformat()
            # Book
            book_res = await book_appointment(
                visitor_name="Alexander Hamilton",
                contact_info="alex@treasury.gov",
                staff_or_department="Rajesh Krishnamurthy",
                date_str=target_date,
                time_slot="02:00 PM",
                purpose="Annual Enterprise Software Contract Review"
            )
            # Cancel
            cancel_res = await cancel_appointment("Alexander Hamilton", target_date)
            return book_res, cancel_res

        book_res, cancel_res = asyncio.run(run_booking())
        self.assertEqual(book_res["status"], "confirmed")
        self.assertEqual(cancel_res["status"], "cancelled")

    def test_06_leave_message_tool(self):
        async def run_tool():
            return await leave_message(
                caller_name="Clara Oswald",
                contact_info="clara@tardis.co.uk",
                recipient_name="Priya Nair",
                message="Please call back regarding cloud infrastructure migration schedule.",
                urgency="Urgent"
            )
        result = asyncio.run(run_tool())
        self.assertEqual(result["status"], "message_logged")

        # Verify through REST API
        res = self.client.get("/api/messages")
        self.assertEqual(res.status_code, 200)
        msgs = res.json()
        self.assertTrue(any(m["caller_name"] == "Clara Oswald" for m in msgs))

    def test_07_company_info_tool(self):
        async def run_tool():
            return await get_company_info("parking")
        result = asyncio.run(run_tool())
        self.assertEqual(result["status"], "success")
        self.assertTrue(len(result["results"]) > 0)

    def test_08_transfer_call_tool(self):
        async def run_tool():
            return await transfer_call("Kavitha Sundaram")
        result = asyncio.run(run_tool())
        self.assertEqual(result["status"], "transfer_initiated")
        self.assertEqual(result["extension"], "601")

    def test_09_search_doctors_tool(self):
        async def run_doctor_searches():
            # Search by name
            res_name = await search_doctors(query="Dr. Arun")
            # Search by specialization
            res_spec = await search_doctors(specialization="Dermatology")
            # Search by symptom
            res_symptom = await search_doctors(query="chest pain")
            # Search all
            res_all = await search_doctors(query="all")
            return res_name, res_spec, res_symptom, res_all

        res_name, res_spec, res_symptom, res_all = asyncio.run(run_doctor_searches())
        self.assertEqual(res_name["status"], "success")
        self.assertTrue(res_name["count"] >= 1)
        self.assertTrue(any("Arun" in d["name"] for d in res_name["doctors"]))

        self.assertEqual(res_spec["status"], "success")
        self.assertTrue(res_spec["count"] >= 1)
        self.assertTrue(any(d["specialization"] == "Dermatology" for d in res_spec["doctors"]))

        self.assertEqual(res_symptom["status"], "success")
        self.assertTrue(res_symptom["count"] >= 1)

        self.assertEqual(res_all["status"], "success")
        self.assertEqual(res_all["count"], 10)

    def test_10_doctor_appointment_booking_flow(self):
        async def run_flow():
            target_date = (date.today() + timedelta(days=3)).isoformat()
            # 1. Search for doctor
            doc_res = await search_doctors(query="Cardiology")
            doctor_name = doc_res["doctors"][0]["name"]

            # 2. Check doctor availability
            avail_res = await check_availability(doctor_name, target_date)

            # 3. Book consultation
            chosen_slot = avail_res["available_slots"][0] if avail_res["available_slots"] else "10:00 AM"
            book_res = await book_appointment(
                visitor_name="Vikramaditya Rao",
                contact_info="+91-98765-11223",
                staff_or_department=doctor_name,
                date_str=target_date,
                time_slot=chosen_slot,
                purpose="Annual cardiac wellness evaluation"
            )

            # 4. Cancel to clean up
            cancel_res = await cancel_appointment("Vikramaditya Rao", target_date)
            return doc_res, avail_res, book_res, cancel_res

        doc_res, avail_res, book_res, cancel_res = asyncio.run(run_flow())
        self.assertEqual(doc_res["status"], "success")
        self.assertEqual(avail_res["status"], "success")
        self.assertEqual(book_res["status"], "confirmed")
        self.assertEqual(cancel_res["status"], "cancelled")

    def test_11_doctor_rest_api_endpoints(self):
        # 1. List doctors
        res = self.client.get("/api/doctors")
        self.assertEqual(res.status_code, 200)
        docs = res.json()
        self.assertEqual(len(docs), 10)

        # 2. List specializations
        res_spec = self.client.get("/api/doctors/specializations/list")
        self.assertEqual(res_spec.status_code, 200)
        specs = res_spec.json()
        self.assertIn("Cardiology", specs)
        self.assertIn("Dermatology", specs)

        # 3. Get single doctor
        first_id = docs[0]["id"]
        res_doc = self.client.get(f"/api/doctors/{first_id}")
        self.assertEqual(res_doc.status_code, 200)
        self.assertEqual(res_doc.json()["id"], first_id)

    @patch("google.genai.Client")
    def test_12_text_chat_function_calling_manual_execution(self, mock_client_cls):
        """Verify proper manual async function calling without AFC crash."""
        # Setup mock Gemini responses
        fc = types.FunctionCall(name="search_doctors", args={"query": "Cardiology"})
        resp1 = MagicMock()
        resp1.function_calls = [fc]
        resp1.candidates = [MagicMock(content=types.Content(role="model", parts=[types.Part.from_function_call(name=fc.name, args=fc.args)]))]
        resp1.text = None

        resp2 = MagicMock()
        resp2.function_calls = None
        resp2.text = "I found Dr. Arun Prakash Sharma, our senior cardiologist. Would you like me to book an appointment for you?"

        mock_instance = MagicMock()
        mock_instance.aio.models.generate_content = AsyncMock(side_effect=[resp1, resp2])
        mock_client_cls.return_value = mock_instance

        # Call /api/chat with an active API key
        res = self.client.post("/api/chat", json={
            "message": "Find a cardiologist",
            "api_key": "test_gemini_api_key"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reply", data)
        self.assertIn("Dr. Arun Prakash Sharma", data["reply"])
        self.assertTrue(any(a["tool"] == "search_doctors" for a in data.get("actions", [])))

        # Verify automatic_function_calling was disabled in generate_content config
        call_kwargs = mock_instance.aio.models.generate_content.call_args_list[0].kwargs
        cfg = call_kwargs["config"]
        self.assertTrue(cfg.automatic_function_calling.disable)

    def test_13_full_patient_conversational_voice_booking_flow(self):
        """Test full conversational journey:
        1. Spoken intent -> search doctor & check availability.
        2. Follow-up missing info collection -> explicit confirmation prompt.
        3. Explicit confirmation -> actual database booking verified.
        """
        history = []

        # Turn 1: Patient expresses intent to book a cardiologist
        res1 = self.client.post("/api/chat", json={
            "message": "Hey Jack, book an appointment with a cardiologist.",
            "history": history
        })
        self.assertEqual(res1.status_code, 200)
        d1 = res1.json()
        self.assertIn("Dr. Arun Prakash Sharma", d1["reply"])
        self.assertIn("slots", d1["reply"].lower())
        self.assertTrue(any(a["tool"] == "check_availability" for a in d1.get("actions", [])))

        history.append({"role": "user", "text": "Hey Jack, book an appointment with a cardiologist."})
        history.append({"role": "model", "text": d1["reply"]})

        # Turn 2: Patient provides missing slot, name, contact
        res2 = self.client.post("/api/chat", json={
            "message": "Tomorrow at 11:00 AM. My name is Sarah Connor, phone is 9876501234.",
            "history": history
        })
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertIn("confirm", d2["reply"].lower())
        self.assertIn("Sarah Connor", d2["reply"])
        self.assertIn("11:00 AM", d2["reply"])

        history.append({"role": "user", "text": "Tomorrow at 11:00 AM. My name is Sarah Connor, phone is 9876501234."})
        history.append({"role": "model", "text": d2["reply"]})

        # Turn 3: Patient gives explicit confirmation
        res3 = self.client.post("/api/chat", json={
            "message": "Yes, please confirm.",
            "history": history
        })
        self.assertEqual(res3.status_code, 200)
        d3 = res3.json()
        self.assertIn("confirmed", d3["reply"].lower())
        self.assertIn("#", d3["reply"])
        self.assertTrue(any(a["tool"] == "book_appointment" for a in d3.get("actions", [])))

        # Verify verified booking in database
        async def check_and_clean_db():
            db = await get_db()
            try:
                async with db.execute(
                    "SELECT * FROM appointments WHERE visitor_name = 'Sarah Connor' AND status = 'Confirmed'"
                ) as cur:
                    row = await cur.fetchone()
                if row:
                    await db.execute("DELETE FROM appointments WHERE visitor_name = 'Sarah Connor'")
                    await db.commit()
                return row
            finally:
                await db.close()

        row = asyncio.run(check_and_clean_db())
        self.assertIsNotNone(row)
        self.assertEqual(row["visitor_name"], "Sarah Connor")
        self.assertEqual(row["time_slot"], "11:00 AM")
        self.assertIn("Dr. Arun Prakash Sharma", row["staff_name"])

    def test_14_book_appointment_with_aliases_and_verification(self):
        """Test parameter alias resilience, database write verification, and conflict detection."""
        async def run_alias_tests():
            tomorrow = (date.today() + timedelta(days=1)).isoformat()

            # 1. Book using aliases: patient_name, doctor, date="tomorrow", slot="02:30 pm"
            res1 = await book_appointment(
                patient_name="Michael Scott",
                phone="555-0192",
                doctor="Dr. Priya",  # Partial doctor name matching Dr. Priyanka Venkatesh (Dermatology)
                date="tomorrow",
                slot="02:30 pm",
                reason="Skin allergy checkup"
            )

            # 2. Duplicate booking attempt for the same slot
            res2 = await book_appointment(
                patient_name="Dwight Schrute",
                doctor="Dr. Priyanka Venkatesh",
                date=tomorrow,
                slot="02:30 PM"
            )

            # 3. Missing patient name
            res3 = await book_appointment(
                doctor="Dr. Priyanka Venkatesh",
                date=tomorrow,
                slot="03:00 PM"
            )

            # Clean up
            db = await get_db()
            try:
                await db.execute("DELETE FROM appointments WHERE visitor_name IN ('Michael Scott', 'Dwight Schrute')")
                await db.commit()
            finally:
                await db.close()

            return res1, res2, res3

        res1, res2, res3 = asyncio.run(run_alias_tests())

        # Test 1 assertions
        self.assertEqual(res1["status"], "confirmed")
        self.assertTrue(res1["verified"])
        self.assertEqual(res1["patient_name"], "Michael Scott")
        self.assertEqual(res1["time_slot"], "02:30 PM")
        self.assertIn("Dr. Priyanka Venkatesh", res1["doctor_name"])

        # Test 2 assertions (conflict)
        self.assertEqual(res2["status"], "conflict")
        self.assertIn("already has an appointment", res2["message"])

        # Test 3 assertions (missing patient name)
        self.assertEqual(res3["status"], "error")
        self.assertEqual(res3["error_type"], "missing_patient_name")

    @patch("google.genai.Client")
    def test_15_gemini_api_book_appointment_tool_execution(self, mock_client_cls):
        """Verify that when Gemini model calls book_appointment with aliases, it is executed and saved in DB."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        fc = types.FunctionCall(
            name="book_appointment",
            args={
                "patient_name": "Diana Prince",
                "phone": "+1-555-0199",
                "doctor": "Dr. Arun Prakash Sharma",
                "date": tomorrow,
                "slot": "04:00 PM",
                "reason": "Cardiology consult"
            }
        )
        resp1 = MagicMock()
        resp1.function_calls = [fc]
        resp1.candidates = [MagicMock(content=types.Content(role="model", parts=[types.Part.from_function_call(name=fc.name, args=fc.args)]))]
        resp1.text = None

        resp2 = MagicMock()
        resp2.function_calls = None
        resp2.text = "Your appointment with Dr. Arun Prakash Sharma has been successfully booked for tomorrow at 04:00 PM!"

        mock_instance = MagicMock()
        mock_instance.aio.models.generate_content = AsyncMock(side_effect=[resp1, resp2])
        mock_client_cls.return_value = mock_instance

        res = self.client.post("/api/chat", json={
            "message": "Yes, please book the appointment for Diana Prince",
            "api_key": "valid_mock_gemini_key_12345"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reply", data)
        self.assertTrue(any(a["tool"] == "book_appointment" for a in data.get("actions", [])))

        # Verify that Diana Prince was actually saved to SQLite database
        async def check_booking():
            db = await get_db()
            try:
                async with db.execute(
                    "SELECT id, visitor_name, staff_name, date, time_slot, status FROM appointments WHERE visitor_name = 'Diana Prince'"
                ) as cur:
                    row = await cur.fetchone()
                if row:
                    await db.execute("DELETE FROM appointments WHERE visitor_name = 'Diana Prince'")
                    await db.commit()
                return row
            finally:
                await db.close()

        saved = asyncio.run(check_booking())
        self.assertIsNotNone(saved)
        self.assertEqual(saved["visitor_name"], "Diana Prince")
        self.assertEqual(saved["status"], "Confirmed")
        self.assertEqual(saved["time_slot"], "04:00 PM")

    def test_16_dashboard_stats_and_patients_endpoints(self):
        """Test the live aggregated dashboard metrics and patients directory endpoints."""
        # 1. /api/stats
        res_stats = self.client.get("/api/stats")
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.json()
        self.assertIn("total_appointments", stats)
        self.assertIn("available_doctors", stats)
        self.assertIn("registered_patients", stats)
        self.assertIn("pending_appointments", stats)
        self.assertTrue(stats["total_appointments"] >= 0)
        self.assertTrue(stats["total_doctors"] >= 10)

        # 2. /api/patients
        res_patients = self.client.get("/api/patients")
        self.assertEqual(res_patients.status_code, 200)
        patients = res_patients.json()
        self.assertIsInstance(patients, list)
        if patients:
            p = patients[0]
            self.assertIn("name", p)
            self.assertIn("contact_info", p)
            self.assertIn("total_appointments", p)

    def test_17_admin_doctor_crud_and_appointment_status_update(self):
        """Test admin doctor registration, deletion, and appointment status patch."""
        # 1. Register new doctor
        new_doc_data = {
            "name": "Dr. Test Specialist",
            "specialization": "Radiology",
            "department": "Imaging Centre",
            "qualification": "MBBS, MD",
            "experience_years": 10,
            "consultation_fee": "₹1000",
            "available_days": "Mon, Wed",
            "available_slots": "10:00 AM, 11:00 AM",
            "rating": 4.9,
            "status": "Available",
            "phone_extension": "301",
            "email": "test.specialist@hrenterprises.com",
            "bio": "Expert in diagnostic radiology",
            "avatar_emoji": "🩺"
        }
        res_add = self.client.post("/api/doctors", json=new_doc_data)
        self.assertEqual(res_add.status_code, 200)
        add_result = res_add.json()
        doc_id = add_result["id"]

        # Verify added doctor is queryable
        res_get = self.client.get(f"/api/doctors/{doc_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["name"], "Dr. Test Specialist")

        # 2. Delete test doctor
        res_del = self.client.delete(f"/api/doctors/{doc_id}")
        self.assertEqual(res_del.status_code, 200)

        # 3. Patch appointment status
        # Book a temporary appointment
        tomorrow = (date.today() + timedelta(days=2)).isoformat()
        res_book = self.client.post("/api/appointments", json={
            "visitor_name": "Tony Stark",
            "contact_info": "tony@stark.com",
            "staff_or_department": "Dr. Arun Prakash Sharma",
            "date": tomorrow,
            "time_slot": "03:00 PM",
            "purpose": "Heart checkup"
        })
        self.assertEqual(res_book.status_code, 200)
        appt_id = res_book.json()["booking_id"]

        # Patch to Completed
        res_patch = self.client.patch(f"/api/appointments/{appt_id}/status", json={"status": "Completed"})
        self.assertEqual(res_patch.status_code, 200)

        # Clean up
        async def clean():
            db = await get_db()
            try:
                await db.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
                await db.commit()
            finally:
                await db.close()
        asyncio.run(clean())

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
