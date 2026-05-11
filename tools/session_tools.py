"""
tools/session_tools.py — LangChain tools that mirror Langflow's
GetSessionData and UpdateSessionData custom nodes.
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Session ID is injected per-invocation via a closure (see factory below).


def make_session_tools(session_id: str):
    """
    Return (get_session_data_tool, update_session_data_tool) bound to session_id.
    This matches how Langflow passes session_id to GetSessionData / UpdateSessionData.
    """
    import sys
    import os
    # Ensure project root is on path when tools are used standalone
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from db.mongo_client import get_session_data, update_session_data

    @tool
    def get_session_data_tool(dummy: str = "") -> str:
        """
        Retrieve the current session data for the active user session.
        Returns JSON string of session state including flow, loan_state, step, card_block, etc.
        """
        data = get_session_data(session_id)
        result = json.dumps(data, default=str)
        logger.info("[GetSessionData] session=%s result=%s", session_id, result)
        return result

    @tool
    def update_session_data_tool(update_json: str) -> str:
        """
        Update session state fields. Input must be a JSON string with the fields to set.
        Example: '{"flow": "loan", "loan_state": "eligibility_check", "step": "eligibility"}'
        Always call this BEFORE sending any message to the user when changing state.
        Returns the updated session state as JSON string.
        """
        try:
            fields: Dict[str, Any] = json.loads(update_json)
        except json.JSONDecodeError as exc:
            err = f"Invalid JSON for update_session_data: {exc}"
            logger.error(err)
            return json.dumps({"error": err})

        updated = update_session_data(session_id, fields)
        result = json.dumps(updated, default=str)
        logger.info("[UpdateSessionData] session=%s fields=%s updated=%s", session_id, fields, result)
        return result

    return get_session_data_tool, update_session_data_tool
