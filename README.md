# 🌦️ Weather Assistant

A intelligent weather chatbot built with LangChain, LangGraph, and Streamlit that provides current weather information, forecasts, clothing suggestions, and weather alerts.

##  Features

* 🌤️ Current Weather: Get real-time weather for any location
* 📅 Weather Forecasts: Multi-day weather predictions (1-7 days)
* 👕 Clothing Suggestions: AI-powered outfit recommendations based on weather
* 🚨 Weather Alerts: Severe weather warnings and advisories
* 💬 Context-Aware Chat: Remember previous locations and follow-up questions
* 💾 Persistent Memory: Chat history saved across sessions
* 🌐 Web Interface: Clean Streamlit UI for easy interaction

## 🛠️ Tech Stack

### Backend
Python 3.8+ - Core programming language 
LangChain - AI application framework 
LangGraph - Graph-based conversation flow 
Google Gemini 2.5 Pro - Large Language Model 
Pydantic - Data validation and serialization 

### APIs & Data Sources
Open-Meteo API - Weather data (free, no API key required) 
Nominatim (OpenStreetMap) - Geocoding services 
Geopy - Geographic location handling

### Frontend
Streamlit - Web UI framework 

### Development Tools
python-dotenv - Environment variable management 
Requests - HTTP client for API calls 
  

# 📂 Project Structure
```bash
weather-Assistant/
│── app/
│ ├── core/
│ │ ├── init.py
│ │ ├── config.py
│ │
│ ├── models/
│ │ ├── init.py
│ │ ├── agentState.py
│ │ ├── alertInput.py
│ │ ├── clothingInput.py
│ │ ├── forecastInput.py
│ │ └── weatherInput.py
│ │
│ ├── tools/
│ │ ├── init.py
│ │ └── tools.py
│ │
│ ├── utils/
│ │ ├── init.py
│ │ └── weather.py
│ │
│ ├── init.py
| ├── weather_agent.py
│ └── weather_agentUI.py
│
├── .env
├── .gitignore
├── README.md
├── requirements.txt
└── venv/ # Virtual environment (not mandatory to commit)  
```
# ⚙️ Setup
1. Clone the repo
```bash
git clone https://github.com/AshiniR/weather-assistant.git
cd weather-assistant
```
3. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

5. Install dependencies
```bash
pip install -r requirements.txt
```

7. Add .env file

Create a .env file in the project root:
```bash
GEMINI_API_KEY=your_google_gemini_api_key
```

## ▶️ Usage

Run the assistant:
```bash
streamlit run app/weather_agentUI.py
```

## 📖 Example Queries
"What's the weather in Paris?"
"Give me a 3-day forecast for Tokyo"
"What should I wear in London today?"
"Are there any weather warnings in New York?"
"What about tomorrow?" (follow-up context)

## Memory Features
* Session Memory: Remembers conversation within current session
* Context Awareness: Understands follow-up questions like "What about tomorrow?"
* Location Context: Remembers last mentioned location for follow-ups

##  Author

Developed by Ashini Dhananjana ✨
