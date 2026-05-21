from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import requests
import json
import os

load_dotenv()

app = FastAPI(title="CropDoc Weather Backend")

# Twilio setup
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

# In-memory farmer registry (replace with DB for production)
farmers = {}

# ── Models ────────────────────────────────────────────────────────────────────

class FarmerRegistration(BaseModel):
    phone_number: str
    location: str

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "CropDoc Weather Backend running"}

@app.post("/register")
def register_farmer(farmer: FarmerRegistration):
    """Register a farmer to receive weather updates."""
    farmers[farmer.phone_number] = farmer.location
    print(f"Registered farmer: {farmer.phone_number} at {farmer.location}")
    return {"status": "registered", "phone": farmer.phone_number, "location": farmer.location}

@app.delete("/unregister/{phone_number}")
def unregister_farmer(phone_number: str):
    """Unregister a farmer from weather updates."""
    if phone_number in farmers:
        del farmers[phone_number]
        return {"status": "unregistered"}
    raise HTTPException(status_code=404, detail="Farmer not found")

@app.get("/farmers")
def list_farmers():
    """List all registered farmers."""
    return {"farmers": farmers}

@app.post("/send-weather-now")
def send_weather_now():
    """Manually trigger weather SMS to all registered farmers."""
    results = send_weather_to_all()
    return {"status": "sent", "results": results}

@app.post("/send-weather-to/{phone_number}")
def send_weather_to_one(phone_number: str):
    """Send weather SMS to a specific farmer."""
    if phone_number not in farmers:
        raise HTTPException(status_code=404, detail="Farmer not registered")
    location = farmers[phone_number]
    result = send_weather_sms(phone_number, location)
    return result

# ── Weather logic ─────────────────────────────────────────────────────────────

def get_weather(location: str) -> dict:
    """Fetch weather from OpenWeatherMap."""
    url = f"https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": OPENWEATHER_KEY,
        "units": "metric"
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Weather API error: {response.status_code} — {response.text}")
    return response.json()

def format_weather_sms(weather_data: dict, location: str) -> str:
    """Format weather data into CROPDOC_WEATHER SMS format."""
    main = weather_data.get("main", {})
    wind = weather_data.get("wind", {})
    rain = weather_data.get("rain", {})
    description = weather_data.get("weather", [{}])[0].get("description", "Clear")

    payload = {
        "type": "CROPDOC_WEATHER",
        "temperature": round(main.get("temp", 0), 1),
        "humidity": round(main.get("humidity", 0), 1),
        "rainfall": round(rain.get("1h", 0.0), 1),
        "windSpeed": round(wind.get("speed", 0) * 3.6, 1),  # m/s to km/h
        "forecast": description.capitalize(),
        "location": location
    }
    return json.dumps(payload)

def send_weather_sms(phone_number: str, location: str) -> dict:
    """Fetch weather and send SMS to farmer."""
    try:
        weather_data = get_weather(location)
        sms_body = format_weather_sms(weather_data, location)

        message = twilio_client.messages.create(
            body=sms_body,
            from_=TWILIO_NUMBER,
            to=phone_number
        )

        print(f"Weather SMS sent to {phone_number}: {message.sid}")
        return {"status": "success", "phone": phone_number, "sid": message.sid}

    except Exception as e:
        print(f"Failed to send weather to {phone_number}: {e}")
        return {"status": "error", "phone": phone_number, "error": str(e)}

def send_weather_to_all() -> list:
    """Send weather SMS to all registered farmers."""
    results = []
    for phone, location in farmers.items():
        result = send_weather_sms(phone, location)
        results.append(result)
    return results

# ── Scheduler ─────────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler()
scheduler.add_job(send_weather_to_all, "cron", hour="6,18")  # 6am and 6pm daily
scheduler.start()

print("CropDoc Weather Backend started. Scheduler running at 6am and 6pm daily.")