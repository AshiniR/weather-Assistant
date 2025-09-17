import os
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "data/memory.json")

geolocator = Nominatim(user_agent="weather-app")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.7,
    max_retries=2,
    google_api_key=api_key,
)

SYSTEM_PROMPT = (
    "You are a helpful weather assistant.\n"
    "You can use the following tools:\n"
    "- get_current_weather → for live temperature/windspeed\n"
    "- get_forecast → for 1–7 day forecast\n"
    "- clothing_suggestion → suggest clothes\n"
    "- weather_alerts → check severe warnings\n"
    "Always call the right tool depending on the user request.\n"
    "If location is missing, ask for it.\n"
    'Before calling a tool, acknowledge it by saying something like "Let me check that..."\n'
)