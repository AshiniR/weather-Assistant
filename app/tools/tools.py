from langchain_core.tools import tool
import requests

from utils.weather import parse_location, get_location
from models.weatherInput import WeatherInput
from models.forecastInput import ForecastInput
from models.clothingInput import ClothingInput
from models.alertInput import AlertInput

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
