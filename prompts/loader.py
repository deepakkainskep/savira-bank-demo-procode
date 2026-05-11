"""
prompts/loader.py — Loads prompt text from the local prompts/ folder.
All .md files are stored directly inside savira_procode/prompts/
"""

from __future__ import annotations
import os

# prompts/ folder is the same directory as this file
_PROMPT_DIR = os.path.dirname(os.path.abspath(__file__))

_CACHE: dict[str, str] = {}


def load_prompt(name: str) -> str:
    """
    Load a prompt by filename (without extension) from the prompts/ directory.
    E.g., load_prompt("master") reads prompts/master.md
    Results are cached in memory.
    """
    if name in _CACHE:
        return _CACHE[name]
    path = os.path.join(_PROMPT_DIR, f"{name}.md")
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    _CACHE[name] = content
    return content


# ── Pre-load all prompts at import time ─────────────────────────────────────
MASTER_PROMPT            = load_prompt("master")
LOAN_AGENT_PROMPT        = load_prompt("loan")
CARD_BLOCK_AGENT_PROMPT  = load_prompt("cardb")
LOAN_ELIGIBILITY_PROMPT  = load_prompt("loan_eligibility")
LOAN_VERIFICATION_PROMPT = load_prompt("loan_verification")
