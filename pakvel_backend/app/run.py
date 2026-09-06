# app/run.py
import uvicorn
from fastapi import FastAPI
from app.db.mongodb import test_connection, create_indexes as create_review_indexes
from app.routes import auth_routes, broker_routes, traveler_routes, weather_routes, review_routes, trip_routes, chat_routes
from app.core.schedular import scheduler, trip_status_job

app = FastAPI()
from app.db.mongodb import  itineraries_collection
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all devices
    allow_credentials=True,
    allow_methods=["*"],  # allow POST, GET, OPTIONS, DELETE, PUT
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("🚀 App startup initiated...")

    # 1️⃣ Test MongoDB connection
    await test_connection()

    # 2️⃣ Create itinerary unique hash index
    await itineraries_collection.create_index(
        "unique_hash",
        unique=True
    )

    # 3️⃣ Create broker review indexes
    await create_review_indexes()

    # ====================================================
    # 🔥 4️⃣ START SCHEDULER (ADD THIS PART)
    # ====================================================
    scheduler.add_job(
        trip_status_job,
        "cron",
        hour = 0,
        minute=0
    )
    scheduler.start()

    print("✅ Scheduler started...")

    print("✅ All startup tasks completed.")

#authentication router
app.include_router(auth_routes.router)
app.include_router(broker_routes.router)
app.include_router(traveler_routes.router)
app.include_router(weather_routes.router)
app.include_router(review_routes.router)
app.include_router(trip_routes.router)
app.include_router(chat_routes.router)




@app.get("/")
async def root():
    return {"message": "FastAPI connected successfully to MongoDB Atlas!"}

#tester
@app.get("/ping")
async def ping():
    return {"message": "pong!"}

##another tester
@app.get("/debug/itineraries")
async def debug_itineraries():
    all_its = await itineraries_collection.find().to_list(None)
    return all_its

if __name__ == "__main__":
    uvicorn.run("app.run:app", host="0.0.0.0", port=8000, reload=True)