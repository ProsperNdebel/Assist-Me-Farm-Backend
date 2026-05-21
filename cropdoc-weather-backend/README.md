# Farm Assistant Weather Backend

A FastAPI microservice that fetches weather data and delivers it to registered farmers via SMS. Built for the Assist-Me-Farm platform targeting Zimbabwean farmers.

## Overview

The service fetches real-time weather from OpenWeatherMap and sends structured SMS messages to farmers at scheduled intervals (6am and 6pm daily). Farmers register with their phone number and location, and the service handles the rest automatically.

## Features

- Farmer registration and management
- Real-time weather fetching via OpenWeatherMap
- Structured JSON SMS payloads (`FARM_ASSISTANT_WEATHER` format) parseable by the Android app
- Scheduled delivery at 6am and 6pm daily via APScheduler
- Manual trigger endpoints for testing

## Tech Stack

- **Framework:** FastAPI
- **Scheduler:** APScheduler (BackgroundScheduler)
- **Weather API:** OpenWeatherMap
- **SMS:** Twilio _(development only — see note below)_

---

## ⚠️ SMS Provider Notice

### Twilio is NOT used in production

Twilio's A2P (Application-to-Person) 10DLC registration requirements make it impractical for sending SMS to Zimbabwean numbers. International delivery to +263 numbers is unreliable without significant carrier vetting overhead.

**On launch, SMS will be migrated to [Africa's Talking](https://africastalking.com/)**, which has:

- Native support for Zimbabwean networks (Econet, NetOne, Telecel)
- Reliable local delivery with local shortcodes
- Competitive pricing for Zimbabwe
- An SDK that is already integrated elsewhere in the Assist-Me-Farm stack

The migration only requires swapping out the `send_weather_sms()` function — the rest of the service is provider-agnostic.

---

## Setup

### Prerequisites

- Python 3.9+
- OpenWeatherMap API key
- Twilio credentials _(dev/testing only)_

### Installation

```bash
pip install fastapi uvicorn twilio apscheduler python-dotenv requests
```

### Environment Variables

Create a `.env` file in the project root:

```env
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

OPENWEATHER_API_KEY=your_openweather_key
```

### Running

```bash
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

---

## API Reference

| Method   | Endpoint                          | Description                         |
| -------- | --------------------------------- | ----------------------------------- |
| `GET`    | `/`                               | Health check                        |
| `POST`   | `/register`                       | Register a farmer                   |
| `DELETE` | `/unregister/{phone_number}`      | Unregister a farmer                 |
| `GET`    | `/farmers`                        | List all registered farmers         |
| `POST`   | `/send-weather-now`               | Manually trigger SMS to all farmers |
| `POST`   | `/send-weather-to/{phone_number}` | Send SMS to a specific farmer       |

### Register a Farmer

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+263771234567", "location": "Harare, ZW"}'
```

### SMS Payload Format

The SMS body is a JSON string with the following structure:

```json
{
  "type": "FARM_ASSISTANT_WEATHER",
  "temperature": 24.5,
  "humidity": 68.0,
  "rainfall": 0.0,
  "windSpeed": 14.4,
  "forecast": "Partly cloudy",
  "location": "Harare, ZW"
}
```

The Android app parses this `FARM_ASSISTANT_WEATHER` payload to update the local weather display without requiring an internet connection on the device.

---

## Scheduler

Weather SMS is automatically sent to all registered farmers at **6:00 AM** and **6:00 PM** daily using APScheduler. To change the schedule, edit this line in `main.py`:

```python
scheduler.add_job(send_weather_to_all, "cron", hour="6,18")
```

---

## Production TODOs

- [ ] Replace Twilio with Africa's Talking SMS SDK
- [ ] Replace in-memory `farmers` dict with PostgreSQL (connect to main Assist-Me-Farm DB)
- [ ] Add authentication to registration endpoints
- [ ] Add retry logic for failed SMS deliveries
- [ ] Add logging to a persistent store
- [ ] Containerize with Docker for deployment on Render
