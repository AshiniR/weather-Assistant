import streamlit as st
from weather_agent import graph
from langchain.schema import HumanMessage

def get_weather_response(user_input: str, conversation_messages):
    # Add user message to conversation
    conversation_messages.append(HumanMessage(content=user_input))
    state = {"messages": conversation_messages}
    
    # Stream the graph and get the final response
    final_response = None
    for event in graph.stream(state):
        for value in event.values():
            conversation_messages[:] = value["messages"]
            final_response = value["messages"][-1].content
    
    return final_response, conversation_messages

# Streamlit UI
st.title("🌤️ Weather Assistant")
st.write("Ask me about weather, forecasts, clothing suggestions, or weather alerts!")

# Initialize session state for conversation
if "conversation_messages" not in st.session_state:
    st.session_state.conversation_messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "processing" not in st.session_state:
    st.session_state.processing = False

# Chat interface - Display chat history
with st.container():
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])

# Input field
user_input = st.chat_input("Type your weather question here...", disabled=st.session_state.processing)

if user_input and not st.session_state.processing:
    # Set processing state
    st.session_state.processing = True
    
    # Add user message to chat history and display immediately
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    # Display user message immediately
    with st.chat_message("user"):
        st.write(user_input)
    
    # Show processing message
    with st.chat_message("assistant"):
        processing_placeholder = st.empty()
        processing_placeholder.write("Thinking...")
        
        # Get response from weather assistant
        response, updated_messages = get_weather_response(
            user_input, 
            st.session_state.conversation_messages.copy()
        )
        st.session_state.conversation_messages = updated_messages
        
        # Clear processing message and show response
        processing_placeholder.empty()
        st.write(response)
    
    # Add assistant response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Reset processing state
    st.session_state.processing = False
    
    # Rerun to refresh the display
    st.rerun()