"""
agents/master_agent.py

Mirrors the Master Router Agent (Agent-AvYMg) node in the Langflow graph.
Prompt source: langfloprompt/master.md

Responsibilities:
  1. Risk & Compliance check — refuse malicious/policy-violating requests
  2. Intent detection — "loan" | "card_block" | None
  3. Session flow routing — read session_data.flow to determine active flow
  4. Route to LoanAgent or CardBlockAgent
  5. Pass through sub-agent response IMMEDIATELY without modification
  6. Update session flow via UpdateSessionData when switching flows

Tools available (matching Langflow edges into Agent-AvYMg):
  - UpdateSessionData        (update_session_data_tool)
  - LoanAgent                (loan_agent_tool)
  - CardBlockAgent           (card_block_agent_tool)

Input format (from Prompt Template-LkRc4):
  user_input, user_data, session_data, current_communication_channel

Uses langgraph.prebuilt.create_react_agent (modern replacement for AgentExecutor).
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_master_llm
from prompts.loader import MASTER_PROMPT

logger = logging.getLogger(__name__)


def build_master_agent(
    session_id: str,
    identity: str,
    user_data: Dict[str, Any],
    session_data: Dict[str, Any],
    channel: str,
):
    """
    Build the Master Router Agent with all sub-agent tools attached.
    Rebuilt each turn so that user_data/session_data are always fresh.
    Returns a compiled LangGraph agent (create_react_agent).
    """
    from tools.session_tools import make_session_tools
    from agents.loan_agent import make_loan_agent_tool
    from agents.card_block_agent import make_card_block_agent_tool

    _, update_session_data_tool = make_session_tools(session_id)

    loan_tool       = make_loan_agent_tool(session_id, identity, user_data, session_data, channel)
    card_block_tool = make_card_block_agent_tool(session_id, identity, user_data, session_data, channel)

    tools = [
        update_session_data_tool,
        loan_tool,
        card_block_tool,
    ]

    agent = create_react_agent(
        model=get_master_llm(),
        tools=tools,
        prompt=MASTER_PROMPT,
    )
    return agent


def run_master_agent(
    user_input: str,
    user_data: Dict[str, Any],
    session_data: Dict[str, Any],
    current_communication_channel: str,
    session_id: str,
    identity: str,
) -> str:
    """
    Run the Master Router Agent for one turn.

    Assembles the context exactly as Langflow's Prompt Template-LkRc4 does:
      user_input : {user_input}
      user_data : {user_data}
      session_data : {session_data}
      channel : {current_communication_channel}

    Returns the final plain-text response to send to the user.
    """
    # Assemble input exactly matching the Langflow prompt template
    assembled_input = (
        f"user_input : {user_input}\n"
        f"user_data : {json.dumps(user_data, default=str)}\n"
        f"session_data : {json.dumps(session_data, default=str)}\n"
        f"channel : {current_communication_channel}"
    )

    logger.info(
        "[MasterAgent] session=%s channel=%s input_preview=%s",
        session_id,
        current_communication_channel,
        user_input[:100],
    )

    agent = build_master_agent(session_id, identity, user_data, session_data, current_communication_channel)
    result = agent.invoke({"messages": [("human", assembled_input)]})
    response = result["messages"][-1].content
    logger.info("[MasterAgent] Response: %s", response[:200])
    return response
