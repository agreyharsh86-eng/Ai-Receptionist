"""OTP Generation, Hashing, and Multi-Channel Delivery Service (Email & SMS).

Email delivery uses the Resend API (https://resend.com).
Falls back to console logging when RESEND_API_KEY is not configured.
"""

import re
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import app.config as config

logger = logging.getLogger("otp_service")


# ---------------------------------------------------------------------------
# OTP Core: generate / hash / verify
# ---------------------------------------------------------------------------

def generate_otp() -> str:
    """Generate a cryptographically secure random 6-digit OTP."""
    code = secrets.randbelow(900000) + 100000
    return str(code)


def hash_otp(otp: str, salt: str = "") -> str:
    """Hash the OTP using SHA-256 with a salt so it is never stored as plain text."""
    salt_val = salt or config.JWT_SECRET
    salted = f"{otp}:{salt_val}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def verify_otp_hash(input_otp: str, stored_hash: str, salt: str = "") -> bool:
    """Compare an input OTP against the stored SHA-256 hash using constant-time comparison."""
    if not input_otp or not stored_hash:
        return False
    computed = hash_otp(input_otp.strip(), salt)
    return secrets.compare_digest(computed, stored_hash)


# ---------------------------------------------------------------------------
# Delivery Router
# ---------------------------------------------------------------------------

async def deliver_otp(identifier: str, channel: str, otp: str) -> Dict[str, Any]:
    """Deliver OTP to email or phone number based on channel."""
    if channel == "email":
        return await send_email_otp(identifier, otp)
    elif channel == "phone":
        return await send_sms_otp(identifier, otp)
    else:
        raise ValueError(f"Unsupported delivery channel: '{channel}'. Use 'email' or 'phone'.")


# ---------------------------------------------------------------------------
# Email OTP via Resend API
# ---------------------------------------------------------------------------

def _build_otp_html(otp: str) -> str:
    """Return the branded HTML email body for the OTP."""
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #070b14; color: #f8fafc; margin: 0; padding: 20px; }}
    .container {{ max-width: 480px; margin: 0 auto; background: #0f172a; border: 1px solid #00f0ff; border-radius: 16px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
    .header {{ text-align: center; margin-bottom: 24px; }}
    .header h1 {{ color: #00f0ff; font-size: 24px; margin: 0; }}
    .header p {{ color: #94a3b8; font-size: 14px; margin-top: 4px; }}
    .otp-box {{ background: rgba(0, 240, 255, 0.1); border: 2px dashed #00f0ff; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0; }}
    .otp-code {{ font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #ffffff; font-family: monospace; }}
    .expiry {{ color: #f43f5e; font-size: 13px; font-weight: 600; text-align: center; margin-bottom: 20px; }}
    .footer {{ text-align: center; color: #64748b; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>⚡ {config.COMPANY_NAME}</h1>
      <p>Jack — AI Receptionist Authentication</p>
    </div>
    <p>Hello,</p>
    <p>You requested a one-time passcode to sign in or verify your account. Please use the verification code below:</p>
    <div class="otp-box">
      <div class="otp-code">{otp}</div>
    </div>
    <div class="expiry">⚠️ This code expires in 30 seconds. Do not share it with anyone.</div>
    <div class="footer">
      If you did not request this verification, you can safely ignore this email.
    </div>
  </div>
</body>
</html>"""


async def send_email_otp(to_email: str, otp: str) -> Dict[str, Any]:
    """Send OTP email via Resend API if configured, or log for developer setup."""
    to_email = to_email.strip().lower()

    html_content = _build_otp_html(otp)

    # Check whether Resend credentials are configured
    has_resend = bool(
        config.RESEND_API_KEY
        and not config.RESEND_API_KEY.startswith("your_")
        and len(config.RESEND_API_KEY) > 10
    )

    if has_resend:
        try:
            import resend

            resend.api_key = config.RESEND_API_KEY

            params: resend.Emails.SendParams = {
                "from": config.EMAIL_FROM,
                "to": [to_email],
                "subject": f"Your Verification Code – {config.COMPANY_NAME}",
                "html": html_content,
            }

            email_response = resend.Emails.send(params)
            email_id = email_response.get("id", "") if isinstance(email_response, dict) else getattr(email_response, "id", "")

            logger.info(f"Resend email sent to {to_email} (id={email_id})")
            return {
                "delivered": True,
                "provider": "resend",
                "message": f"Verification code sent to {to_email}",
            }

        except Exception as e:
            logger.error(f"Resend delivery failed to {to_email}: {e}", exc_info=True)
            return {
                "delivered": False,
                "provider": "resend_failed",
                "error": str(e),
                "message": "Email delivery error. Please try again or check Resend configuration.",
            }
    else:
        # Development Mode: Log code for instant verification testing
        logger.info("======================================================")
        logger.info(f"[DEV AUTH] Verification OTP for {to_email}: >>> {otp} <<< (Expires in 30s)")
        logger.info("======================================================")
        return {
            "delivered": True,
            "provider": "console_dev_mode",
            "message": f"Verification code generated for {to_email}. (Set RESEND_API_KEY in .env for live email delivery)",
        }


# ---------------------------------------------------------------------------
# SMS OTP via Twilio
# ---------------------------------------------------------------------------

async def send_sms_otp(to_phone: str, otp: str) -> Dict[str, Any]:
    """Send OTP SMS via Twilio if configured, or log for developer setup."""
    to_phone = to_phone.strip()
    sms_body = f"Your {config.COMPANY_NAME} (Jack AI) verification code is {otp}. Valid for 30 seconds."

    has_twilio = bool(
        config.TWILIO_ACCOUNT_SID
        and config.TWILIO_AUTH_TOKEN
        and config.TWILIO_PHONE_NUMBER
        and not config.TWILIO_ACCOUNT_SID.startswith("your_")
    )

    if has_twilio:
        try:
            import urllib.request
            import urllib.parse
            import base64

            twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json"
            data = urllib.parse.urlencode({
                "To": to_phone,
                "From": config.TWILIO_PHONE_NUMBER,
                "Body": sms_body
            }).encode("utf-8")

            req = urllib.request.Request(twilio_url, data=data, method="POST")
            auth_str = f"{config.TWILIO_ACCOUNT_SID}:{config.TWILIO_AUTH_TOKEN}"
            auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            req.add_header("Authorization", f"Basic {auth_b64}")

            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.getcode()
                logger.info(f"Twilio SMS sent to {to_phone} (HTTP {status_code})")
                return {
                    "delivered": True,
                    "provider": "twilio",
                    "message": f"SMS OTP sent to {to_phone}",
                }
        except Exception as e:
            logger.error(f"Twilio SMS failed to {to_phone}: {e}", exc_info=True)
            return {
                "delivered": False,
                "provider": "twilio_failed",
                "error": str(e),
                "message": "Twilio SMS delivery error. (Check Twilio credentials in .env)",
            }
    else:
        # Development Mode: Log code for instant verification testing
        logger.info("======================================================")
        logger.info(f"[DEV AUTH] Verification OTP for {to_phone}: >>> {otp} <<< (Expires in 30s)")
        logger.info("======================================================")
        return {
            "delivered": True,
            "provider": "console_dev_mode",
            "message": f"SMS OTP generated for {to_phone}. (Set Twilio credentials in .env for live SMS delivery)",
        }
