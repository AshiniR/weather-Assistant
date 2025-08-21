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
    

class ForecastInput(BaseModel):
    location: str = Field(description="City and country, e.g., 'Berlin, Germany'")
    days: int = Field(default=3, description="Number of days for forecast (1–7)")

@tool("get_weather_forecast", args_schema=ForecastInput, return_direct=True)
def get_weather_forecast(location: str, days: int = 3):
    """Get daily weather forecast for a location (up to 7 days)."""
    try:
        if days < 1 or days > 7:
            return {"error": "Days must be between 1 and 7."}

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
        data = resp.json()
        return data.get("daily", {})
    except Exception as e:
        return {"error": str(e)}
    

class AirQualityInput(BaseModel):
    location: str = Field(description="City and country, e.g., 'Berlin, Germany'")

@tool("get_air_quality", args_schema=AirQualityInput, return_direct=True)
def get_air_quality(location: str):
    """Get current air quality data (AQI, PM2.5, PM10, Ozone, etc.) for a location."""
    try:
        place = geolocator.geocode(location, timeout=10)
        if not place:
            return {"error": f"Location not found: {location}"}

        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={place.latitude}&longitude={place.longitude}"
            f"&hourly=pm10,pm2_5,carbon_monoxide,ozone,nitrogen_dioxide,sulphur_dioxide,us_aqi"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        hourly = data.get("hourly", {})

        return {
            "pm2_5": hourly.get("pm2_5", ["N/A"])[0],
            "pm10": hourly.get("pm10", ["N/A"])[0],
            "ozone": hourly.get("ozone", ["N/A"])[0],
            "carbon_monoxide": hourly.get("carbon_monoxide", ["N/A"])[0],
            "us_aqi": hourly.get("us_aqi", ["N/A"])[0],
        }
    except Exception as e:
        return {"error": str(e)}
    

class AlertInput(BaseModel):
    location: str = Field(description="City and country, e.g., 'Berlin, Germany'")

@tool("get_weather_alerts", args_schema=AlertInput, return_direct=True)
def get_weather_alerts(location: str):
    """Check for severe weather warnings like storms, floods, or heatwaves."""
    try:
        place = geolocator.geocode(location, timeout=10)
        if not place:
            return {"error": f"Location not found: {location}"}

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={place.latitude}&longitude={place.longitude}"
            f"&daily=weathercode&forecast_days=1&timezone=auto"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        weather_codes = data.get("daily", {}).get("weathercode", [])

        alerts = []
        if 95 in weather_codes:
            alerts.append("⚡ Thunderstorm warning")
        if 96 in weather_codes or 99 in weather_codes:
            alerts.append("🌧️ Severe rain or hail warning")
        if not alerts:
            alerts = ["✅ No severe weather alerts today"]

        return {"alerts": alerts}
    except Exception as e:
        return {"error": str(e)}


tools = [
    get_current_weather,
    get_weather_alerts,
    get_air_quality,
    get_weather_forecast,
]
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

You have access to the following tools:
- get_current_weather: Get the current weather for a given city and country.
- get_weather_forecast: Get the weather forecast for 1–7 days.
- get_weather_alerts: Check for severe weather alerts (storms, floods, heatwaves).
- get_air_quality: Get current air quality (AQI, PM2.5, PM10, Ozone, etc.).

Instructions:
- If the user asks for the current weather, call `get_current_weather`.
- If the user asks about weather for upcoming days (tomorrow, next 3 days, weekend, etc.), call `get_weather_forecast`.
- If the user asks about warnings, alerts, storms, floods, or heatwaves, call `get_weather_alerts`.
- If the user asks about air quality, pollution, or AQI, call `get_air_quality`.

Guidelines:
- If the location is missing, ask the user for it.
- Always summarize tool results in clear, concise language.
- Keep answers short but informative (1–3 sentences).
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