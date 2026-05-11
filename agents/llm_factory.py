"""
agents/llm_factory.py — Shared Azure OpenAI LLM instances.
Mirrors the two AzureOpenAI model nodes in the Langflow graph:
  - AzureOpenAIModel-Dkml1  (used by Master Agent, temperature=0)
  - AzureOpenAIModel-t6Mi5  (used by LoanAgent, CardBlockAgent, LoanVerification, temperature=0)
"""

from __future__ import annotations
from functools import lru_cache

from langchain_openai import AzureChatOpenAI
from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
)


@lru_cache(maxsize=None)
def get_master_llm() -> AzureChatOpenAI:
    """
    LLM for the Master Router Agent (AzureOpenAIModel-Dkml1).
    Temperature 0 for deterministic routing.
    """
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=0,
        streaming=False,
    )


@lru_cache(maxsize=None)
def get_sub_agent_llm() -> AzureChatOpenAI:
    """
    LLM for sub-agents: LoanAgent, CardBlockAgent, LoanEligibilityAgent,
    LoanVerificationAgent (AzureOpenAIModel-t6Mi5).
    Temperature 0.05 as specified in cardb.md, 0 for loan agents.
    """
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=0.05,
        streaming=False,
    )
