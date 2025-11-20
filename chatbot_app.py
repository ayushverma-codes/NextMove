import streamlit as st
import requests
import json
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="NextMove Job Chatbot",
    page_icon="🤖",
    layout="wide"
)

# --- API Endpoint ---
FASTAPI_ENDPOINT = "http://127.0.0.1:8000/run"
# --- Page Title and Sidebar ---
st.title("🤖 NextMove Job Chatbot")

with st.sidebar:
    st.header("Settings")
    
    # 1. Debug Mode Toggle
    debug_mode = st.checkbox("🛠️ Debug Mode", value=False, help="Show intermediate steps (SQL, JSON, etc.)")
    
    # 2. History/Context Toggle
    use_history = st.checkbox("🧠 History Aware", value=True, help="Allow the bot to remember previous messages.")
    
    st.divider()
    
    if st.button("🗑️ Clear Chat UI"):
        st.session_state.messages = []
        st.rerun()

# --- Chat History Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display Past Messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # If debug data exists from a previous turn, display it
        if "debug_info" in message:
            with st.expander("Show Debug Info"):
                st.json(message["debug_info"])

# --- Handle User Input ---
if prompt := st.chat_input("Ask about job postings..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Call FastAPI Backend ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking... ⏳")
        start_time = time.time()
        
        try:
            # UPDATED PAYLOAD with 'use_history'
            payload = {
                "query": prompt, 
                "debug_mode": debug_mode,
                "use_history": use_history
            }
            
            # Send POST request
            response = requests.post(FASTAPI_ENDPOINT, json=payload, timeout=300)
            response.raise_for_status() # Raise an exception for bad status codes
            
            # Parse the response
            data = response.json()
            final_answer = data.get("final_answer", "Sorry, I received an invalid response.")
            debug_info = data.get("debug_info")
            
            end_time = time.time()
            elapsed_time = f"(Time: {end_time - start_time:.2f}s)"

            # Display the final answer
            message_placeholder.markdown(final_answer)

            # Store assistant response in history
            assistant_message = {"role": "assistant", "content": final_answer}
            
            # If in debug mode, show and store debug info
            if debug_mode and debug_info:
                assistant_message["debug_info"] = debug_info
                with st.expander("Show Debug Info"):
                    st.json(debug_info)
            
            st.session_state.messages.append(assistant_message)

        except requests.exceptions.ConnectionError:
            message_placeholder.error("Connection Error: Could not connect to the NextMove API. Is the FastAPI server running?")
            st.stop()
        except requests.exceptions.RequestException as e:
            message_placeholder.error(f"API Error: {e}")
            st.stop()
        except Exception as e:
            message_placeholder.error(f"An unexpected error occurred: {e}")
            st.stop()