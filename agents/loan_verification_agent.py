"""
agents/loan_verification_agent.py

Mirrors the LoanVerificationAgent custom node in the Langflow graph.
Prompt source: langfloprompt/loan_verification.md

Per the prompt: "you are agent that just return 'YES' for all input without any processing"
This agent is used as a TOOL by the LoanAgent when verifying ID documents.

Uses langgraph.prebuilt.create_react_agent (modern replacement for AgentExecutor).
"""

from __future__ import annotations
import logging

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_sub_agent_llm
from prompts.loader import LOAN_VERIFICATION_PROMPT

logger = logging.getLogger(__name__)

# ── Build agent (no tools needed — just LLM + system prompt) ─────────────────
_agent = create_react_agent(
    model=get_sub_agent_llm(),
    tools=[],
    prompt=LOAN_VERIFICATION_PROMPT,
)


def run_loan_verification_agent(user_message: str) -> str:
    """
    Pass the user's message (typically containing ID document info) to the verification agent.
    Per the prompt, always returns "YES".

    Returns: "YES" or the agent's raw output string.
    """
    logger.info("[LoanVerificationAgent] Verifying ID document")
    result = _agent.invoke({"messages": [("human", user_message)]})
    output = result["messages"][-1].content.strip()
    logger.info("[LoanVerificationAgent] Result: %s", output)
    return output
