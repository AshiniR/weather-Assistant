import os
from datetime import date
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

# --- Weather Tools ---
geolocator = Nominatim(user_agent="weather-chatbot")

class WeatherInput(BaseModel):
    location: str = Field(description="City and country, e.g., 'Berlin, Germany'")

@tool("get_current_weather", args_schema=WeatherInput, return_direct=True)
def get_current_weather(location: str):
    """Get current weather for a location."""
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
        return resp.json().get("current_weather", {})
    except Exception as e:
        return {"error": str(e)}

# --- Forecast Tool ---
class ForecastInput(BaseModel):
    location: str = Field(description="City and country, e.g., 'Berlin, Germany'")
    days: int = Field(default=3, description="Number of days for forecast (1–7)")

@tool("get_weather_forecast", args_schema=ForecastInput, return_direct=True)
def get_weather_forecast(location: str, days: int = 3):
    """Get daily weather forecast for a location (up to 7 days)."""
    try:
        place = geolocator.geocode(location, timeout=10)
        if not place:
            return {"error": f"Location not found: {location}"}
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={place.latitude}&longitude={place.longitude}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&forecast_days={days}&timezone=auto"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json().get("daily", {})
    except Exception as e:
        return {"error": str(e)}

# --- Clothing Suggestion Tool ---
class ClothingInput(BaseModel):
    location: str = Field(description="City and country, e.g., 'Berlin, Germany'")

@tool("get_clothing_suggestion", args_schema=ClothingInput, return_direct=True)
def get_clothing_suggestion(location: str):
    """Suggest clothing based on current weather."""
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
        weather = resp.json().get("current_weather", {})

        temp = weather.get("temperature", 20)
        wind = weather.get("windspeed", 0)

        if temp < 10:
            suggestion = "🧥 Wear a warm coat, scarf, and gloves."
        elif 10 <= temp < 20:
            suggestion = "🧥👕 A light jacket or sweater is good."
        else:
            suggestion = "😎 T-shirt weather! Stay cool."

        if wind > 20:
            suggestion += " 💨 It's windy, take a windbreaker."

        return {"temperature": temp, "windspeed": wind, "suggestion": suggestion}
    except Exception as e:
        return {"error": str(e)}

# --- Weather News Tool ---
class NewsInput(BaseModel):
    country: str = Field(default="us", description="Country code, e.g., 'us', 'de', 'lk'")

@tool("get_weather_news", args_schema=NewsInput, return_direct=True)
def get_weather_news(country: str = "us"):
    """Get top and today's weather-related news headlines."""
    try:
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            return {"error": "NEWS_API_KEY not set."}

        # 1) Try top-headlines first
        url_top = f"https://newsapi.org/v2/top-headlines?q=weather&country={country}&apiKey={api_key}"
        resp_top = requests.get(url_top, timeout=20)
        resp_top.raise_for_status()
        articles_top = resp_top.json().get("articles", [])[:5]
        top_headlines = [a["title"] for a in articles_top if "title" in a]

        # 2) Then get all today's news
        today = date.today().isoformat()
        url_all = f"https://newsapi.org/v2/everything?q=weather&from={today}&to={today}&sortBy=publishedAt&language=en&apiKey={api_key}"
        resp_all = requests.get(url_all, timeout=20)
        resp_all.raise_for_status()
        articles_all = resp_all.json().get("articles", [])[:5]
        today_headlines = [a["title"] for a in articles_all if "title" in a]

        return {
            "top_headlines": top_headlines,
            "today_headlines": today_headlines
        }
    except Exception as e:
        return {"error": str(e)}

# --- Tools ---
tools = [get_current_weather, get_weather_forecast, get_clothing_suggestion, get_weather_news]
tools_by_name = {t.name: t for t in tools}

# --- Model ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.7,
    google_api_key=api_key,
)
model = llm.bind_tools(tools)

# --- System Prompt ---
SYSTEM_PROMPT = """You are a friendly weather chatbot 🤖

You can use 4 tools:
🌤️ get_current_weather → Current weather
📅 get_weather_forecast → Forecast 1–7 days
👕 get_clothing_suggestion → What to wear
📰 get_weather_news → Weather-related news

Rules for tool use:
- If the user asks about current weather (temperature, condition, "now") → get_current_weather
- If the user asks about forecast (tomorrow, next days, weekend) → get_weather_forecast
- If the user asks about clothing/outfit → get_clothing_suggestion
- If the user asks about news, storm updates, latest weather → get_weather_news
- If unsure, ask the user to clarify.

Few-shot examples:
User: "What's the weather in Paris right now?"
Assistant: [Calls get_current_weather(location="Paris, France")]

User: "Can you give me a 3-day forecast in Tokyo?"
Assistant: [Calls get_weather_forecast(location="Tokyo, Japan", days=3)]

User: "What should I wear in Berlin today?"
Assistant: [Calls get_clothing_suggestion(location="Berlin, Germany")]

User: "Give me the latest weather news in the US"
Assistant: [Calls get_weather_news(country="us")]

User: "Will it rain this weekend in London?"
Assistant: [Calls get_weather_forecast(location="London, UK", days=3)]

Always respond in short, friendly messages with emojis after using the tools.
"""

# --- Node Functions ---
def call_model(state: AgentState, config: RunnableConfig):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = model.invoke(messages, config)
    return {"messages": [response], "number_of_steps": state.get("number_of_steps", 0) + 1}

def call_tool(state: AgentState):
    last = state["messages"][-1]
    outputs = []
    for tool_call in getattr(last, "tool_calls", []) or []:
        tool_name, tool_args, tool_id = tool_call["name"], tool_call["args"], tool_call["id"]
        result = tools_by_name[tool_name].invoke(tool_args)
        outputs.append(ToolMessage(content=result, name=tool_name, tool_call_id=tool_id))
    return {"messages": outputs, "number_of_steps": state.get("number_of_steps", 0) + 1}

# --- Graph Logic ---
def should_continue(state: AgentState):
    last = state["messages"][-1]
    return "continue" if getattr(last, "tool_calls", []) else "end"

workflow = StateGraph(AgentState)
workflow.add_node("llm", call_model)
workflow.add_node("tools", call_tool)
workflow.set_entry_point("llm")
workflow.add_conditional_edges("llm", should_continue, {"continue": "tools", "end": END})
workflow.add_edge("tools", "llm")
graph = workflow.compile()

# --- Chatbot Run ---
def run_once(prompt: str):
    inputs = {"messages": [("user", prompt)], "number_of_steps": 0}
    for state in graph.stream(inputs, stream_mode="values"):
        msg = state["messages"][-1]
        try:
            msg.pretty_print()
        except Exception:
            print(f"[{msg.__class__.__name__}] {getattr(msg, 'content', '')}")

if __name__ == "__main__":
    print("\n🤖 Weather Chatbot Ready!")
    print("You can ask me about the following:\n")
    print("🌤️ Current Weather: 'What's the weather in Colombo?'")
    print("📅 Forecast: 'Give me a 3-day forecast in London' or 'Will it rain this weekend in Paris?'")
    print("👕 Clothing Suggestion: 'What should I wear in Berlin today?'")
    print("📰 Weather News: 'Show me the latest weather news in the US'")
    print("🚨 Severe Weather Alerts: 'Are there any weather warnings in New York?'")
    print("\nType 'exit' to quit.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break
        run_once(user)