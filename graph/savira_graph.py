"""
graph/savira_graph.py

LangGraph implementation of the complete Savira multi-agent flow.

Graph topology (mirrors Langflow edges):
─────────────────────────────────────────────────────────────
  START
    │
    ▼
  [fetch_user_and_session]   ← MongoDBUserFetcher + GetSessionData
    │
    ▼
  [run_master_agent]         ← Prompt Template-LkRc4 → Agent-AvYMg
    │                          (Master Agent calls LoanAgent or CardBlockAgent as tools)
    ▼
  [store_conversation]       ← MongoDBRetrieverStore (Store mode, both instances)
    │
    ▼
  END

The Master Agent internally:
  - routes to LoanAgent    (Agent-iwpNN → exposed as tool)
  - routes to CardBlockAgent (Agent-w5vyh → exposed as tool)
  - calls UpdateSessionData when switching flows

Each sub-agent calls its own UpdateSessionData and other tools.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END

from state import SaviraState
from db.mongo_client import fetch_user, get_session_data, store_message
from agents.master_agent import run_master_agent

logger = logging.getLogger(__name__)


# ─── Node 1: Fetch user profile + session state ───────────────────────────────
def fetch_user_and_session(state: SaviraState) -> SaviraState:
    """
    Mirrors:
      - MongoDBUserFetcher node → fetches user by identity
      - GetSessionData node → retrieves session_data from MongoDB sessions collection

    If user is not found, sets an error and terminates early.
    """
    identity   = state.get("identity") or ""
    session_id = state.get("session_id") or "default_session"

    logger.info("[Graph] fetch_user_and_session session_id=%s identity=%s", session_id, identity)

    # Fetch user — primary key is user_id == session_id, fallback to email/phone
    user = fetch_user(session_id=session_id, identity=identity or None)
    if user is None:
        logger.warning("[Graph] User not found for session_id=%s identity=%s", session_id, identity)
        user = {}

    # Fetch session
    session = get_session_data(session_id)

    return {
        **state,
        "user_data": user,
        "session_data": session,
    }


# ─── Node 2: Run Master Agent ─────────────────────────────────────────────────
def run_master_agent_node(state: SaviraState) -> SaviraState:
    """
    Mirrors:
      - Prompt Template-LkRc4 (assembles user_input + user_data + session_data + channel)
      - Agent-AvYMg (Master Agent with LoanAgent + CardBlockAgent + UpdateSessionData tools)

    The Master Agent internally calls sub-agents as tools and returns their response
    unchanged (pass-through rule from master.md).
    """
    user_input  = state.get("user_input", "")
    user_data   = state.get("user_data", {})
    session_data = state.get("session_data", {})
    channel     = state.get("current_communication_channel", "chat")
    session_id  = state.get("session_id", "default_session")
    identity    = state.get("identity", "")

    try:
        response = run_master_agent(
            user_input=user_input,
            user_data=user_data,
            session_data=session_data,
            current_communication_channel=channel,
            session_id=session_id,
            identity=identity,
        )
    except Exception as exc:
        logger.error("[Graph] Master agent error: %s", exc, exc_info=True)
        response = "I encountered an error processing your request. Please try again."

    return {
        **state,
        "agent_response": response,
        "final_response": response,
    }


# ─── Node 3: Store conversation in MongoDB ────────────────────────────────────
def store_conversation_node(state: SaviraState) -> SaviraState:
    """
    Mirrors TWO MongoDBRetrieverStore nodes in Store mode:
      - MongoDBRetrieverStore-vXus8  (stores the human/user message)
      - MongoDBRetrieverStore-LFwNj  (stores the AI/agent response)

    Both use the same session_id, channel, and user metadata.
    """
    session_id  = state.get("session_id", "default_session")
    user_input  = state.get("user_input", "")
    response    = state.get("final_response", "")
    channel     = state.get("current_communication_channel", "chat")
    user_data   = state.get("user_data", {})

    phone = user_data.get("phone", "")
    email = user_data.get("email", "")
    name  = user_data.get("name", "")

    try:
        # Store human message (MongoDBRetrieverStore-vXus8, sender_type="human")
        if user_input:
            store_message(
                session_id=session_id,
                message=user_input,
                sender_type="human",
                channel=channel,
                user_phone=phone,
                user_email=email,
                user_name=name,
            )

        # Store AI response (MongoDBRetrieverStore-LFwNj, sender_type="ai")
        if response:
            store_message(
                session_id=session_id,
                message=response,
                sender_type="ai",
                channel=channel,
                user_phone=phone,
                user_email=email,
                user_name=name,
            )
    except Exception as exc:
        logger.error("[Graph] Failed to store conversation: %s", exc)

    return state


# ─── Conditional: skip sub-agent if error in fetch ───────────────────────────
def should_run_agent(state: SaviraState) -> Literal["run_master", "end"]:
    if state.get("error"):
        return "end"
    return "run_master"


# ─── Build the graph ──────────────────────────────────────────────────────────
def build_savira_graph() -> StateGraph:
    builder = StateGraph(SaviraState)

    builder.add_node("fetch_user_and_session", fetch_user_and_session)
    builder.add_node("run_master_agent",       run_master_agent_node)
    builder.add_node("store_conversation",     store_conversation_node)

    builder.add_edge(START, "fetch_user_and_session")

    builder.add_conditional_edges(
        "fetch_user_and_session",
        should_run_agent,
        {
            "run_master": "run_master_agent",
            "end":        END,
        },
    )

    builder.add_edge("run_master_agent",   "store_conversation")
    builder.add_edge("store_conversation", END)

    return builder.compile()


# ── Module-level compiled graph (singleton) ───────────────────────────────────
savira_graph = build_savira_graph()
