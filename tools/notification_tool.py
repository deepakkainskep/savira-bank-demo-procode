"""
tools/notification_tool.py — LangChain tool mirroring SendNotificationTool.

Confirmed working payload format:
  POST https://wappdemo-fncapp.azurewebsites.net/api/notification/send?code=XXX
  {
    "phone":   "919376072346",
    "title":   "Notification from ABC Bank",
    "content": "Your message here",
    "payload": {
      "navigateTo": "notification",
      "text": "Your message here"
    }
  }
"""

from __future__ import annotations
import json
import logging
import requests

from langchain_core.tools import tool
from config import NOTIFICATION_API_URL, NOTIFICATION_API_KEY

logger = logging.getLogger(__name__)


def make_notification_tool(user_phone: str = "", user_id: str = ""):
    """
    Factory: returns a notification tool pre-loaded with the user's phone number.
    Phone is automatically injected into every notification payload.
    """

    @tool
    def send_notification(payload_json: str) -> str:
        """
        Send a push notification or approval popup to the user's mobile app.

        Input must be a JSON string with:
        - notification_type (str, required): "notification" | "approval-popup"
        - title (str, required): notification title shown on device
        - content (str, required): main notification body text
        - navigate_to (str, optional): screen to open — default "notification"
        - text (str, optional): extra text in payload — defaults to content

        RESTRICTED usage:
        - "approval-popup"  ONLY at DEBIT_REQUEST step (loan disbursement)
        - "notification"    ONLY at FINAL_APPROVAL and CREDIT_NOTIFICATION
        - NEVER use for eligibility, profile verification, T&C messages

        Returns: JSON string with {"status": "sent"} or {"status": "sent_mock"}
        """
        try:
            inp: dict = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"Invalid JSON: {exc}"})

        notification_type = inp.get("notification_type", "notification")
        title   = inp.get("title", "Notification from ABC Bank")
        content = inp.get("content") or inp.get("message", "")
        navigate_to = inp.get("navigate_to", notification_type)
        text = inp.get("text") or content

        if not content:
            return json.dumps({"error": "content or message is required"})

        # ── Confirmed working payload format ──────────────────────────────────
        body = {
            "phone":   user_phone,
            "title":   title,
            "content": content,
            "payload": {
                "navigateTo": navigate_to,
                "text":       text,
            },
        }

        logger.info("[Notification] Sending type=%s to phone=%s body=%s",
                    notification_type, user_phone, json.dumps(body))

        if not NOTIFICATION_API_URL:
            logger.warning("[Notification] NOTIFICATION_API_URL not configured — mocking")
            return json.dumps({"status": "sent_mock", "reason": "URL not configured"})

        auth_suffix = NOTIFICATION_API_KEY if NOTIFICATION_API_KEY else ""
        full_url    = f"{NOTIFICATION_API_URL}{auth_suffix}"

        try:
            resp = requests.post(
                full_url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code == 200:
                logger.info("[Notification] OK type=%s phone=%s resp=%s",
                            notification_type, user_phone, resp.text[:150])
                return json.dumps({
                    "status": "sent",
                    "phone":  user_phone,
                    "type":   notification_type,
                })
            else:
                logger.warning("[Notification] API %s: %s — mock fallback",
                               resp.status_code, resp.text[:200])
                return json.dumps({
                    "status":      "sent_mock",
                    "http_status": resp.status_code,
                    "api_message": resp.text[:200],
                    "note":        "Notification API returned error — flow continues",
                })
        except requests.RequestException as exc:
            logger.error("[Notification] Request failed: %s", exc)
            return json.dumps({
                "status": "sent_mock",
                "error":  str(exc),
                "note":   "Notification API unreachable — flow continues",
            })

    return send_notification


# ── Standalone tool (no phone) — fallback when factory not used ───────────────
@tool
def send_notification(payload_json: str) -> str:
    """
    Send a push notification. Use make_notification_tool() factory for auto phone injection.
    """
    return make_notification_tool()(payload_json)
