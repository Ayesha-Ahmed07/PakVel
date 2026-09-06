# app/db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import certifi  # ✅ add this

load_dotenv()  # Load variables from .env

# --- Load MongoDB connection info ---
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

# --- Create MongoDB client with SSL verification ---
try:
    # Use certifi's CA bundle to avoid SSL handshake issues
    client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where())
    database = client[DB_NAME]

    # Optional: define collections for easy access
    users_collection = database.get_collection("users")
    brokers_collection = database.get_collection("brokers")
    itineraries_collection = database.get_collection("itineraries")
    preferences_collection = database.get_collection("preferences")
    messages_collection = database.get_collection("messages")
    broker_itineraries_collection = database.get_collection("broker_itineraries")
    broker_collection = database.get_collection("brokers")
    weather_collection = database.get_collection("weather")
    broker_reviews_collection = database.get_collection("broker_reviews")
    trips_collection = database.get_collection("trips")
    broker_profiles_collection = database.get_collection("broker_profiles")




    async def create_indexes():
        await broker_reviews_collection.create_index(
            [("itineraryId", 1), ("userId", 1)],
            unique = True
        )
        await trips_collection.create_index(
            [
                ("user_id", 1),
                ("itinerary_source_id", 1),
                ("trip_type", 1),
            ],
            unique=True
        )

    async def test_connection():
        try:
            await client.admin.command('ping')
            print("✅ MongoDB connection successful!")
        except Exception as e:
            print("❌ MongoDB connection failed:", e)

except Exception as e:
    print("❌ MongoDB initialization error:", e)
