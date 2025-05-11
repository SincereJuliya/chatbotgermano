import datetime
import markdown
import streamlit as st
from typing import List, Dict, Optional, Any, Literal
import streamlit.components.v1 as components, html
from modal import Modal
import math

st.set_page_config(layout="centered",
                    page_title="Chatbot Germano",
                    page_icon="🤖",
                    menu_items={
                                'Get Help': 'https://www.example.com/help', # Placeholder
                                'Report a bug': "https://www.example.com/bug", # Placeholder
                                'About': "# Streamlit Chat with FastAPI Backend!"
                        },
                    )

def calculate_text_height(text: str, font_size: int, line_height_multiplier: float, max_height: int) -> int:
    """
    Calculates the estimated height of the text in a container based on font size, line height, and maximum height.

    Args:
        text (str): The text whose height we want to estimate.
        font_size (int): The font size in pixels.
        line_height_multiplier (float): The multiplier for line height based on the font size (e.g., 1.6).
        max_height (int): The maximum height of the chat container (in pixels).
        max_chars_per_line (int): The maximum number of characters per line.

    Returns:
        int: The estimated height of the text in pixels, adjusted to not exceed the maximum height.
    """
    # Calculate number of characters
    num_chars = len(text)
    # Calculate number of line breaks (newlines)
    num_breaks = text.count('\n')
    max_chars_per_line = 65  # Assuming an average of 50 characters per line

    # Calculate number of lines based on text length and max characters per line
    num_lines = (num_chars / (line_height_multiplier*max_chars_per_line)) + (num_breaks*line_height_multiplier if num_breaks > 0 else 0)

    # Estimate the total height required for the text
    total_height = round(num_lines * font_size * (line_height_multiplier if num_breaks> 0 else 1))
    #st.info(f"Text Height: {total_height} px (Font Size: {font_size}px, Line Height: {line_height_multiplier}, Max Height: {max_height}px, {num_chars} chars)")
    return min(total_height, max_height)

# Include JavaScript
def render_text_with_citations(text: str):
    # Display markdown with HTML content
    
    # Inject JavaScript to handle the click event on citation spans
    components.html(f"""
    <div style="letter-spacing: 0.01em; line-height: 1.6; box-sizing: border-box; color: rgb(49, 51, 63); color-scheme: light; font-family: sans-serif; font-size: 14px; font-weight: 400; margin-bottom: 16px; margin-left: 0px; margin-right: 0px; margin-top: 0px; padding-bottom: 0px; padding-left: 0px; padding-right: 0px; padding-top: 0px; word-break: break-word;">
        {text}
    </div>
    <script>
        window.onload = function() {{
            const spans = document.querySelectorAll('span[data-citation-id]');
            spans.forEach(span => {{
                span.addEventListener('click', () => {{
                    const citationId = span.getAttribute('data-citation-id');
                    const lol = `[class*="trigger-button-${{citationId}}"]`;
                    const hiddenInput = window.parent.document.querySelector(lol);
                    const button = hiddenInput.querySelector('button');
                    if (button) {{
                        button.click();
                    }}
                }});
            }});
            
        }};
    </script>
    """, height=calculate_text_height(text, 14, 1.6, 350), scrolling=True)

# These imports must appear after setting the set_page_config bec it has to be 1st
from utils import(
    handle_api_error,
    api_get_sessions,
    api_create_session,
    api_get_messages,
    api_create_message,
    api_get_citation,
    api_get_docs,
    get_model_name_from_message,
    find_url_in_text,
    extract_citations,
    format_text_with_citations
)

def load_css(file_path):
    with open(file_path, "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# --- Streamlit Modal Setup ---
# Define Modal instance (can be defined once globally or here)
modal = Modal(
    title="Citation Details", # Set a relevant title
    key="citation-modal"
)

# --- Configuration ---
_raw_url = st.secrets.get("API_URL", "").strip()
#_raw_url = "http://13.53.108.0:8000"

if _raw_url:
    BACKEND_URL = _raw_url
else:
    BACKEND_URL = "http://localhost:8000"

# Guarantee scheme
if not BACKEND_URL.startswith(("http://", "https://")):
    BACKEND_URL = "http://" + BACKEND_URL

# For debugging: expose the URL in the query params using new API
st.query_params = {"debug_backend": BACKEND_URL}
print(f"▶️ Using BACKEND_URL = {BACKEND_URL}")

# Inject into utils so all api_... functions use this base
import utils
utils.BACKEND_URL = BACKEND_URL

"""# Chatbot Germano """

def initialize_app():
    """Initialize app configuration and session state variables.
    Sets up the page layout, initializes session state variables, and fetches initial chat sessions.
    
    Returns:
        Modal instance for displaying citation details.
    """
    # Initialize session state variables if they don't exist
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {"name": "User", "avatar": "👤"}

    # Store fetched sessions {session_id: session_data}
    if "chat_sessions" not in st.session_state:
         # Fetch initial list of sessions from backend
         fetched_sessions = api_get_sessions() # TODO: make this async
         st.session_state.chat_sessions = {s['id']: s for s in fetched_sessions} if fetched_sessions else {}

    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None

    # Store messages for the *currently selected* chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # State for citation modal (using ID of citation to show)
    if "show_citation_id" not in st.session_state:
        st.session_state.show_citation_id = None

    # Cache for fetched citation details {citation_id: citation_data}
    if "documents_cache" not in st.session_state:
        st.session_state.documents_cache = {}
        
    #display_citation_modal()


# --- UI Rendering Functions ---
def render_text_with_buttons() -> None:
    # Render the citation as a button
    st.session_state.show_citation_id = citation_id

def render_header() -> None:
    """Render the app header."""
    st.header(":blue[Chat with Germano]", divider=True)

def render_sidebar() -> None:
    """Render the sidebar with chat sessions."""
    with st.sidebar:
        # --- Top Bar ---
        # (Keep the settings/profile/new chat buttons as before)
        col_settings, col_profile, _, col_new_chat, _ = st.columns([0.60, 0.15, 0.05, 0.15, 0.05])
        with col_settings:
             if st.button("Settings", key="settings_btn", help="App Settings (Placeholder)"):
                 st.toast("Settings clicked (placeholder)")
        with col_profile:
             if st.button(f"{st.session_state.user_profile['avatar']}", key="profile_btn", help="User Profile (Placeholder)"):
                  st.toast(f"User profile clicked (placeholder)")
        with col_new_chat:
             if st.button("➕", key="new_chat_btn", help="Start a new chat"):
                create_new_chat()

        st.divider()

        # --- Chat List ---
        st.header("Chat Sessions", divider=False)
        if not st.session_state.chat_sessions:
            st.caption("No chats yet. Click ➕ to start!")
        else:
            # Scrollable Chat List
            chat_list_container = st.container(height=300, border=True)
            with chat_list_container:
                # Sort by title or creation date if available and desired
                # API currently sorts by created_at desc, let's use the order received
                sorted_chat_ids = list(st.session_state.chat_sessions.keys())

                for chat_id in sorted_chat_ids:
                    chat_title = st.session_state.chat_sessions[chat_id].get('title', f"Chat {chat_id[:6]}")
                    button_type = "primary" if chat_id == st.session_state.current_chat_id else "secondary"
                    if st.button(f"💬 {chat_title[:30]}", key=f"chat_{chat_id}", use_container_width=True, type=button_type):
                        if st.session_state.current_chat_id != chat_id:
                             st.session_state.current_chat_id = chat_id
                             st.session_state.show_citation_id = None # Reset modal state
                             st.session_state.documents_cache = {} # Clear citation cache
                             # Fetch messages for the selected chat
                             with st.spinner(f"Loading chat '{chat_title}'..."):
                                 st.session_state.messages = api_get_messages(chat_id)
                             st.rerun() # Rerun to display fetched messages

def render_chat_message(message: Dict, index: int) -> None:
    """Render a single chat message from the fetched data.
    
    Args:
        message (dict): The message data containing role, content, and other attributes.
    
    Returns: 
        None
    """
    # Determine avatar and model name based on role
    model_name = get_model_name_from_message(message) if message["role"] == "assistant" else None
    
    # avatar = "👤" if message["role"] == "user" else "🤖"
    # with st.chat_message(message["role"], avatar=avatar):
    with st.chat_message(message["role"]):
        content = message.get("content", "")
        # citations = extract_citations(content)
        # formatted_content = format_text_with_citations(content)
        citations = message.get("citations", [])
        formatted_content = format_text_with_citations(content, citations) if citations else st.markdown(content)
        
        if citations:
            text = formatted_content
            render_text_with_citations(text)
        
        # Render invisible buttons for citations present in *this specific message*
        if citations:
            # Use columns to lay out buttons less intrusively if many citations
            cols = st.columns(len(citations))
            # for idx, (citation_id, cited_text) in enumerate(citations.items()):
            for idx, citation in enumerate(citations):
                with cols[idx]:
                    citation_id = citation['id']
                    
                    # Unique button key combining message index and citation id/index
                    button_key = f"trigger-button-{citation_id}"
                    if st.button(f"[{citation_id}]", key=button_key, help=f"View details for '{citation['text']}'", 
                                 use_container_width=False, type="secondary"):
                        st.session_state.show_citation_id = citation_id
                        # No rerun here, display_citation_modal logic handles opening
                        # Need to trigger a rerun *after* state is set if modal check is later
                        st.rerun() # Rerun needed to make modal check happen
        

        # Display timestamp and model info (if assistant)
        timestamp_str = message.get('timestamp', '')
        # Try formatting timestamp if it's a datetime object
        if isinstance(timestamp_str, datetime.datetime):
             try:
                  timestamp_str = timestamp_str.strftime("%Y-%m-%d %H:%M")
             except ValueError:
                  timestamp_str = str(timestamp_str) # Fallback to string representation
        elif isinstance(timestamp_str, str):
            # Attempt to parse and reformat common ISO string format
             try:
                 dt_obj = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                 timestamp_str = dt_obj.strftime("%Y-%m-%d %H:%M")
             except ValueError:
                 pass # Keep original string if parsing fails


        caption_parts = [timestamp_str]
        if model_name:
             caption_parts.append(model_name)
        st.caption(" | ".join(filter(None, caption_parts)))

        # Display optional link button
        link_url = message.get("link")
        if link_url:
             link_key = f"view_link_{st.session_state.current_chat_id}_{index}"
             if st.button("🔗 View Link", key=link_key, help=f"Open {link_url}"):
                  # Open link in new tab
                  components.html(f"<script>window.open('{link_url}', '_blank');</script>", height=0, width=0)


def render_chat_area() -> None:
    """Render the main chat area including messages and input."""
    chat_container = st.container(
                            height=600, # Set a fixed height for the chat area
                            border=False,
                            key="chat_container"  # Add this for better CSS targeting
    )

    # Display existing messages for the current chat
    with chat_container:
        if st.session_state.current_chat_id:
            if not st.session_state.messages:
                st.caption("No messages in this chat yet. Send one below!")
            # Display messages using the fetched list in session state
            for i, message in enumerate(st.session_state.messages):
                render_chat_message(message, i)
        else:
            # Text-styled button that shares the create_new_chat function
            st.button(
                   "Select a chat from the sidebar or start a new one using  ➕",
                    key="text_chat_trigger",  # This key is used in the CSS selector
                    on_click=create_new_chat,
                    help="Start a new chat",
                    type="primary"
            )
    

    # Separator and Chat input - Place outside the message container
    if st.session_state.current_chat_id:
        st.divider()
        user_input = st.chat_input("Type your message here...", key=f"chat_input_{st.session_state.current_chat_id}")

        if user_input:
            current_chat_id = st.session_state.current_chat_id
            # 1. Add user message visually (optimistic update - optional)
            #    This provides immediate feedback but might differ slightly from backend timestamp/id
            # with chat_container: # Re-enter container context if needed
            #     with st.chat_message("user", avatar="👤"):
            #          st.markdown(escape(user_input))

            # 2. Send user message to backend
            with st.spinner("Sending..."):
                 created_assistant_msg = api_create_message(current_chat_id, "user", user_input)

            if created_assistant_msg:
                print(f"3. render_chat_area -> created_assistant_msg: {created_assistant_msg} ")
                # 3. Refresh message list from backend to show user msg & potential (future) assistant msg
                with st.spinner("Checking for response..."): # Placeholder spinner
                    st.session_state.messages = api_get_messages(current_chat_id)
                st.rerun() # Rerun to display the refreshed message list
            else:
                 st.error("Failed to send message.") # API call already showed error

def create_new_chat():
    """Shared function for new chat creation"""
    with st.spinner("Creating new chat..."):
        new_session = api_create_session()
    if new_session:
        st.session_state.chat_sessions[new_session['id']] = new_session
        st.session_state.current_chat_id = new_session['id']
        st.session_state.messages = []
        st.session_state.show_citation_id = None
        st.session_state.documents_cache = {}
        st.toast(f"Created '{new_session['title']}'")
        st.rerun()
    else:
        st.error("Failed to create new chat session")


def display_citation_modal() -> None:
    """Displays the modal with citation details if show_citation_id is set."""
    # Check if we need to open the modal based on the state variable
    if st.session_state.show_citation_id and not modal.is_open():
        modal.open()

    if modal.is_open() and st.session_state.show_citation_id:
        citation_id = st.session_state.show_citation_id
        docs = None

        # Check cache first
        if citation_id in st.session_state.documents_cache:
            docs = st.session_state.documents_cache[citation_id]
        else:
            # Fetch from API if not in cache
            with st.spinner(f"Loading citation '{citation_id}'..."):
                doc_ids = api_get_citation(citation_id)
                print(f"1. display_citation_modal -> doc_ids: {doc_ids}")
                docs = api_get_docs(doc_ids)
                print(f"2. display_citation_modal -> docs 1: {docs}")
            if docs:
                st.session_state.documents_cache[citation_id] = docs # Store in cache
            print(f"2. display_citation_modal -> docs: {docs}")

        with modal.container():
            if docs:
                for doc in docs:
                    st.markdown(f"### {doc.get('title', 'Citation Detail')}")
                    st.markdown(f"**Document ID:** `{doc.get('id', 'N/A')}`")
                    st.write("**Content:**")
                    # Use st.markdown with blockquote for better formatting
                    st.markdown(f"> {doc.get('text', 'No content available.')}")
            else:
                # Error fetching or citation not found (API function handles toast/error)
                st.warning(f"Could not load details for citation ID '{citation_id}'. It might not exist.")

            st.divider()
            # Button to close the modal AND reset the state variable
            if st.button("Close Citation", key=f"close_citation_{citation_id}"):
                st.session_state.show_citation_id = None
                modal.close()
                st.rerun() # Rerun to reflect closed state

# --- Main Application Execution ---
def main() -> None:
    """The main function to run the Streamlit app.
    """
    # Initialize app (sets config, state vars, fetches initial sessions)
    initialize_app()

    # Add custom CSS
    load_css("frontend/styles.css")

    # Render UI components
    render_header()
    render_sidebar()
    render_chat_area()
    

    # Handle Citation Modal Display (check state and render if needed)
    display_citation_modal()

if __name__ == "__main__":
    main()