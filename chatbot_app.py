import streamlit as st
import requests
import json
import time
import uuid

# --- Page Configuration ---
st.set_page_config(
    page_title="NextMove Job Chatbot",
    page_icon="🤖",
    layout="wide"
)

# --- 1. INITIALIZATION (Must be at the top) ---
# Initialize Session ID if missing
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Initialize Chat Messages if missing
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- API Endpoint ---
FASTAPI_ENDPOINT = "http://127.0.0.1:8000/run"

# --- Page Title ---
st.title("🤖 NextMove Job Chatbot")

# --- Sidebar & Settings ---
with st.sidebar:
    st.header("Settings")
    
    debug_mode = st.checkbox("🛠️ Debug Mode", value=False, help="Show intermediate steps (SQL, JSON, etc.)")
    use_history = st.checkbox("🧠 History Aware", value=True, help="Enable persistent memory.")
    
    st.caption(f"Session ID: {st.session_state.session_id[:8]}...") 
    
    st.divider()
    
    if st.button("🗑️ Clear Chat & Reset Session"):
        # Clear local UI history
        st.session_state.messages = []
        # Generate new session ID (simulate fresh start)
        st.session_state.session_id = str(uuid.uuid4())
        # Rerun immediately to reflect empty state
        st.rerun()

# --- Display Past Messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "debug_info" in message:
            with st.expander("Show Debug Info"):
                st.json(message["debug_info"])

# --- Handle User Input ---
if prompt := st.chat_input("Ask about job postings..."):
    # 1. Append user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Call Backend
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking... ⏳")
        start_time = time.time()
        
        try:
            # Prepare payload
            payload = {
                "query": prompt, 
                "debug_mode": debug_mode,
                "use_history": use_history,
                "session_id": st.session_state.session_id
            }
            
            # Send Request
            response = requests.post(FASTAPI_ENDPOINT, json=payload, timeout=300)
            response.raise_for_status()
            
            # Parse Response
            data = response.json()
            final_answer = data.get("final_answer", "Sorry, I received an invalid response.")
            debug_info = data.get("debug_info")
            
            # Display Answer
            message_placeholder.markdown(final_answer)

            # Store Assistant Response
            assistant_message = {"role": "assistant", "content": final_answer}
            
            if debug_mode and debug_info:
                assistant_message["debug_info"] = debug_info
                with st.expander("Show Debug Info"):
                    st.json(debug_info)
            
            st.session_state.messages.append(assistant_message)

        except requests.exceptions.ConnectionError:
            message_placeholder.error("Connection Error: Is the FastAPI server running?")
        except Exception as e:
            message_placeholder.error(f"An error occurred: {e}")