"""
agents/card_block_agent.py

Mirrors the CardBlockAgent (Agent-w5vyh) node in the Langflow graph.
Prompt source: langfloprompt/cardb.md

Card blocking 4-step flow:
  WAITING_CVV → WAITING_REASON → WAITING_CONFIRMATION → COMPLETED

Tools available (matching Langflow edges into Agent-w5vyh):
  - UpdateSessionData       (update_session_data_tool)
  - MongoDBUserUpdater      (mongodb_user_updater)

Uses langgraph.prebuilt.create_react_agent (modern replacement for AgentExecutor).
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from agents.llm_factory import get_sub_agent_llm
from prompts.loader import CARD_BLOCK_AGENT_PROMPT

logger = logging.getLogger(__name__)


def build_card_block_agent(session_id: str, identity: str):
    """
    Build a CardBlockAgent with tools bound to the current session/user.
    Returns a compiled LangGraph agent (create_react_agent).
    """
    from tools.session_tools import make_session_tools
    from tools.mongo_user_updater_tool import make_user_updater_tool

    get_session_data_tool, update_session_data_tool = make_session_tools(session_id)
    mongodb_user_updater = make_user_updater_tool(session_id=session_id, identity=identity)

    tools = [
        get_session_data_tool,
        update_session_data_tool,
        mongodb_user_updater,
    ]

    agent = create_react_agent(
        model=get_sub_agent_llm(),
        tools=tools,
        prompt=CARD_BLOCK_AGENT_PROMPT,
    )
    return agent


def run_card_block_agent(
    user_input: str,
    user_data: Dict[str, Any],
    session_data: Dict[str, Any],
    current_communication_channel: str,
    session_id: str,
    identity: str,
) -> str:
    """
    Run the Card Block Agent for one turn.

    Builds a stringified JSON context and invokes the agent.
    Returns the agent's plain-text response.
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

    logger.info("[CardBlockAgent] Running for session=%s", session_id)
    agent = build_card_block_agent(session_id, identity)
    result = agent.invoke({"messages": [("human", context)]})
    response = result["messages"][-1].content
    logger.info("[CardBlockAgent] Response: %s", response[:200])
    return response


# ── Expose CardBlockAgent as a Tool for the Master Agent ──────────────────────

def make_card_block_agent_tool(
    session_id: str,
    identity: str,
    user_data: Dict,
    session_data: Dict,
    channel: str,
):
    """
    Factory: returns a LangChain @tool that wraps the CardBlockAgent.
    Mirrors 'Agent-w5vyh → component_as_tool → Agent-AvYMg' edge.
    """

    @tool
    def card_block_agent_tool(input_json: str) -> str:
        """
        CardBlockAgent — handles debit card blocking in 4 steps:
        CVV verification → reason collection → confirmation → completion.

        Input: stringified JSON with keys:
          flow_tweak_data: {"ChatInput-XXXXX~input_value": "<STRINGIFIED_COMPLETE_INPUT>"}

        OR pass the full context JSON directly:
          {"user_input": "...", "user_data": {...}, "session_data": {...}, "current_communication_channel": "..."}

        Returns the agent's response as plain text — pass through to user immediately.
        NEVER re-process the agent's response.
        """
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

        return run_card_block_agent(actual_input, ud, sd, ch, session_id, identity)

    return card_block_agent_tool
