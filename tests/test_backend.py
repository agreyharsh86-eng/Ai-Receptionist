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

if __name__ == "__main__":
    unittest.main()
