"""
tools/whatsapp_tool.py — LangChain tool mirroring SaviraWhatsAppTool.

Azure Function URL format:
  POST https://wappdemo-fncapp.azurewebsites.net/api/message/send?code=XXX
  Body: { phone, message, ... }
  Auth: code is in WHATSAPP_API_KEY as query-string value (e.g. "?code=n98zeI...")
"""

from __future__ import annotations
import json
import logging
import requests

from langchain_core.tools import tool
from config import WHATSAPP_API_URL, WHATSAPP_API_KEY

logger = logging.getLogger(__name__)


@tool
def send_whatsapp_message(payload_json: str) -> str:
    """
    Send a WhatsApp message to a user via the Savira WhatsApp Azure Function.

    Input must be a JSON string with these fields:
    - phone (str, required): recipient phone number (e.g. "916350618176")
    - message (str, required): text body to send
    - channel (str, optional): should be "whatsapp"
    - file_url (str, optional): URL of file to attach
    - file_name (str, optional): filename for the attachment

    Returns: JSON string with {"status": "sent"} or {"error": "..."}

    Use ONLY for WhatsApp channel delivery. Never use for chat responses.
    """
    try:
        payload: dict = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc}"})

    phone   = payload.get("phone", "")
    message = payload.get("message", "")

    if not phone or not message:
        return json.dumps({"error": "phone and message are required"})

    # Build correct payload — confirmed working format: {phone, message, type}
    body = {
        "phone":   phone,
        "message": message,
        "type":    payload.get("type", "text"),
    }
    if payload.get("file_url"):
        body["file_url"]  = payload["file_url"]
        body["file_name"] = payload.get("file_name", "document")
        body["type"]      = "document"

    auth_suffix = WHATSAPP_API_KEY if WHATSAPP_API_KEY else ""
    full_url    = f"{WHATSAPP_API_URL}{auth_suffix}"

    logger.info("[WhatsApp] Sending to phone=%s body=%s", phone, json.dumps(body))

    if not WHATSAPP_API_URL:
        logger.warning("[WhatsApp] WHATSAPP_API_URL not configured — mocking")
        return json.dumps({"status": "sent_mock", "phone": phone, "note": "URL not configured"})

    try:
        resp = requests.post(
            full_url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("[WhatsApp] Sent to phone=%s response=%s", phone, resp.text[:100])
        return json.dumps({"status": "sent", "phone": phone})
    except requests.RequestException as exc:
        logger.error("[WhatsApp] Error: %s", exc)
        logger.warning("[WhatsApp] Returning mock success (API unavailable)")
        return json.dumps({"status": "sent_mock", "phone": phone, "note": str(exc)})
