"""
state.py — LangGraph shared state schema for the Savira multi-agent system.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


# ─── Card-Block sub-state ─────────────────────────────────────────────────────
class CardBlockState(TypedDict, total=False):
    current_step: str           # WAITING_CVV | WAITING_REASON | WAITING_CONFIRMATION | COMPLETED
    cvv_verified: bool
    block_reason: Optional[str] # "lost" | "stolen" | null
    confirmation: Optional[bool]


# ─── Loan sub-state ──────────────────────────────────────────────────────────
class LoanState(TypedDict, total=False):
    loan_state: str             # start | eligibility_check | profile_verification | loan_disbursement | disbursed
    step: Optional[str]
    last_channel: Optional[str]
    loan_preapproved_amount: Optional[Any]
    interest_rate: Optional[Any]
    loan_amount_requested: Optional[Any]
    profile_verified: Optional[bool]
    tnc_accepted: Optional[bool]
    id_verified: Optional[bool]
    debit_approved: Optional[bool]
    requested_document: Optional[str]
    document_status: Optional[str]
    document_url: Optional[str]


# ─── Session data (persisted in MongoDB sessions collection) ──────────────────
class SessionData(TypedDict, total=False):
    flow: Optional[str]                     # "loan" | "card_block" | None
    card_block: Optional[CardBlockState]
    # loan fields are stored flat in session (mirrors Langflow UpdateSessionData)
    loan_state: Optional[str]
    step: Optional[str]
    last_channel: Optional[str]
    loan_preapproved_amount: Optional[Any]
    interest_rate: Optional[Any]
    loan_amount_requested: Optional[Any]
    profile_verified: Optional[bool]
    tnc_accepted: Optional[bool]
    id_verified: Optional[bool]
    debit_approved: Optional[bool]
    requested_document: Optional[str]
    document_status: Optional[str]
    document_url: Optional[str]


# ─── User profile (fetched from MongoDB users collection) ─────────────────────
class UserData(TypedDict, total=False):
    _id: Any
    name: str
    email: str
    phone: str
    address: str
    occupation: str
    epn_number: str
    account_balance: float
    is_active: bool
    debit_card_status: str          # "ACTIVE" | "BLOCKED"
    debit_card_cvv: str             # 3-digit string
    loan_preapproved_amount: Optional[Any]
    interest_rate: Optional[Any]


# ─── Master graph state ───────────────────────────────────────────────────────
class SaviraState(TypedDict, total=False):
    # ── Inputs ──────────────────────────────────────────────────────────────
    user_input: str
    session_id: str
    current_communication_channel: str         # "chat" | "whatsapp" | "email" | "call"
    identity: Optional[str]                    # email or phone for user lookup

    # ── Resolved data ────────────────────────────────────────────────────────
    user_data: Optional[UserData]
    session_data: Optional[SessionData]

    # ── Routing ──────────────────────────────────────────────────────────────
    detected_intent: Optional[str]             # "loan" | "card_block" | None
    routed_to: Optional[str]                   # "LoanAgent" | "CardBlockAgent"

    # ── Agent outputs ────────────────────────────────────────────────────────
    agent_response: Optional[str]
    final_response: Optional[str]

    # ── Error ────────────────────────────────────────────────────────────────
    error: Optional[str]

    # ── Conversation history (retrieved from MongoDB) ─────────────────────────
    conversation_history: Optional[List[Dict[str, Any]]]
