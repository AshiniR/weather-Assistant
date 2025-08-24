import streamlit as st
from weather_agent import run_once

st.set_page_config(page_title="Weather Chatbot", page_icon="🌤️")

st.markdown(
    "<h2 style='text-align: center;'>🤖 Weather Chatbot</h2>",
    unsafe_allow_html=True,
)

st.write("Ask me about the weather, forecasts, clothing suggestions, or weather news!")

# --- Example Queries Section ---
with st.expander("💡 Example Queries"):
    st.markdown("""
    - 🌤️ **Current Weather:** `What's the weather in Colombo?`  
    - 📅 **Forecast:** `Give me a 3-day forecast in London`  
    - 👕 **Clothing Suggestion:** `What should I wear in Berlin today?`  
    - 📰 **Weather News / Alerts:** `Are there any weather warnings in New York?`
    """)

# --- Initialize chat history ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Chat Display ---
chat_container = st.container()

with chat_container:
    for user, bot in st.session_state.chat_history:
        # User message (right side bubble with avatar)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-end; align-items: center; margin: 8px;">
                <div style="max-width: 70%; background-color: #DCF8C6; padding: 10px 15px; 
                            border-radius: 12px; text-align: left;">
                    {user}
                </div>
                <div style="margin-left: 8px; font-size: 22px;">🙂</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Bot message (left side bubble with avatar)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-start; align-items: center; margin: 8px;">
                <div style="margin-right: 8px; font-size: 22px;">🤖</div>
                <div style="max-width: 70%; background-color: #F1F0F0; padding: 10px 15px; 
                            border-radius: 12px; text-align: left;">
                    {bot}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# --- Input Box ---
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message:", "")
    submit = st.form_submit_button("Send")

if submit and user_input:
    if user_input.strip().lower() in {"exit", "quit"}:
        st.stop()
    assistant_reply = run_once(user_input.strip())
    st.session_state.chat_history.append((user_input.strip(), assistant_reply))
    st.rerun()
