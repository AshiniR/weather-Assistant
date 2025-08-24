
import os
import json
from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import requests
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Persistent memory (chat history, last location, last date) ---
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"chat_memory": [], "last_location": None, "last_date": None}

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

memory = load_memory()
chat_memory = memory["chat_memory"]
last_location = memory["last_location"]
last_date = memory["last_date"]
load_dotenv()

# --- Persistent memory (chat history, last location, last date) ---
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"chat_memory": [], "last_location": None, "last_date": None}

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

memory = load_memory()
chat_memory = memory["chat_memory"]
last_location = memory["last_location"]
last_date = memory["last_date"]
load_dotenv()
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


geolocator = Nominatim(user_agent="weather-app")

def detect_intent(user_query: str) -> str:
    user_query = user_query.lower().strip()

    if any(word in user_query for word in ["forecast", "next days", "tomorrow", "week"]):
        return "forecast"
    elif any(word in user_query for word in ["alert", "alerts", "warning", "warnings", "storm", "flood", "heatwave", "news"]):
        return "alerts"
    elif any(word in user_query for word in ["wear", "clothes", "clothing", "outfit"]):
        return "clothing"
    elif "weather" in user_query and not any(
        word in user_query for word in ["forecast", "alert", "alerts", "clothing", "sunrise", "sunset", "news", "warning", "warnings"]
    ):
        return "current_weather"
    else:
        return "unknown"


# --- Location Parsing Helpers ---
def parse_location(user_input: str):
    """Extract city and country if provided, else return just the first part."""
    import re
    # Remove trailing slashes and extra whitespace
    user_input = user_input.replace('/', ' ').strip()
    # Try to extract after 'in <location>' or 'at <location>'
    match = re.search(r'\b(?:in|at)\s+([A-Za-z\s]+)', user_input, re.IGNORECASE)
    if match:
        location_text = match.group(1).strip()
    else:
        # Try to extract after 'wear in <location>'
        match2 = re.search(r'wear in ([A-Za-z\s]+)', user_input, re.IGNORECASE)
        if match2:
            location_text = match2.group(1).strip()
        else:
            # Try to extract after 'weather in <location>'
            match3 = re.search(r'weather in ([A-Za-z\s]+)', user_input, re.IGNORECASE)
            if match3:
                location_text = match3.group(1).strip()
            else:
                # Try to extract last word if it looks like a place
                tokens = user_input.strip().split()
                # Remove common trailing words
                trailing = {'today', 'now', 'please', 'tomorrow', 'tonight', 'currently', 'week', 'morning', 'evening', 'weather', 'wear', 'should', 'i', 'what'}
                filtered = [t for t in tokens if t.lower() not in trailing]
                # If any capitalized word left, use last one
                cap_words = [t for t in filtered if t and t[0].isupper()]
                if cap_words:
                    location_text = cap_words[-1]
                elif filtered:
                    location_text = filtered[-1]
                else:
                    location_text = user_input.strip()

    # Remove trailing non-location words (e.g., 'today', 'now', 'please', 'tomorrow')
    location_text = re.sub(r'\b(today|now|please|tomorrow|right now|currently|this week|tonight|in the morning|in the evening|weather|wear|should|i|what)\b', '', location_text, flags=re.IGNORECASE).strip()
    # Remove any double spaces left after removal
    location_text = re.sub(r'\s+', ' ', location_text)
    parts = [p.strip() for p in location_text.split(",")]
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return parts[0], None

def get_location(city: str, country: str = None):
    """Geocode city + optional country into lat/lon."""
    if country:
        query = f"{city}, {country}"
    else:
        query = city
    place = geolocator.geocode(query, timeout=10)
    if not place:
        # If no country was provided, ask the user for it
        if not country or country.strip() == "":
            return {"need_country": True, "city": city}
        return None
    # Use the resolved place name if available
    resolved_city = getattr(place, 'raw', {}).get('display_name', None)
    if resolved_city:
        resolved_city = resolved_city.split(',')[0]
    return {
        "city": resolved_city or city,
        "country": country or "",
        "latitude": place.latitude,
        "longitude": place.longitude,
    }


# --- Tool Inputs ---
class WeatherInput(BaseModel):
    location: str = Field(description="City and optionally country, e.g., 'Berlin, Germany'")

class ForecastInput(BaseModel):
    location: str = Field(description="City and optionally country, e.g., 'London, UK'")
    days: int = Field(description="Number of days (1-7)", ge=1, le=7)

class ClothingInput(BaseModel):
    location: str = Field(description="City and optionally country, e.g., 'Berlin, Germany'")

class AlertInput(BaseModel):
    location: str = Field(description="City and optionally country, e.g., 'New York, USA'")


# --- Tools ---
# --- Tools with proper docstrings and safe location handling ---

@tool("get_current_weather", args_schema=WeatherInput, return_direct=True)
def get_current_weather(location: str):
    """Get current weather for a location using Open-Meteo API."""
    try:
        city, country = parse_location(location)
        loc = get_location(city, country)
        if isinstance(loc, dict) and loc.get("need_country"):
            return loc
        if not loc:
            return {"error": f"Location not found: {location}"}

        url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current_weather=true"
        resp = requests.get(url, timeout=20)
        data = resp.json()
        weather = data.get("current_weather", {})
        if not weather:
            return {"error": "No current weather data returned."}

        city_name = loc.get("city") or loc.get("name") or "Unknown"
        country_name = loc.get("country") or ""
        location_name = f"{city_name}, {country_name}" if country_name else city_name

        weather.update({"location": location_name})
        return weather

    except Exception as e:
        return {"error": str(e)}


@tool("get_forecast", args_schema=ForecastInput, return_direct=True)
def get_forecast(location: str, days: int):
    """Get weather forecast for the next N days using Open-Meteo API."""
    try:
        city, country = parse_location(location)
        loc = get_location(city, country)
        if not loc:
            return {"error": f"Location not found: {location}"}

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={loc['latitude']}&longitude={loc['longitude']}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=auto&forecast_days={days}"
        )
        resp = requests.get(url, timeout=20)
        data = resp.json()

        city_name = loc.get("city") or loc.get("name") or "Unknown"
        country_name = loc.get("country") or ""
        location_name = f"{city_name}, {country_name}" if country_name else city_name

        return {"location": location_name, "forecast": data.get("daily", {})}

    except Exception as e:
        return {"error": str(e)}


@tool("clothing_suggestion", args_schema=ClothingInput, return_direct=True)
def clothing_suggestion(location: str):
    """Suggest clothing based on current weather conditions."""
    try:

        weather = get_current_weather.invoke({"location": location})
        if "need_country" in weather:
            return weather
        if "error" in weather:
            return weather

        temp = weather.get("temperature", 25)
        wind = weather.get("windspeed", 5)

        if temp < 10:
            suggestion = "Wear a heavy jacket, gloves, and scarf."
        elif 10 <= temp < 20:
            suggestion = "Wear a light jacket or sweater."
        elif 20 <= temp < 30:
            suggestion = "Comfortable clothes like a t-shirt and jeans are fine."
        else:
            suggestion = "It's hot! Wear shorts and stay hydrated."

        if wind > 20:
            suggestion += " It's windy, consider a windbreaker."

        location_name = weather.get("location", "Unknown location")

        return {
            "clothing_advice": suggestion,
            "temperature": temp,
            "windspeed": wind,
            "location": location_name,
        }

    except Exception as e:
        return {"error": str(e)}


@tool("weather_alerts", args_schema=AlertInput, return_direct=True)
def weather_alerts(location: str):
    """Check for severe weather alerts in a given location using Open-Meteo API."""
    try:
        city, country = parse_location(location)
        loc = get_location(city, country)
        if not loc:
            return {"error": f"Location not found: {location}"}

        url = f"https://api.open-meteo.com/v1/warnings?latitude={loc['latitude']}&longitude={loc['longitude']}&timezone=auto"
        resp = requests.get(url, timeout=20)
        data = resp.json() if resp and resp.content else {}
        if not isinstance(data, dict):
            data = {}

        alerts = data.get("warnings", []) or []

        city_name = loc.get("city") or loc.get("name") or "Unknown"
        country_name = loc.get("country") or ""
        location_name = f"{city_name}, {country_name}" if country_name else city_name

        return {"location": location_name, "alerts": alerts}

    except Exception as e:
        return {"error": str(e)}


# Register all tools
tools = [get_current_weather, get_forecast, clothing_suggestion, weather_alerts]
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
SYSTEM_PROMPT = """You are a helpful weather assistant.
You can use the following tools:
- get_current_weather → for live temperature/windspeed
- get_forecast → for 1–7 day forecast
- clothing_suggestion → suggest clothes
- weather_alerts → check severe warnings
Always call the right tool depending on the user request.
If location is missing, ask for it.
"""

def call_model(state: AgentState, config: RunnableConfig):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = model.invoke(messages, config)
    return {"messages": [response], "number_of_steps": state.get("number_of_steps", 0) + 1}

def call_tool(state: AgentState):
    last = state["messages"][-1]
    outputs = []
    for tool_call in getattr(last, "tool_calls", []) or []:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        result = tools_by_name[tool_name].invoke(tool_args)
        outputs.append(ToolMessage(content=result, name=tool_name, tool_call_id=tool_id))
    return {"messages": outputs, "number_of_steps": state.get("number_of_steps", 0) + 1}


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
workflow.add_conditional_edges("llm", should_continue, {"continue": "tools", "end": END})
workflow.add_edge("tools", "llm")
graph = workflow.compile()


# --- Run Once ---
def run_once(prompt: str):
    global last_location, last_date
    intent = detect_intent(prompt)

    # Check for chat history request
    history_keywords = [
        "history", "previous question", "chat log", "show my questions", "show my chat"
    ]
    if any(k in prompt.lower() for k in history_keywords):
        if not chat_memory:
            return "No chat history yet."
        reply = "\nChat History:\n"
        for i, (u, a) in enumerate(chat_memory, 1):
            reply += f"{i}. You: {u}\n   Bot: {a}\n"
        return reply

    # --- Context-aware follow-up: fill missing location/date ---
    import re
    # If user says 'What about tomorrow?' or 'And in Galle?' etc.
    # --- Generic context-aware location for all tools that use a location ---
    city, country = parse_location(prompt)
    # If no city found, use last_location from memory (context-aware for all tools)
    if (not city or city.lower() in ["", "?", "there", "here", "it", "that", "this", "what about bob wall"]) and memory.get("last_location"):
        city, country = memory["last_location"], None
    # Normalize common misspellings for date words
    prompt_norm = prompt.lower().replace('tomorow', 'tomorrow').replace('tommorow', 'tomorrow').replace('todays', 'today')
    # If user says 'tomorrow', 'today', etc., extract date
    date_match = re.search(r"\b(today|tomorrow|tonight|this week|now)\b", prompt_norm, re.IGNORECASE)
    date_str = date_match.group(1).lower() if date_match else None
    if not date_str and last_date:
        date_str = last_date

    # Extract number of days if user asks for 'in X days', 'next X days', or 'forecast for X days'
    days = 3  # default
    days_match = re.search(r'(?:in|next|for|forecast for)\s*(\d+)\s*days?', prompt, re.IGNORECASE)
    if days_match:
        days = int(days_match.group(1))
        if days < 1:
            days = 1
        elif days > 7:
            days = 7
    # If the prompt is a follow-up (like 'what about tomorrow?'), use last_location for the location
    if (prompt.strip().lower() in ["what about tomorrow?", "what about today?", "what about tonight?", "what about this week?", "what about now?", "what about", "and tomorrow?", "and today?", "and tonight?", "and this week?", "and now?"] or not city or city.lower() in ["", "?", "there", "here", "it", "that", "this", "what about bob wall"]) and memory.get("last_location"):
        city = memory["last_location"]
    # For forecast, pass both city and date to the tool
    if intent == "forecast" and city:
        prompt = f"{city}{', ' + country if country else ''}"
    elif intent == "alerts" and city:
        prompt = f"{city}{', ' + country if country else ''}"
    elif city:
        prompt = city
        if date_str:
            prompt += f" {date_str}"

    try:
        # --- Current Weather ---
        if intent == "current_weather":
            data = get_current_weather.invoke({"location": prompt})
            if "need_country" in data:
                response = f"🌍 I couldn't find the location '{data['city']}'. Please specify the country as well (e.g., 'Moratuwa, Sri Lanka')."
            elif "error" in data:
                response = f"❌ {data['error']}"
            else:
                location_name = data.get("location")
                if not location_name:
                    city = data.get("city", "Unknown location")
                    country = data.get("country", "")
                    if country and country != "Unknown":
                        location_name = f"{city}, {country}"
                    else:
                        location_name = city
                temperature = data.get("temperature", "N/A")
                wind_speed = data.get("windspeed", "N/A")
                condition = data.get("weathercode", "N/A")
                humidity = data.get("humidity", "N/A")
                response = (
                    f"🌍 Weather in {location_name}:\n"
                    f"🌡️ Temperature: {temperature}°C, Condition: {condition}\n"
                    f"💨 Wind: {wind_speed} km/h\n"
                    f"💧 Humidity: {humidity}%"
                )
                # Update last_location and last_date
                memory["last_location"] = city
                memory["last_date"] = None
            chat_memory.append((prompt, response))
            memory["chat_memory"] = chat_memory
            save_memory(memory)
            return response

        # --- Clothing Suggestion ---
        elif intent == "clothing":
            data = clothing_suggestion.invoke({"location": prompt})
            if "need_country" in data:
                response = f"🌍 I couldn't find the location '{data['city']}'. Please specify the country as well (e.g., 'Moratuwa, Sri Lanka')."
            elif "error" in data:
                response = f"❌ {data['error']}"
            else:
                location_name = data.get("location", "Unknown location")
                advice = data.get("clothing_advice", "No suggestion available.")
                response = f"👕 Clothing Suggestion for {location_name}:\n{advice}"
                # Update last_location and last_date
                memory["last_location"] = city
                memory["last_date"] = None
            chat_memory.append((prompt, response))
            memory["chat_memory"] = chat_memory
            save_memory(memory)
            return response

        # --- Weather Alerts ---
        if intent == "forecast":
            # Always pass a valid location string
            location_str = prompt
            # If user asked for a specific day, adjust days accordingly (but allow user to override with explicit days)
            if date_str in ["tomorrow", "today"] and 'days_match' not in locals():
                days = 2
            data = get_forecast.invoke({"location": location_str, "days": days})
            if "error" in data:
                response = f"❌ {data['error']}"
            else:
                location_name = data.get("location", "Unknown location")
                forecast = data.get("forecast", {})
                times = forecast.get("time", [])
                temp_min = forecast.get("temperature_2m_min", [])
                temp_max = forecast.get("temperature_2m_max", [])
                precipitation = forecast.get("precipitation_sum", [])
                # Only show the day the user asked for
                if date_str == "tomorrow" and len(times) > 1:
                    reply = f"📅 Forecast for tomorrow in {location_name}:\n"
                    reply += (
                        f"🗓️ {times[1]}: "
                        f"🌡️ {temp_min[1]}°C - {temp_max[1]}°C, "
                        f"🌧️ {precipitation[1]} mm rain"
                    )
                elif date_str == "today" and len(times) > 0:
                    reply = f"📅 Forecast for today in {location_name}:\n"
                    reply += (
                        f"🗓️ {times[0]}: "
                        f"🌡️ {temp_min[0]}°C - {temp_max[0]}°C, "
                        f"🌧️ {precipitation[0]} mm rain"
                    )
                elif days_match:
                    # If user asked for N days, show N days
                    reply = f"📅 {days}-Day Forecast for {location_name}:\n"
                    for i in range(min(days, len(times))):
                        reply += (
                            f"\n🗓️ {times[i]}: "
                            f"🌡️ {temp_min[i]}°C - {temp_max[i]}°C, "
                            f"🌧️ {precipitation[i]} mm rain"
                        )
                else:
                    # If no specific day, show all available days
                    reply = f"📅 {len(times)}-Day Forecast for {location_name}:\n"
                    for i in range(len(times)):
                        reply += (
                            f"\n🗓️ {times[i]}: "
                            f"🌡️ {temp_min[i]}°C - {temp_max[i]}°C, "
                            f"🌧️ {precipitation[i]} mm rain"
                        )
                response = reply
                # Update last_location and last_date
                memory["last_location"] = city
                memory["last_date"] = date_str if 'date_str' in locals() else None
            chat_memory.append((prompt, response))
            memory["chat_memory"] = chat_memory
            save_memory(memory)
            return response
        elif intent == "alerts":
            # Always pass a valid location string
            location_str = prompt
            data = weather_alerts.invoke({"location": location_str})
            if "error" in data:
                response = f"❌ {data['error']}"
            else:
                location_name = data.get("location", "Unknown location")
                alerts = data.get("alerts", [])
                if alerts:
                    reply = f"🚨 Weather Alerts for {location_name}:\n"
                    for alert in alerts:
                        reply += f"- {alert}\n"
                else:
                    reply = f"✅ No weather alerts for {location_name}."
                response = reply
                # Update last_location and last_date
                memory["last_location"] = city
                memory["last_date"] = date_str if 'date_str' in locals() else None
            chat_memory.append((prompt, response))
            memory["chat_memory"] = chat_memory
            save_memory(memory)
            return response

        # --- Fallback for unrelated queries ---
        else:
            response = "❓ Sorry, I can only answer weather-related questions such as current weather, forecasts, clothing suggestions, or weather alerts for a location."
            chat_memory.append((prompt, response))
            memory["chat_memory"] = chat_memory
            save_memory(memory)
            return response

    except Exception as e:
        return f"❌ Error processing request: {str(e)}"

