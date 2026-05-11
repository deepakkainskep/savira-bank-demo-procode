"""
agents/loan_agent.py

Mirrors the LoanAgent (Agent-iwpNN) node in the Langflow graph.
Prompt source: langfloprompt/loan.md

This agent handles the full personal loan lifecycle:
  start → eligibility_check → profile_verification → loan_disbursement → disbursed

Tools available (matching Langflow edges into Agent-iwpNN):
  - UpdateSessionData       (update_session_data_tool)
  - SaviraWhatsAppTool      (send_whatsapp_message)
  - SendNotificationTool    (send_notification)
  - MongoDBUserUpdater      (mongodb_user_updater)
  - LoanVerificationAgent   (loan_verification_tool)
  - EPNApisCaller           (check_loan_eligibility)

Uses langgraph.prebuilt.create_react_agent (modern replacement for AgentExecutor).
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from agents.llm_factory import get_sub_agent_llm
from tools.whatsapp_tool import send_whatsapp_message
from tools.notification_tool import make_notification_tool
from tools.epn_tool import check_loan_eligibility
from prompts.loader import LOAN_AGENT_PROMPT

logger = logging.getLogger(__name__)


def build_loan_agent(session_id: str, identity: str):
    """
    Build a LoanAgent with all required tools bound to the current session/user.
    Returns a compiled LangGraph agent (create_react_agent).
    """
    from tools.session_tools import make_session_tools
    from tools.mongo_user_updater_tool import make_user_updater_tool
    from agents.loan_verification_agent import run_loan_verification_agent

    get_session_data_tool, update_session_data_tool = make_session_tools(session_id)
    mongodb_user_updater = make_user_updater_tool(session_id=session_id, identity=identity)

    # Fetch user's phone number for push notifications
    from db.mongo_client import fetch_user
    user = fetch_user(session_id=session_id, identity=identity or None) or {}
    user_phone = user.get("user_phone", "") or user.get("phone", "")
    send_notification = make_notification_tool(user_phone=user_phone, user_id=session_id)

    @tool
    def loan_verification_tool(user_message: str) -> str:
        """
        Verify the user's ID document.
        Pass the complete user message as-is to this tool.
        Returns 'YES' if verified.
        Used at step 'waiting_id' when the user submits their ID document.
        """
        return run_loan_verification_agent(user_message)

    tools = [
        get_session_data_tool,
        update_session_data_tool,
        send_whatsapp_message,
        send_notification,
        mongodb_user_updater,
        loan_verification_tool,
        check_loan_eligibility,
    ]

    agent = create_react_agent(
        model=get_sub_agent_llm(),
        tools=tools,
        prompt=LOAN_AGENT_PROMPT,
    )
    return agent


def run_loan_agent(
    user_input: str,
    user_data: Dict[str, Any],
    session_data: Dict[str, Any],
    current_communication_channel: str,
    session_id: str,
    identity: str,
) -> str:
    """
    Run the Loan Agent for one turn.

    Builds a stringified JSON context (matching how the Master passes data in Langflow)
    and invokes the agent.

    Returns the agent's plain-text response to send to the user.
    """
    context = json.dumps(
        {
            "user_input": user_input,
            "user_data": user_data,
            "session_data": session_data,
            "current_communication_channel": current_communication_channel,
        },
        default=str,
        ensure_ascii=False,
    )

    logger.info("[LoanAgent] Running for session=%s channel=%s", session_id, current_communication_channel)
    agent = build_loan_agent(session_id, identity)
    result = agent.invoke({"messages": [("human", context)]})
    response = result["messages"][-1].content
    logger.info("[LoanAgent] Response: %s", response[:200])
    return response


# ── Expose LoanAgent as a Tool for the Master Agent ───────────────────────────

def make_loan_agent_tool(session_id: str, identity: str, user_data: Dict, session_data: Dict, channel: str):
    """
    Factory: returns a LangChain @tool that wraps the LoanAgent.
    Mirrors 'Agent-iwpNN → component_as_tool → Agent-AvYMg' edge.
    """

    @tool
    def loan_agent_tool(input_json: str) -> str:
        """
        LoanAgent — handles the complete personal loan lifecycle:
        eligibility check, profile verification, disbursement, post-loan queries.

        Input: stringified JSON with keys:
          flow_tweak_data: {"ChatInput-XXXXX~input_value": "<STRINGIFIED_COMPLETE_INPUT>"}

        OR pass the full context JSON directly:
          {"user_input": "...", "user_data": {...}, "session_data": {...}, "current_communication_channel": "..."}

        Returns the agent's response as plain text — pass through to user immediately.
        """
        # Try to extract user_input from flow_tweak_data wrapper (Langflow compat)
        try:
            parsed = json.loads(input_json)
            if "flow_tweak_data" in parsed:
                inner = next(iter(parsed["flow_tweak_data"].values()), "{}")
                context_dict = json.loads(inner)
                actual_input = context_dict.get("user_input", input_json)
                sd = context_dict.get("session_data", session_data)
                ud = context_dict.get("user_data", user_data)
                ch = context_dict.get("current_communication_channel", channel)
            else:
                actual_input = parsed.get("user_input", input_json)
                sd = parsed.get("session_data", session_data)
                ud = parsed.get("user_data", user_data)
                ch = parsed.get("current_communication_channel", channel)
        except (json.JSONDecodeError, AttributeError):
            actual_input = input_json
            sd = session_data
            ud = user_data
            ch = channel

        return run_loan_agent(actual_input, ud, sd, ch, session_id, identity)

    return loan_agent_tool
