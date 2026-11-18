"""MongoDB Client & Database Management Layer for Jack AI Authentication.

Manages connections, collections (users, otp_verifications),
TTL indexes for auto-expiring OTP records, and user authentication storage.
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import motor.motor_asyncio
import pymongo
from bson import ObjectId

import app.config as config

logger = logging.getLogger("mongo_db")

_mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_mongo_db = None
_is_connected = False

# Local fallback store in case MongoDB instance is not yet running locally
_local_users: Dict[str, Dict[str, Any]] = {}
_local_otps: List[Dict[str, Any]] = []

async def init_mongo():
    """Initialize MongoDB connection and ensure collections & indexes."""
    global _mongo_client, _mongo_db, _is_connected
    try:
        uri = config.MONGODB_URI or "mongodb://127.0.0.1:27017"
        _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=1200
        )
        _mongo_db = _mongo_client[config.MONGODB_DB_NAME]

        # Verify connection
        await _mongo_client.admin.command('ping')
        _is_connected = True
        logger.info(f"Connected to MongoDB ({config.MONGODB_DB_NAME}) at {uri}")

        # 1. Ensure TTL Index on otp_verifications for expired records
        # MongoDB automatically removes documents when 'expires_at' passes
        await _mongo_db["otp_verifications"].create_index(
            "expires_at",
            expireAfterSeconds=0,
            name="otp_ttl_expiry_index"
        )
        await _mongo_db["otp_verifications"].create_index(
            [("identifier", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
            name="otp_identifier_lookup_index"
        )

        # 2. Ensure sparse unique indexes on users collection
        await _mongo_db["users"].create_index(
            "email",
            unique=True,
            sparse=True,
            name="user_email_unique_index"
        )
        await _mongo_db["users"].create_index(
            "phone_number",
            unique=True,
            sparse=True,
            name="user_phone_unique_index"
        )
        logger.info("MongoDB indexes verified successfully.")

    except Exception as e:
        _is_connected = False
        logger.warning(
            f"MongoDB connection to '{config.MONGODB_URI}' unavailable ({e}). "
            f"Using local in-memory fallback store until MongoDB URI is configured in .env."
        )

def is_mongo_connected() -> bool:
    """Return whether live MongoDB connection is active."""
    return _is_connected

def get_mongo_db():
    """Retrieve raw MongoDB database handle."""
    return _mongo_db

# =============================================================================
# OTP Verification Collection Helpers
# =============================================================================
async def save_otp_verification(
    identifier: str,
    hashed_otp: str,
    expires_at: datetime
) -> Dict[str, Any]:
    """Store hashed OTP with expiration timestamp and zero attempts."""
    clean_id = identifier.strip().lower()
    now = datetime.now(timezone.utc)

    record = {
        "identifier": clean_id,
        "hashed_otp": hashed_otp,
        "expires_at": expires_at,
        "attempts": 0,
        "verified": False,
        "created_at": now
    }

    if _is_connected and _mongo_db is not None:
        try:
            # Invalidate any previously unverified active OTPs for this identifier
            await _mongo_db["otp_verifications"].update_many(
                {"identifier": clean_id, "verified": False},
                {"$set": {"verified": True, "invalidated": True}}
            )
            result = await _mongo_db["otp_verifications"].insert_one(record)
            record["_id"] = str(result.inserted_id)
            return record
        except Exception as e:
            logger.error(f"Error saving OTP in MongoDB: {e}")

    # Fallback storage
    # Invalidate old
    for item in _local_otps:
        if item.get("identifier") == clean_id and not item.get("verified"):
            item["verified"] = True
    record["_id"] = str(uuid.uuid4())
    _local_otps.append(record)
    return record

async def get_active_otp(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieve the latest unverified and non-expired OTP record for an identifier."""
    clean_id = identifier.strip().lower()
    now = datetime.now(timezone.utc)

    if _is_connected and _mongo_db is not None:
        try:
            doc = await _mongo_db["otp_verifications"].find_one(
                {
                    "identifier": clean_id,
                    "verified": False,
                    "expires_at": {"$gt": now}
                },
                sort=[("created_at", pymongo.DESCENDING)]
            )
            if doc:
                doc["_id"] = str(doc["_id"])
                return doc
        except Exception as e:
            logger.error(f"Error reading OTP from MongoDB: {e}")

    # Fallback search
    for item in reversed(_local_otps):
        if item.get("identifier") == clean_id and not item.get("verified"):
            exp = item.get("expires_at")
            if exp and exp > now:
                return item
    return None

async def increment_otp_attempts(identifier: str) -> int:
    """Increment failed OTP attempt count."""
    clean_id = identifier.strip().lower()

    if _is_connected and _mongo_db is not None:
        try:
            doc = await _mongo_db["otp_verifications"].find_one_and_update(
                {"identifier": clean_id, "verified": False},
                {"$inc": {"attempts": 1}},
                sort=[("created_at", pymongo.DESCENDING)],
                return_document=pymongo.ReturnDocument.AFTER
            )
            if doc:
                return doc.get("attempts", 1)
        except Exception as e:
            logger.error(f"Error incrementing OTP attempts in MongoDB: {e}")

    # Fallback
    for item in reversed(_local_otps):
        if item.get("identifier") == clean_id and not item.get("verified"):
            item["attempts"] = item.get("attempts", 0) + 1
            return item["attempts"]
    return 1

async def mark_otp_verified(identifier: str) -> bool:
    """Mark OTP as verified and consumed so it cannot be re-used."""
    clean_id = identifier.strip().lower()

    if _is_connected and _mongo_db is not None:
        try:
            await _mongo_db["otp_verifications"].update_many(
                {"identifier": clean_id},
                {"$set": {"verified": True, "consumed_at": datetime.now(timezone.utc)}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking OTP verified in MongoDB: {e}")

    # Fallback
    for item in _local_otps:
        if item.get("identifier") == clean_id:
            item["verified"] = True
    return True

# =============================================================================
# Users Collection Helpers
# =============================================================================
async def find_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Look up user by _id."""
    if not user_id:
        return None

    if _is_connected and _mongo_db is not None:
        try:
            query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
            doc = await _mongo_db["users"].find_one(query)
            if doc:
                doc["_id"] = str(doc["_id"])
                return doc
        except Exception as e:
            logger.error(f"Error finding user in MongoDB: {e}")

    # Fallback
    for uid, user in _local_users.items():
        if uid == str(user_id) or user.get("_id") == str(user_id):
            return user
    return None

async def find_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """Look up user by either email or phone number."""
    clean_id = identifier.strip().lower()

    if _is_connected and _mongo_db is not None:
        try:
            doc = await _mongo_db["users"].find_one({
                "$or": [
                    {"email": clean_id},
                    {"phone_number": identifier.strip()}
                ]
            })
            if doc:
                doc["_id"] = str(doc["_id"])
                return doc
        except Exception as e:
            logger.error(f"Error querying user by identifier in MongoDB: {e}")

    # Fallback
    for user in _local_users.values():
        if user.get("email") == clean_id or user.get("phone_number") == identifier.strip():
            return user
    return None

async def upsert_user_on_login(
    identifier: str,
    channel: str,
    name: Optional[str] = None
) -> Dict[str, Any]:
    """Register new user or authenticate existing user upon successful OTP verification."""
    clean_id = identifier.strip()
    is_email = (channel == "email") or ("@" in clean_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    existing = await find_user_by_identifier(clean_id)

    if existing:
        # Existing user: update last_login
        user_id = str(existing["_id"])
        update_fields: Dict[str, Any] = {"last_login": now_iso}
        if is_email:
            update_fields["email_verified"] = True
        else:
            update_fields["phone_verified"] = True
        if name and not existing.get("name"):
            update_fields["name"] = name.strip()

        if _is_connected and _mongo_db is not None:
            try:
                query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
                await _mongo_db["users"].update_one(query, {"$set": update_fields})
                existing.update(update_fields)
                existing["_id"] = user_id
                return existing
            except Exception as e:
                logger.error(f"Error updating user in MongoDB: {e}")

        # Fallback update
        existing.update(update_fields)
        _local_users[user_id] = existing
        return existing

    # New user: Create account
    user_record = {
        "name": name.strip() if name else "",
        "email": clean_id.lower() if is_email else None,
        "phone_number": clean_id if not is_email else None,
        "email_verified": is_email,
        "phone_verified": not is_email,
        "created_at": now_iso,
        "last_login": now_iso
    }

    if _is_connected and _mongo_db is not None:
        try:
            result = await _mongo_db["users"].insert_one(user_record)
            user_record["_id"] = str(result.inserted_id)
            logger.info(f"New user registered in MongoDB: {user_record['_id']} ({clean_id})")
            return user_record
        except Exception as e:
            logger.error(f"Error creating user in MongoDB: {e}")

    # Fallback create
    user_id = str(uuid.uuid4())
    user_record["_id"] = user_id
    _local_users[user_id] = user_record
    logger.info(f"New user registered in local store: {user_id} ({clean_id})")
    return user_record

