"""
Authentication API Endpoints
Handles OTP dispatch, OTP verification, user profile lookup, and session management.
"""
import re
import logging
from typing import Optional, Literal
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, HTTPException, Depends, status

import app.config as config
from app.services.otp_service import (
    generate_otp,
    hash_otp,
    verify_otp_hash,
    deliver_otp
)
from app.database_mongo import (
    save_otp_verification,
    get_active_otp,
    increment_otp_attempts,
    mark_otp_verified,
    upsert_user_on_login
)
from app.services.auth_service import (
    create_access_token,
    get_current_user
)

logger = logging.getLogger("receptionist.auth")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")


class SendOtpRequest(BaseModel):
    identifier: str = Field(..., description="Email address or phone number")
    channel: Optional[Literal["email", "phone"]] = None

    @validator("identifier")
    def clean_identifier(cls, v):
        v = v.strip().lower()
        if not v:
            raise ValueError("Identifier cannot be empty")
        return v


class VerifyOtpRequest(BaseModel):
    identifier: str = Field(..., description="Email address or phone number")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    name: Optional[str] = Field(None, max_length=100, description="Optional user display name")

    @validator("identifier")
    def clean_identifier(cls, v):
        return v.strip().lower()

    @validator("otp")
    def validate_otp_digits(cls, v):
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v


@router.post("/send-otp")
async def send_otp(request: SendOtpRequest):
    """
    Generate and dispatch a cryptographically secure 6-digit OTP.
    Expires strictly after 30 seconds.
    """
    identifier = request.identifier
    channel = request.channel

    # Auto-detect channel if omitted
    if not channel:
        if "@" in identifier:
            channel = "email"
        else:
            channel = "phone"

    # Validate identifier format
    if channel == "email":
        if not EMAIL_REGEX.match(identifier):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid email format. Please provide a valid email address (e.g. user@example.com)."
            )
    elif channel == "phone":
        cleaned_phone = re.sub(r"[\s\-\(\)]", "", identifier)
        if not PHONE_REGEX.match(cleaned_phone):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid phone number format. Please enter a valid 10-15 digit phone number."
            )
        identifier = cleaned_phone

    # Generate 6-digit secure random OTP
    otp = generate_otp()
    hashed = hash_otp(otp)

    # Persist in MongoDB with TTL index
    await save_otp_verification(
        identifier=identifier,
        hashed_otp=hashed,
        expires_in_seconds=config.OTP_EXPIRE_SECONDS
    )

    # Dispatch via Email or SMS provider (with console fallback in dev)
    delivery_success = await deliver_otp(
        identifier=identifier,
        channel=channel,
        otp=otp
    )

    return {
        "status": "success",
        "message": f"Verification code sent via {channel}.",
        "channel": channel,
        "identifier": identifier,
        "expires_in": config.OTP_EXPIRE_SECONDS,
        "delivered": delivery_success
    }


@router.post("/verify-otp")
async def verify_otp(request: VerifyOtpRequest):
    """
    Verify the 6-digit OTP code against MongoDB record.
    Invalidates on success (single-use) or on maximum failed attempts.
    Returns JWT access token and user profile on success.
    """
    identifier = request.identifier
    if "@" not in identifier:
        identifier = re.sub(r"[\s\-\(\)]", "", identifier)

    record = await get_active_otp(identifier)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired or was not requested. Please request a new code."
        )

    # Check attempt threshold
    attempts = record.get("attempts", 0)
    if attempts >= config.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum verification attempts exceeded. Please request a new code."
        )

    # Constant-time hash verification
    is_valid = verify_otp_hash(request.otp, record.get("hashed_otp", ""))

    if not is_valid:
        updated_attempts = await increment_otp_attempts(identifier)
        remaining = max(0, config.OTP_MAX_ATTEMPTS - updated_attempts)
        if remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code. Maximum attempts reached. Please request a new code."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining."
        )

    # Invalidate OTP record immediately (Single Use)
    await mark_otp_verified(identifier)

    # Determine channel and register/log in user
    channel = "email" if "@" in identifier else "phone"
    user = await upsert_user_on_login(
        identifier=identifier,
        channel=channel,
        name=request.name
    )

    # Issue JWT access token
    token = create_access_token(user_data={
        "id": user["_id"],
        "email": user.get("email"),
        "phone_number": user.get("phone_number"),
        "name": user.get("name")
    })

    return {
        "status": "success",
        "message": "Authentication successful",
        "token": token,
        "user": user
    }


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve currently authenticated user profile."""
    return {
        "status": "success",
        "user": current_user
    }


@router.post("/logout")
async def logout():
    """Client-side token revocation confirmation."""
    return {
        "status": "success",
        "message": "Logged out successfully"
    }
