import datetime
import streamlit as st
from typing import Dict
import streamlit.components.v1 as components
from streamlit_modal import Modal
from utils import (
    handle_api_error,
    api_get_sessions,
    api_create_session,
    api_get_messages,
    api_create_message,
    api_get_citation,
    api_get_docs,
    get_model_name_from_message,
    format_text_with_citations
)

# --- Page Setup ---
st.set_page_config(
    layout="centered",
    page_title="Chatbot Germano",
    page_icon="🤖",
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': "https://www.example.com/bug",
        'About': "# Streamlit Chat with FastAPI Backend!"
    },
)

# --- Load CSS ---
def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Backend URL Configuration ---
BACKEND_URL = st.secrets.get("API_URL", "http://localhost:8000").strip()
if not BACKEND_URL.startswith(("http://", "https://")):
    BACKEND_URL = "http://" + BACKEND_URL
st.query_params = {"debug_backend": BACKEND_URL}

import utils
utils.BACKEND_URL = BACKEND_URL

# --- Initialization ---
def initialize_app():
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {"name": "User", "avatar": "👤"}
    if "chat_sessions" not in st.session_state:
        sessions = api_get_sessions()
        st.session_state.chat_sessions = {s['id']: s for s in sessions} if sessions else {}
    for key in ["current_chat_id", "messages", "show_citation_id", "documents_cache"]:
        if key not in st.session_state:
            st.session_state[key] = None if "id" in key else [] if key == "messages" else {}
    return Modal(title="Citation Details", key="citation-modal", padding=20, max_width=700)

# --- Sidebar ---
def render_sidebar():
    with st.sidebar:
        cols = st.columns([0.6, 0.15, 0.05, 0.15, 0.05])
        if cols[0].button("Settings", key="settings_btn"):
            st.toast("Settings clicked (placeholder)")
        if cols[1].button(st.session_state.user_profile['avatar'], key="profile_btn"):
            st.toast("User profile clicked (placeholder)")
        if cols[3].button("➕", key="new_chat_btn"):
            create_new_chat()

        st.divider()
        st.header("Chat Sessions", divider=False)

        if not st.session_state.chat_sessions:
            st.caption("No chats yet. Click ➕ to start!")
        else:
            with st.container(height=300, border=True):
                for chat_id in st.session_state.chat_sessions:
                    chat = st.session_state.chat_sessions[chat_id]
                    title = chat.get('title', f"Chat {chat_id[:6]}")
                    btn_type = "primary" if chat_id == st.session_state.current_chat_id else "secondary"
                    if st.button(f"💬 {title[:30]}", key=f"chat_{chat_id}", type=btn_type):
                        st.session_state.current_chat_id = chat_id
                        st.session_state.show_citation_id = None
                        st.session_state.documents_cache = {}
                        with st.spinner(f"Loading chat '{title}'..."):
                            st.session_state.messages = api_get_messages(chat_id)
                        st.rerun()

# --- Chat Message ---
def render_chat_message(message: Dict, index: int):
    role = message["role"]
    content = message.get("content", "")
    citations = message.get("citations", [])
    formatted = format_text_with_citations(content, citations) if citations else content

    with st.chat_message(role):
        st.markdown(formatted, unsafe_allow_html=True)
        if citations:
            for idx, c in enumerate(citations):
                if st.columns(len(citations))[idx].button(f"[{c['id']}]", key=f"citation_btn_{index}_{idx}"):
                    st.session_state.show_citation_id = c['id']
                    st.rerun()

        ts = message.get('timestamp')
        try:
            ts = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M") if isinstance(ts, str) else ts
        except:
            pass

        caption = " | ".join(filter(None, [str(ts), get_model_name_from_message(message) if role == "assistant" else None]))
        if caption:
            st.caption(caption)

        link = message.get("link")
        if link:
            if st.button("🔗 View Link", key=f"view_link_{index}"):
                components.html(f"<script>window.open('{link}', '_blank');</script>", height=0, width=0)

# --- Chat Area ---
def render_chat_area():
    with st.container(height=500, border=False):
        if st.session_state.current_chat_id:
            for i, msg in enumerate(st.session_state.messages):
                render_chat_message(msg, i)
        else:
            st.button("Select a chat from the sidebar or start a new one using  ➕", key="start_chat_btn", on_click=create_new_chat, type="primary")

    if st.session_state.current_chat_id:
        st.divider()
        user_input = st.chat_input("Type your message here...", key=f"chat_input_{st.session_state.current_chat_id}")
        if user_input:
            with st.spinner("Sending..."):
                api_create_message(st.session_state.current_chat_id, "user", user_input)
                st.session_state.messages = api_get_messages(st.session_state.current_chat_id)
            st.rerun()

# --- Create Chat ---
def create_new_chat():
    with st.spinner("Creating new chat..."):
        new_chat = api_create_session()
    if new_chat:
        st.session_state.chat_sessions[new_chat['id']] = new_chat
        st.session_state.current_chat_id = new_chat['id']
        st.session_state.messages = []
        st.session_state.show_citation_id = None
        st.session_state.documents_cache = {}
        st.toast(f"Created '{new_chat['title']}'")
        st.rerun()

# --- Citation Modal ---
def display_citation_modal(modal: Modal):
    if st.session_state.show_citation_id and not modal.is_open():
        modal.open()

    if modal.is_open() and st.session_state.show_citation_id:
        cid = st.session_state.show_citation_id
        docs = st.session_state.documents_cache.get(cid)
        if not docs:
            with st.spinner(f"Loading citation '{cid}'..."):
                doc_ids = api_get_citation(cid)
                docs = api_get_docs(doc_ids)
                if docs:
                    st.session_state.documents_cache[cid] = docs

        with modal.container():
            if docs:
                for doc in docs:
                    st.markdown(f"### {doc.get('title', 'Citation Detail')}")
                    st.markdown(f"**Document ID:** `{doc.get('id', 'N/A')}`")
                    st.markdown(f"> {doc.get('text', 'No content available.')}")
            else:
                st.warning(f"Could not load citation ID '{cid}'")

            st.divider()
            if st.button("Close Citation", key=f"close_{cid}") or st.button("X", key="modal_close"):
                st.session_state.show_citation_id = None
                modal.close()
                st.rerun()

# --- Main ---
modal = initialize_app()
render_header = lambda: st.header(":blue[Chat with Germano]", divider=True)
render_header()
render_sidebar()
render_chat_area()
display_citation_modal(modal)
