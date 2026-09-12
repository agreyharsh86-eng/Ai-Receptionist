"""Unit and Integration Tests for AI Receptionist Backend."""

import asyncio
import unittest
import os
import aiosqlite
from fastapi.testclient import TestClient
from datetime import date, timedelta

from app.main import app
from app.database import init_db, get_db
from app.tools.receptionist_tools import (
    check_availability,
    book_appointment,
    cancel_appointment,
    leave_message,
    lookup_directory,
    get_company_info,
    transfer_call
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

        # Search query
        res_search = self.client.get("/api/directory?q=Marcus")
        self.assertEqual(res_search.status_code, 200)
        found = res_search.json()
        self.assertTrue(any("Marcus" in s["name"] for s in found))

    def test_03_lookup_directory_tool(self):
        async def run_tool():
            return await lookup_directory("Sales")
        result = asyncio.run(run_tool())
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["total_matches"] > 0)

    def test_04_check_availability_tool(self):
        async def run_tool():
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            return await check_availability("Marcus Sterling", tomorrow)
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
                staff_or_department="Marcus Sterling",
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
                recipient_name="Sarah Jenkins",
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
            return await transfer_call("Jessica Wong")
        result = asyncio.run(run_tool())
        self.assertEqual(result["status"], "transfer_initiated")
        self.assertEqual(result["extension"], "601")

if __name__ == "__main__":
    unittest.main()
