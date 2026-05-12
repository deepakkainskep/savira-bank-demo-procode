import streamlit as st
import requests
import sys
import os

# Ensure we can import from db
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.mongo_client import get_db, retrieve_messages
from config import MONGO_COLLECTION_USERS

API_URL = "http://localhost:7071/chat"

st.set_page_config(page_title="Savira Banking Assistant", page_icon="🏦", layout="centered")

st.title("🏦 Savira Banking Assistant")

# --- Session State Management ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def lookup_user_by_phone(phone: str):
    """Fetch user from MongoDB using user_phone."""
    db = get_db()
    user = db[MONGO_COLLECTION_USERS].find_one({
        "$or": [{"user_phone": phone}, {"phone": phone}]
    })
    return user

# --- Login Screen ---
if not st.session_state.logged_in:
    st.subheader("Login to your account")
    st.write("Enter your registered phone number to load your profile and session.")
    
    phone_input = st.text_input("Phone number (e.g., 919376072346):")
    
    if st.button("Login", type="primary"):
        if phone_input:
            user = lookup_user_by_phone(phone_input.strip())
            if user:
                # IMPORTANT: We use user_id as the session_id so flow persistence works!
                uid = user.get("user_id")
                st.session_state.user_id = uid
                st.session_state.user_name = user.get("user_name", "Customer")
                st.session_state.logged_in = True
                
                # Fetch existing chat history from MongoDB
                history = retrieve_messages(uid, limit=50)
                st.session_state.messages = []
                for msg in history:
                    role = "user" if msg["role"] == "HUMAN" else "assistant"
                    st.session_state.messages.append({"role": role, "content": msg["content"]})
                
                st.rerun()
            else:
                st.error(f"No user found with phone number: {phone_input}. Please check the database.")
        else:
            st.warning("Please enter a phone number.")
            
    st.markdown("---")
    st.markdown("*Note: Make sure your FastAPI server is running on port 9000 (`uvicorn main:app --port 9000`)*")
    st.stop()


# --- Main Chat Interface ---
col1, col2 = st.columns([4, 1])
with col1:
    st.success(f"Welcome back, **{st.session_state.user_name}**!")
with col2:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.messages = []
        st.rerun()

st.caption(f"User ID: `{st.session_state.user_id}`")
st.markdown("---")

# 1. Display chat messages from state
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. Accept user input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat state & display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call FastAPI backend
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Savira is thinking...)*")
        
        try:
            payload = {
                "message": prompt,
                "session_id": st.session_state.user_id, # Link session_id to user_id
                "channel": "chat"
            }
            response = requests.post(API_URL, json=payload, timeout=120)
            
            if response.status_code == 200:
                data = response.json()
                bot_reply = data.get("response", "")
                message_placeholder.markdown(bot_reply)
                # Add to state
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            else:
                try:
                    err = response.json()
                except:
                    err = response.text
                error_msg = f"**Error {response.status_code}:** {err}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
        except Exception as e:
            error_msg = f"**Failed to connect to Savira server:**\n`{e}`"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
