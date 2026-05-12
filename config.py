"""
config.py — Central configuration for Savira Multi-Agent System
All credentials and settings are loaded from .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Server & Distributed Agents ───────────────────────────────────────────────
SERVER_PORT              = int(os.getenv("SERVER_PORT", "9000"))   # Use 9000 (8000 is reserved by other services)

# Detection for Azure Environment to auto-construct Agent URLs
hostname = os.getenv("WEBSITE_HOSTNAME")
base_url = f"https://{hostname}" if hostname else f"http://localhost:{SERVER_PORT}"

LOAN_AGENT_URL           = os.getenv("LOAN_AGENT_URL") or f"{base_url}/agent/loan"
CARD_BLOCK_AGENT_URL     = os.getenv("CARD_BLOCK_AGENT_URL") or f"{base_url}/agent/card_block"

# ─── Azure OpenAI ────────────────────────────────────────────────────────────
AZURE_OPENAI_API_KEY     = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT    = os.getenv("AZURE_OPENAI_ENDPOINT", "https://saviragenai.openai.azure.com/")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_DEPLOYMENT  = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

# ─── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_CONNECTION_STRING  = os.getenv(
    "MONGO_CONNECTION_STRING",
    "mongodb://admin:WorKBench%40PwC%401221@4.221.107.123:27017/"
)
MONGO_DATABASE           = os.getenv("MONGO_DATABASE", "chat_history_demo")
MONGO_COLLECTION_HISTORY = os.getenv("MONGO_COLLECTION_HISTORY", "old_chats")
MONGO_COLLECTION_SESSION = os.getenv("MONGO_COLLECTION_SESSION", "session_states")
MONGO_COLLECTION_USERS   = os.getenv("MONGO_COLLECTION_USERS", "users")

# ─── EPN API ─────────────────────────────────────────────────────────────────
# Full URL format: https://...azurewebsites.net/api/loan/eligibility?code=XXX
# The EPN_API_KEY stores just the query-string part: ?code=XXX
EPN_API_BASE_URL         = os.getenv("EPN_API_BASE_URL", "")
EPN_API_KEY              = os.getenv("EPN_API_KEY", "")   # e.g. code=oee_inq...

# ─── WhatsApp Tool ──────────────────────────────────────────────────────────
# Full URL: https://wappdemo-fncapp.azurewebsites.net/api/message/send
# The WHATSAPP_API_KEY stores the query-string auth: ?code=XXX
WHATSAPP_API_URL         = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_API_KEY         = os.getenv("WHATSAPP_API_KEY", "")   # e.g. ?code=n98ze...

# ─── Notification / Push ─────────────────────────────────────────────────────
# Full URL: https://wappdemo-fncapp.azurewebsites.net/api/notification/send
NOTIFICATION_API_URL     = os.getenv("NOTIFICATION_API_URL", "")
NOTIFICATION_API_KEY     = os.getenv("NOTIFICATION_API_KEY", "")   # e.g. ?code=rIert9...

# ─── General ─────────────────────────────────────────────────────────────────
DEFAULT_CHANNEL          = os.getenv("DEFAULT_CHANNEL", "chat")
LOG_LEVEL                = os.getenv("LOG_LEVEL", "INFO")
