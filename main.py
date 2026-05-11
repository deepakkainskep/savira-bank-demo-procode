"""
main.py — Entry point for the Savira Multi-Agent System.
FastAPI REST server + interactive CLI.

Usage:
  uvicorn main:app --host 0.0.0.0 --port 8000
  python main.py   # CLI mode
"""

from __future__ import annotations
import logging
import sys
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Import graph (done at module level so uvicorn sees it properly) ────────────
from graph.savira_graph import savira_graph
from state import SaviraState

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app (top-level so uvicorn always finds it)
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Savira Multi-Agent Banking Assistant",
    description="LangGraph/LangChain procode — converted from Savira Langflow flow.",
    version="1.0.0",
)


# ─────────────────────────────────────────────────────────────────────────────
# Core runner  (mirrors ChatInput → graph → ChatOutput)
# ─────────────────────────────────────────────────────────────────────────────
def run_savira(
    user_input: str,
    session_id: str,
    identity: Optional[str] = None,
    channel: str = "chat",
) -> str:
    """
    Single-turn entry point.

    session_id   — conversation identifier; also used as users.user_id lookup key.
    identity     — optional email/phone fallback for user lookup.
    channel      — chat | whatsapp | email | call
    """
    initial_state: SaviraState = {
        "user_input":                   user_input,
        "session_id":                   session_id,
        "identity":                     identity or "",
        "current_communication_channel": channel,
        "user_data":                    None,
        "session_data":                 None,
        "detected_intent":              None,
        "routed_to":                    None,
        "agent_response":               None,
        "final_response":               None,
        "error":                        None,
        "conversation_history":         None,
    }

    logger.info(
        "[run_savira] session=%s channel=%s input=%.80s",
        session_id, channel, user_input,
    )

    final_state = savira_graph.invoke(initial_state)
    response = (
        final_state.get("final_response")
        or "I'm sorry, I couldn't process your request."
    )

    logger.info("[run_savira] response=%.100s", response)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    # Accept both 'user_input' and 'message' (alias) — either works
    user_input: Optional[str] = None
    message:    Optional[str] = None   # alias for user_input
    session_id: Optional[str] = None
    identity:   Optional[str] = None   # optional: email or phone
                                        # primary key is session_id = users.user_id
    channel:    str = "chat"

    def get_input(self) -> str:
        """Return whichever of user_input / message was provided."""
        return (self.user_input or self.message or "").strip()


class ChatResponse(BaseModel):
    session_id: str
    response:   str


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "savira-procode"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Process one chat turn.

    Accepts either field name:
      { "user_input": "...", ... }   (original format)
      { "message":    "...", ... }   (alternative alias)

    - session_id: auto-generated if not provided.
    - identity:   optional email/phone — primary key is session_id = users.user_id.
    - channel:    chat | whatsapp | email | call
    """
    sid        = request.session_id or str(uuid.uuid4())
    user_input = request.get_input()

    if not user_input:
        raise HTTPException(status_code=422, detail="'user_input' or 'message' field is required")

    try:
        response = run_savira(
            user_input=user_input,
            session_id=sid,
            identity=request.identity,
            channel=request.channel,
        )
    except Exception as exc:
        logger.error("[/chat] Unhandled error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return ChatResponse(session_id=sid, response=response)


# ─────────────────────────────────────────────────────────────────────────────
# Interactive CLI  (python main.py)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Savira Multi-Agent Banking Assistant — CLI Mode")
    print("=" * 60)

    session_id = input("Session ID (press Enter for new): ").strip() or str(uuid.uuid4())
    identity   = input("Identity (email/phone, optional): ").strip() or None
    channel    = input("Channel [chat/whatsapp/email/call] (default=chat): ").strip() or "chat"

    print(f"\nSession ID : {session_id}")
    print(f"Channel    : {channel}")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        response = run_savira(
            user_input=user_input,
            session_id=session_id,
            identity=identity,
            channel=channel,
        )
        print(f"\nSavira: {response}\n")
