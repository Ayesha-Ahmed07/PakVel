from fastapi import APIRouter, HTTPException
import httpx
import os
from datetime import datetime
from bson import ObjectId
from app.db.mongodb import weather_collection, itineraries_collection

router = APIRouter(prefix="/weather", tags=["Weather"])

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY", "1110000XXXYYYZZZ")


# -------- 1) LIVE WEATHER FETCH -------- #
from datetime import timedelta

from datetime import datetime, timedelta
from fastapi import HTTPException
import httpx

@router.get("/live")
async def get_live_weather(city: str):
    city = city.strip().title()
    try:
        # 1️⃣ Check cache (last 10 minutes)
        cached = await weather_collection.find_one(
            {
                "city": city,
                "weather": {"$exists": True},
                "timestamp": {
                    "$gte": datetime.utcnow() - timedelta(minutes=10)
                }
            },
            sort=[("timestamp", -1)]
        )

        if cached:
            ts = cached.get("timestamp")

            return {
                "status": "success",
                "cached": True,
                "data": cached["weather"],
                "lastUpdatedAt": (
                    ts.isoformat() if isinstance(ts, datetime) else str(ts)
                )
            }

        # 2️⃣ Call OpenWeather only if cache miss
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)

        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=res.text)

        data = res.json()

        # 3️⃣ Store snapshot
        now = datetime.utcnow()
        await weather_collection.insert_one({
            "city": city,
            "weather": data,
            "timestamp": now
        })

        return {
            "status": "success",
            "cached": False,
            "data": data,
            "lastUpdatedAt": now.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print("❌ LIVE WEATHER ERROR:", e)
        raise HTTPException(
            status_code=500,
            detail="Internal weather service error"
        )

def serialize_mongo_doc(doc: dict):
    """
    Converts ObjectId → string so FastAPI can return the document safely.
    """
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        # also check nested fields
        if isinstance(value, dict):
            doc[key] = serialize_mongo_doc(value)
        if isinstance(value, list):
            doc[key] = [serialize_mongo_doc(v) if isinstance(v, dict) else v for v in value]
    return doc


async def fetch_openweather(url: str):
    """
    Helper to fetch weather data from OpenWeather API
    """
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    if res.status_code != 200:
        raise HTTPException(400, detail=data)

    return data


# -------- 2) GET WEATHER HISTORY -------- #
@router.get("/history/{city}")
async def get_weather_history(city: str):

    records = (
        await weather_collection.find({"city": city})
        .sort("timestamp", -1)
        .to_list(None)
    )

    # Convert each MongoDB document
    records = [serialize_mongo_doc(r) for r in records]

    return {
        "city": city,
        "count": len(records),
        "history": records,
    }

# -------- 3) FETCH WEATHER FOR ITINERARY -------- #
@router.post("/itinerary/{itinerary_id}")
async def fetch_itinerary_weather(itinerary_id: str):

    try:
        itinerary = await itineraries_collection.find_one({"_id": ObjectId(itinerary_id)})

        if not itinerary:
            raise HTTPException(404, "Itinerary not found")

        city = itinerary.get("destination")
        if not city:
            raise HTTPException(400, "Itinerary has no destination field")

        # Fetch live weather for itinerary city
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"

        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            data = res.json()

        if res.status_code != 200:
            raise HTTPException(400, data)

        # Save inside itinerary document
        await itineraries_collection.update_one(
            {"_id": itinerary["_id"]},
            {"$set": {"latestWeather": data, "weatherUpdatedAt": datetime.utcnow()}}
        )

        return {
            "status": "success",
            "destination": city,
            "message": "Weather updated for itinerary",
            "weather": data
        }

    except Exception as e:
        raise HTTPException(500, f"Weather update error: {str(e)}")
    
@router.get("/forecast")
async def get_forecast(city: str):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"

        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            data = res.json()

        if res.status_code != 200:
            raise HTTPException(400, data)

        # Store forecast snapshot
        record = {
            "city": city,
            "type": "forecast",
            "data": data,
            "timestamp": datetime.utcnow()
        }
        await weather_collection.insert_one(record)

        return {
            "status": "success",
            "message": "5-day forecast fetched & stored",
            "forecast": data
        }

    except Exception as e:
        raise HTTPException(500, f"Forecast fetch error: {str(e)}")
