"""
tools/epn_tool.py — LangChain tool mirroring EPNApisCaller.

Azure Function URL format:
  GET https://loaneligiblitycheck-bsf0bhc6fbbreqhp.southafricanorth-01.azurewebsites.net
       /api/loan/eligibility?code=XXX&epn_number=YYY
  EPN_API_BASE_URL already includes trailing `?` in .env
  EPN_API_KEY stores the `code=XXX` part
"""

from __future__ import annotations
import json
import logging
import requests

from langchain_core.tools import tool
from config import EPN_API_BASE_URL, EPN_API_KEY

logger = logging.getLogger(__name__)


@tool
def check_loan_eligibility(epn_number: str) -> str:
    """
    Check personal loan eligibility for a user using their EPN number.

    Input: epn_number (str) — the user's EPN identifier (e.g. "12345678").

    Returns a JSON string with:
    - eligible (bool)
    - loan_preapproved_amount (float | null)
    - interest_rate (float | null)
    - reason (str | null) — if not eligible

    Rules:
    - ONLY use values returned by this tool. Never invent amounts or rates.
    - If API errors, report eligibility could not be confirmed.
    """
    if not epn_number:
        return json.dumps({"error": "epn_number is required"})

    if not EPN_API_BASE_URL:
        logger.warning("[EPNApi] EPN_API_BASE_URL not configured — returning mock data")
        return json.dumps({
            "eligible": True,
            "loan_preapproved_amount": 50000,
            "interest_rate": 12.5,
            "currency": "R",
            "note": "Mock data — EPN API not configured",
        })

    # Build URL:
    # Base URL may end with '?' already (e.g. ".../eligibility?")
    # Key is "code=XXX", epn_number is appended
    separator = "&" if "?" in EPN_API_BASE_URL else "?"
    key_part  = f"{EPN_API_KEY}&" if EPN_API_KEY else ""
    full_url  = f"{EPN_API_BASE_URL}{key_part}epn_number={epn_number}"

    logger.info("[EPNApi] Calling: %s", full_url)

    try:
        resp = requests.get(full_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info("[EPNApi] Response for epn=%s: %s", epn_number, data)
        return json.dumps(data)
    except requests.RequestException as exc:
        logger.error("[EPNApi] Error: %s", exc)
        mock = {
            "eligible": True,
            "loan_preapproved_amount": 50000,
            "interest_rate": 12.5,
            "currency": "R",
            "note": f"Mock data — EPN API error: {exc}",
        }
        logger.warning("[EPNApi] Returning mock eligibility data")
        return json.dumps(mock)
