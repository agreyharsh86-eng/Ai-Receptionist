"""
Unit and Integration Tests for MongoDB OTP Authentication System.
Tests generation, hashing, 30s expiration, attempts limit, single-use invalidation,
JWT generation and verification, and FastAPI endpoints.
"""
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
import app.config as config
from app.services.otp_service import generate_otp, hash_otp, verify_otp_hash
from app.database_mongo import (
    init_mongo,
    save_otp_verification,
    get_active_otp,
    increment_otp_attempts,
    mark_otp_verified,
    upsert_user_on_login,
    find_user_by_id,
    find_user_by_identifier
)
from app.services.auth_service import create_access_token, decode_access_token


class TestAuthSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        asyncio.run(init_mongo())
        cls.client = TestClient(app)

    def test_01_otp_generation_and_hashing(self):
        """OTP must be a 6-digit numeric string and verify using constant-time hash."""
        otp = generate_otp()
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

        # Test hash & verify
        hashed = hash_otp(otp)
        self.assertNotEqual(otp, hashed)
        self.assertTrue(verify_otp_hash(otp, hashed))
        self.assertFalse(verify_otp_hash("000000" if otp != "000000" else "111111", hashed))

    def test_02_send_otp_email_api(self):
        """API /api/auth/send-otp must succeed and indicate 30s expiration."""
        payload = {
            "identifier": "test.patient@example.com",
            "channel": "email"
        }
        res = self.client.post("/api/auth/send-otp", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["expires_in"], 30)
        self.assertEqual(data["channel"], "email")

    def test_03_send_otp_phone_api(self):
        """API /api/auth/send-otp with phone number must succeed."""
        payload = {
            "identifier": "+919876543210",
            "channel": "phone"
        }
        res = self.client.post("/api/auth/send-otp", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["channel"], "phone")

    def test_04_verify_otp_and_receive_jwt(self):
        """Valid OTP must return JWT access token and user record."""
        identifier = "auth_tester@example.com"
        otp = generate_otp()
        hashed = hash_otp(otp)

        # Directly store active OTP
        asyncio.run(save_otp_verification(identifier, hashed, expires_in_seconds=30))

        verify_payload = {
            "identifier": identifier,
            "otp": otp,
            "name": "Jane Doe Tester"
        }
        res = self.client.post("/api/auth/verify-otp", json=verify_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("token", data)
        self.assertEqual(data["user"]["email"], identifier)
        self.assertEqual(data["user"]["name"], "Jane Doe Tester")

        # Decode JWT token to verify signature and claims
        payload = decode_access_token(data["token"])
        self.assertIsNotNone(payload)
        self.assertEqual(payload["email"], identifier)

    def test_05_otp_single_use_invalidation(self):
        """Reusing the same OTP must fail because it was invalidated upon first use."""
        identifier = "single_use_test@example.com"
        otp = generate_otp()
        hashed = hash_otp(otp)

        asyncio.run(save_otp_verification(identifier, hashed, expires_in_seconds=30))

        # First verification succeeds
        res1 = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp})
        self.assertEqual(res1.status_code, 200)

        # Second verification fails immediately
        res2 = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("expired", res2.json()["detail"].lower())

    def test_06_wrong_otp_and_max_attempts_lockout(self):
        """Entering incorrect OTP increments attempt counter and locks out after max attempts."""
        identifier = "attempts_test@example.com"
        real_otp = "123456"
        hashed = hash_otp(real_otp)

        asyncio.run(save_otp_verification(identifier, hashed, expires_in_seconds=30))

        # Attempt 1: wrong code
        res1 = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": "999999"})
        self.assertEqual(res1.status_code, 400)
        self.assertIn("2 attempt(s) remaining", res1.json()["detail"])

        # Attempt 2: wrong code
        res2 = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": "888888"})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("1 attempt(s) remaining", res2.json()["detail"])

        # Attempt 3: wrong code -> Exceeded
        res3 = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": "777777"})
        self.assertEqual(res3.status_code, 400)
        self.assertIn("maximum attempts", res3.json()["detail"].lower())

        # Attempt 4: even if real code is provided now, it must be locked out
        res4 = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": real_otp})
        self.assertEqual(res4.status_code, 400)
        self.assertIn("maximum verification attempts exceeded", res4.json()["detail"].lower())

    def test_07_expired_otp_rejection(self):
        """OTP with expires_at in the past must be rejected."""
        identifier = "expired_test@example.com"
        otp = "654321"
        hashed = hash_otp(otp)

        # Save with negative or 0 expiry to simulate past expiration
        asyncio.run(save_otp_verification(identifier, hashed, expires_in_seconds=-10))

        res = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp})
        self.assertEqual(res.status_code, 400)
        self.assertIn("expired", res.json()["detail"].lower())

    def test_08_protected_me_endpoint(self):
        """GET /api/auth/me requires valid Bearer token."""
        # Unauthenticated request
        unauth_res = self.client.get("/api/auth/me")
        self.assertEqual(unauth_res.status_code, 401)

        # Authenticated request
        identifier = "me_endpoint_test@example.com"
        otp = generate_otp()
        asyncio.run(save_otp_verification(identifier, hash_otp(otp), expires_in_seconds=30))

        verify_res = self.client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp, "name": "Me Tester"})
        token = verify_res.json()["token"]

        auth_res = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(auth_res.status_code, 200)
        user = auth_res.json()["user"]
        self.assertEqual(user["email"], identifier)
        self.assertEqual(user["name"], "Me Tester")

    def test_09_logout_endpoint(self):
        """POST /api/auth/logout should return success."""
        res = self.client.post("/api/auth/logout")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
