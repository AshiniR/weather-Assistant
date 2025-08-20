import os
from datetime import datetime
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
load_dotenv()

from geopy.geocoders import Nominatim
import requests
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from langchain_google_genai import ChatGoogleGenerativeAI

# --- Agent State ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    number_of_steps: int

# --- Weather Tool ---
geolocator = Nominatim(user_agent="weather-app")

class WeatherInput(BaseModel):
    location: str = Field(description="City and country, e.g., 'Berlin, Germany'")

@tool("get_current_weather", args_schema=WeatherInput, return_direct=True)
def get_current_weather(location: str):
    """Get current weather for a location using Open-Meteo."""
    try:
        place = geolocator.geocode(location, timeout=10)
        if not place:
            return {"error": f"Location not found: {location}"}
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={place.latitude}&longitude={place.longitude}"
            f"&current_weather=true"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        weather = data.get("current_weather", {})
        if not weather:
            return {"error": "No current weather data returned."}
        return {
            "temperature": weather.get("temperature"),
            "windspeed": weather.get("windspeed"),
            "weathercode": weather.get("weathercode"),
            "time": weather.get("time"),
        }
    except Exception as e:
        return {"error": str(e)}

tools = [get_current_weather]
tools_by_name = {t.name: t for t in tools}

# --- Model (Gemini 2.5) ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.7,
    max_retries=2,
    google_api_key=api_key,
)
model = llm.bind_tools(tools)

# --- Nodes ---
SYSTEM_PROMPT = """You are a helpful weather agent.
- If the user asks for the current weather, call the tool `get_current_weather` with a city and country.
- If the location is missing, ask the user for it.
- After receiving tool results, summarize the current weather clearly.
- Keep answers concise.
"""

def call_model(state: AgentState, config: RunnableConfig):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = model.invoke(messages, config)
    return {
        "messages": [response],
        "number_of_steps": state.get("number_of_steps", 0) + 1,
    }

def call_tool(state: AgentState):
    last = state["messages"][-1]
    outputs = []
    for tool_call in getattr(last, "tool_calls", []) or []:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        result = tools_by_name[tool_name].invoke(tool_args)
        outputs.append(
            ToolMessage(
                content=result,
                name=tool_name,
                tool_call_id=tool_id,
            )
        )
    return {
        "messages": outputs,
        "number_of_steps": state.get("number_of_steps", 0) + 1,
    }

# --- Edges ---
def should_continue(state: AgentState):
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", []):
        return "end"
    return "continue"

# --- Build LangGraph ---
workflow = StateGraph(AgentState)
workflow.add_node("llm", call_model)
workflow.add_node("tools", call_tool)
workflow.set_entry_point("llm")
workflow.add_conditional_edges(
    "llm",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    },
)
workflow.add_edge("tools", "llm")
graph = workflow.compile()

# --- CLI Demo ---
def run_once(prompt: str):
    inputs = {
        "messages": [("user", prompt)],
        "number_of_steps": 0,
    }
    final_state = None
    for state in graph.stream(inputs, stream_mode="values"):
        msg = state["messages"][-1]
        try:
            msg.pretty_print()
        except Exception:
            print(f"[{msg.__class__.__name__}] {getattr(msg, 'content', '')}")
        final_state = state
    return final_state

if __name__ == "__main__":
    print("\nWeather Agent ready! Ask for the current weather in a city (e.g., 'What's the weather in Paris?').")
    print("Type 'exit' to quit.\n")
    while True:
        user = input("You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break
        run_once(user)