"""
tools/mongo_user_updater_tool.py — LangChain tool mirroring MongoDBUserUpdater.
Allows agents to update the user profile document in MongoDB.

Primary lookup: user_id == session_id  (users table uses user_id = session_id)
Fallback: email or phone via identity string.
"""

from __future__ import annotations
import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def make_user_updater_tool(session_id: str, identity: str = ""):
    """
    Returns a MongoDBUserUpdater tool.
    Primary key for lookup: user_id == session_id
    Fallback: identity (email or phone)
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from db.mongo_client import update_user, increment_account_balance

    @tool
    def mongodb_user_updater(update_json: str) -> str:
        """
        Update the user's profile in MongoDB.

        Input must be a JSON string with the fields to update.
        Special field: if 'account_balance_increment' (float) is present, it is
        ADDED to the existing balance (not replaced).

        Common usage examples:
        - Block card:       '{"debit_card_status": "BLOCKED"}'
        - Credit loan:      '{"account_balance_increment": 50000}'
        - Update any field: '{"address": "123 New St"}'

        Returns: JSON string with {"status": "updated"} or {"error": "..."}
        """
        try:
            fields: dict = json.loads(update_json)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"Invalid JSON: {exc}"})

        # Handle special increment field
        increment = fields.pop("account_balance_increment", None)
        success = True

        if increment is not None:
            ok = increment_account_balance(
                session_id=session_id,
                amount=float(increment),
                identity=identity or None,
            )
            success = ok
            logger.info("[UserUpdater] Incremented balance by %s for session=%s", increment, session_id)

        if fields:
            ok = update_user(
                session_id=session_id,
                update_fields=fields,
                identity=identity or None,
            )
            success = success and ok
            logger.info("[UserUpdater] Updated fields=%s for session=%s", fields, session_id)

        if success:
            return json.dumps({"status": "updated", "session_id": session_id})
        return json.dumps({"error": "Update had no effect — user not found or unchanged"})

    return mongodb_user_updater
