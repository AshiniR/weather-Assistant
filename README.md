# 🌦️ Weather Assistant

An AI-powered conversational assistant that provides current weather, forecasts, clothing suggestions, and severe weather alerts for any city.
It remembers chat history, last location, and last date for context-aware follow-ups (e.g., “What about tomorrow?”).

## ✨ Features

* 🌤️ Current Weather – Live temperature, windspeed, humidity, condition.
* 📅 Forecasts – Up to 7-day daily forecasts with min/max temperatures & precipitation.
* 👕 Clothing Suggestions – Outfit advice depending on temperature & wind.
* 🚨 Severe Weather Alerts – Warnings for storms, floods, heatwaves, etc.
* 🧠 Memory – Remembers last location/date for follow-ups like:
      “What about tomorrow?”
* 💬 Friendly Chat – Responds to greetings and farewells.
* 📝 Chat History – Retrieve previous Q&A logs.

## 🛠️ Tech Stack

* Python 3.10+
* LangGraph + LangChain – Orchestrating model & tools
* Google Gemini 2.5 Pro – LLM backend (ChatGoogleGenerativeAI)
* Open-Meteo API – Weather & forecast data
* Geopy (Nominatim) – Geocoding cities into latitude/longitude
* dotenv – Manage API keys via .env
* Persistent Memory – Saved in memory.json

# 📂 Project Structure
```bash
weather-Assistant/
│── weather_agent.py       
│── weather_ui.py         
│── memory.json           
│── requirements.txt      
│── .env                  
│── README.md             
│── .gitignore            
└── .venv/    
```
# ⚙️ Setup
1. Clone the repo
```bash
git clone https://github.com/your-username/weather-assistant.git
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

▶️ Usage

Run the assistant:
```bash
streamlit run weather_ui.py
```

Then chat naturally:
```bash
* 👤 User: What's the weather in Colombo?
* 🤖 Bot: 🌍 Weather in Colombo:
        🌡️ Temperature: 27°C, Condition: Clear Sky
        💨 Wind: 16 km/h
        💧 Humidity: 70%

* 👤 User: What about tomorrow?
* 🤖 Bot: 📅 Forecast for tomorrow in Colombo:
        🗓️ 2025-08-25: 🌡️ 26°C - 31°C, 🌧️ 5 mm rain

* 👤 User: What should I wear in Berlin today?
* 🤖 Bot: 👕 Clothing Suggestion for Berlin:
        Wear a light jacket or sweater.
```
## 📖 Example Interactions

* Current Weather → “What’s the weather in New York?”
* Forecast → “3-day forecast for London” / “What about tomorrow?”
* Alerts → “Any weather warnings in Tokyo?”
* Clothing Advice → “What should I wear in Paris today?”
*  Memory → “And in Galle?” (uses last query context)
* History → “Show my chat history”

## 👨‍💻 Author

Developed by Ashini Dhananjana ✨
