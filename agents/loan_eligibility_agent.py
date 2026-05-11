"""
agents/loan_eligibility_agent.py

Mirrors the LoanVerificationAgent (LoanAgent-5UBnk) sub-agent in the Langflow graph.
Prompt source: langfloprompt/loan_eligibility.md

Responsibility:
  - Call EPNApisCaller tool with the user's epn_number
  - Return structured eligibility values: loan_preapproved_amount, interest_rate
  - NEVER invent values; only use tool-returned data

Uses langgraph.prebuilt.create_react_agent (modern replacement for AgentExecutor).
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict

from langgraph.prebuilt import create_react_agent

from agents.llm_factory import get_sub_agent_llm
from tools.epn_tool import check_loan_eligibility
from prompts.loader import LOAN_ELIGIBILITY_PROMPT

logger = logging.getLogger(__name__)

# ── Build agent ───────────────────────────────────────────────────────────────
_TOOLS = [check_loan_eligibility]

_agent = create_react_agent(
    model=get_sub_agent_llm(),
    tools=_TOOLS,
    prompt=LOAN_ELIGIBILITY_PROMPT,
)


def run_loan_eligibility_agent(epn_number: str) -> Dict[str, Any]:
    """
    Check loan eligibility for a user.

    Returns dict with:
    - eligible (bool)
    - loan_preapproved_amount (float | None)
    - interest_rate (float | None)
    - raw_response (str)
    """
    logger.info("[LoanEligibilityAgent] Checking eligibility for epn=%s", epn_number)
    result = _agent.invoke({"messages": [("human", epn_number)]})
    raw = result["messages"][-1].content

    # Try to parse structured JSON from response
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        data = {
            "eligible": None,
            "loan_preapproved_amount": None,
            "interest_rate": None,
            "raw_response": raw,
        }

    logger.info("[LoanEligibilityAgent] Result: %s", data)
    return data
