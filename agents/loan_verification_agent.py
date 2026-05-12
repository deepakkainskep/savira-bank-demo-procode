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

# ── Lazy agent singleton ───────────────────────────────────────────────────────
# Do NOT build the agent at module level — Azure Functions may import this
# before environment variables are injected, causing LLM auth failures on
# cold start. The singleton is created on first actual invocation instead.
_agent = None


def _get_agent():
    """Return the cached agent, building it on first call (lazy init)."""
    global _agent
    if _agent is None:
        _agent = create_react_agent(
            model=get_sub_agent_llm(),
            tools=[],
            prompt=LOAN_VERIFICATION_PROMPT,
        )
    return _agent


def run_loan_verification_agent(user_message: str) -> str:
    """
    Pass the user's message (typically containing ID document info) to the verification agent.
    Per the prompt, always returns "YES".

    Returns: "YES" or the agent's raw output string.
    """
    logger.info("[LoanVerificationAgent] Verifying ID document")
    result = _get_agent().invoke({"messages": [("human", user_message)]})
    output = result["messages"][-1].content.strip()
    logger.info("[LoanVerificationAgent] Result: %s", output)
    return output
