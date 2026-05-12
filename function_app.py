from __future__ import annotations

import azure.functions as func
import json
import logging
import sys
import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Imports from your modules
from db.mongo_client import fetch_user, get_session_data, store_message
from agents.master_agent import run_master_agent
from agents.loan_agent import run_loan_agent
from agents.card_block_agent import run_card_block_agent

# ── Orchestrator Logic ────────────────────────────────────────────────────────
def run_orchestrator(
    user_input: str,
    session_id: str,
    identity: Optional[str] = None,
    channel: str = "chat",
) -> str:
    user_data = fetch_user(session_id, identity) or {}
    session_data = get_session_data(session_id)

    response = run_master_agent(
        user_input=user_input,
        user_data=user_data,
        session_data=session_data,
        current_communication_channel=channel,
        session_id=session_id,
        identity=identity or ""
    )

    store_message(session_id, user_input, "human", channel)
    store_message(session_id, response, "ai", channel)
    return response

# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    user_input: Optional[str] = None
    message:    Optional[str] = None
    session_id: Optional[str] = None
    identity:   Optional[str] = None
    channel:    str = "chat"

    def get_input(self) -> str:
        return (self.user_input or self.message or "").strip()

class ChatResponse(BaseModel):
    session_id: str
    response:   str

class AgentRequest(BaseModel):
    session_id: str
    identity: str
    user_input: str
    channel: str

# ─────────────────────────────────────────────────────────────────────────────
# Azure Functions (explicit routes so each shows as a separate Function)
# ─────────────────────────────────────────────────────────────────────────────
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _json_response(payload: Dict[str, Any], status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload),
        status_code=status_code,
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _json_response({"status": "ok", "service": "savira-procode-microservices"})


@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "Invalid JSON body"}, status_code=400)

    request = ChatRequest(**body)
    sid = request.session_id or str(uuid.uuid4())
    user_input = request.get_input()

    if not user_input:
        return _json_response({"error": "'user_input' or 'message' field is required"}, status_code=422)

    try:
        response = run_orchestrator(
            user_input=user_input,
            session_id=sid,
            identity=request.identity,
            channel=request.channel,
        )
        return _json_response(ChatResponse(session_id=sid, response=response).model_dump())
    except Exception as exc:
        logger.exception("Error during chat processing")
        return _json_response({"error": str(exc)}, status_code=500)


@app.route(route="agent/loan", methods=["POST"])
def agent_loan(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "Invalid JSON body"}, status_code=400)

    request = AgentRequest(**body)
    user_data = fetch_user(request.session_id, request.identity) or {}
    session_data = get_session_data(request.session_id)
    response = run_loan_agent(
        request.user_input,
        user_data,
        session_data,
        request.channel,
        request.session_id,
        request.identity,
    )
    return _json_response({"response": response})


@app.route(route="agent/card_block", methods=["POST"])
def agent_card_block(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "Invalid JSON body"}, status_code=400)

    request = AgentRequest(**body)
    user_data = fetch_user(request.session_id, request.identity) or {}
    session_data = get_session_data(request.session_id)
    response = run_card_block_agent(
        request.user_input,
        user_data,
        session_data,
        request.channel,
        request.session_id,
        request.identity,
    )
    return _json_response({"response": response})
