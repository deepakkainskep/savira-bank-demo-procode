"""
db/mongo_client.py — MongoDB helper: user fetcher, session store, history store, user updater.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

from config import (
    MONGO_CONNECTION_STRING,
    MONGO_DATABASE,
    MONGO_COLLECTION_HISTORY,
    MONGO_COLLECTION_SESSION,
    MONGO_COLLECTION_USERS,
)

logger = logging.getLogger(__name__)

# ─── Singleton connection ─────────────────────────────────────────────────────
_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_CONNECTION_STRING)
    return _client


def get_db():
    return get_client()[MONGO_DATABASE]


# ─── User Fetcher (mirrors MongoDBUserFetcher node) ──────────────────────────
def fetch_user(session_id: str, identity: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch user document.
    Primary lookup: user_id == session_id  (users table uses user_id = session_id)
    Fallback lookup: email or phone from identity string (if provided)
    """
    db = get_db()
    col = db[MONGO_COLLECTION_USERS]

    # Primary: match user_id field to session_id
    user = col.find_one({"user_id": session_id}, {"_id": 0})
    if user:
        logger.info("User found by user_id=%s", session_id)
        return user

    # Fallback: match by email or phone
    if identity:
        user = col.find_one(
            {"$or": [
                {"user_email": identity},
                {"email": identity},
                {"user_phone": identity},
                {"phone": identity},
            ]},
            {"_id": 0}
        )
        if user:
            logger.info("User found by identity=%s", identity)
            return user

    logger.warning("User not found for session_id=%s identity=%s", session_id, identity)
    return None


# ─── User Updater (mirrors MongoDBUserUpdater node) ──────────────────────────
def update_user(session_id: str, update_fields: Dict[str, Any], identity: Optional[str] = None) -> bool:
    """
    Partially update user document.
    Primary key: user_id == session_id
    Fallback: email or phone from identity string
    """
    db = get_db()
    col = db[MONGO_COLLECTION_USERS]

    # Build query: try user_id first, then email/phone fallback
    query_parts = [{"user_id": session_id}]
    if identity:
        query_parts += [
            {"user_email": identity},
            {"email": identity},
            {"user_phone": identity},
            {"phone": identity},
        ]

    result = col.update_one(
        {"$or": query_parts},
        {"$set": update_fields}
    )
    success = result.modified_count > 0
    if not success:
        logger.warning("User update had no effect for session_id=%s fields=%s", session_id, update_fields)
    return success


def increment_account_balance(session_id: str, amount: float, identity: Optional[str] = None) -> bool:
    """Add amount to account_balance. Looks up by user_id (=session_id) first, then email/phone."""
    db = get_db()
    col = db[MONGO_COLLECTION_USERS]

    query_parts = [{"user_id": session_id}]
    if identity:
        query_parts += [
            {"user_email": identity},
            {"email": identity},
            {"user_phone": identity},
            {"phone": identity},
        ]

    result = col.update_one(
        {"$or": query_parts},
        {"$inc": {"account_balance": amount}}
    )
    return result.modified_count > 0


# ─── Session Data (mirrors GetSessionData / UpdateSessionData nodes) ──────────
def get_session_data(session_id: str) -> Dict[str, Any]:
    """Return session document or empty dict if not found."""
    db = get_db()
    col = db[MONGO_COLLECTION_SESSION]
    doc = col.find_one({"session_id": session_id}, {"_id": 0, "session_id": 0})
    return doc or {}


def update_session_data(session_id: str, update_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep-merge update_fields into the session document.
    Returns the updated document.
    """
    db = get_db()
    col = db[MONGO_COLLECTION_SESSION]

    # Build a flat $set for nested keys (e.g., card_block.current_step)
    set_payload: Dict[str, Any] = {}
    for key, value in update_fields.items():
        if isinstance(value, dict):
            # Flatten nested dict — e.g., {"card_block": {"current_step": "WAITING_CVV"}}
            # becomes {"card_block.current_step": "WAITING_CVV"} IF we want deep merge,
            # but here we store entire sub-doc replacement for simplicity.
            set_payload[key] = value
        else:
            set_payload[key] = value

    set_payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    updated = col.find_one_and_update(
        {"session_id": session_id},
        {"$set": set_payload},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return {k: v for k, v in (updated or {}).items() if k not in ("_id", "session_id")}


# ─── Conversation History (mirrors MongoDBRetrieverStore nodes) ───────────────
def store_message(
    session_id: str,
    message: str,
    sender_type: str,          # "human" | "ai"
    channel: str = "",
    user_phone: str = "",
    user_email: str = "",
    user_name: str = "",
) -> None:
    """Persist a single conversation message."""
    db = get_db()
    col = db[MONGO_COLLECTION_HISTORY]
    metadata = {
        "user_id": session_id,
        "session_id": session_id,
        "user_phone": user_phone,
        "user_email": user_email,
        "user_name": user_name,
        "sender_type": sender_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    col.insert_one({
        "session_id": session_id,
        "user_id": session_id,
        "sender_type": sender_type,
        "message": {"type": sender_type, "data": {"content": message}},
        "metadata": metadata,
        "timestamp": metadata["timestamp"],
        "channel": channel,
    })


def retrieve_messages(session_id: str, limit: int = 50) -> list[Dict[str, Any]]:
    """Retrieve conversation history for a session."""
    db = get_db()
    col = db[MONGO_COLLECTION_HISTORY]
    docs = list(col.find({"session_id": session_id}).sort("timestamp", 1).limit(limit))
    history = []
    for d in docs:
        msg = d.get("message", {})
        role = msg.get("type", "").upper()
        content = msg.get("content", "")
        history.append({"role": role, "content": content, "channel": d.get("channel", "")})
    return history
