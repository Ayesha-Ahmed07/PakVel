from datetime import datetime
from app.db.mongodb import trips_collection
from app.routes.weather_routes import fetch_openweather
from app.services.notifications import send_weather_alert
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY", "65760d5aa092b9e0f31fd1da2e762d3d")

import os

DANGEROUS_CONDITIONS = [
    "Thunderstorm",
    "Heavy Rain",
    "Snow",
    "Extreme Heat",
    "Fog"
]

async def check_active_trip_weather():
    active_trips = await trips_collection.find(
        {"status": "active"}
    ).to_list(None)

    for trip in active_trips:
        city = trip.get("destination")
        if not city:
            continue

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )

        weather = await fetch_openweather(url)

        condition = weather["weather"][0]["main"]

        if condition in DANGEROUS_CONDITIONS:
            # 🔔 Trigger notification
            await send_weather_alert(
                user_id=trip["user_id"],
                city=city,
                condition=condition
            )