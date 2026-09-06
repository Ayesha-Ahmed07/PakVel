from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from app.db.mongodb import trips_collection

scheduler = AsyncIOScheduler(timezone="Asia/Karachi")


async def trip_status_job():
    now = datetime.utcnow()

    print("⏱ Running trip status job at:", now)

    # =========================================
    # 🔹 CASE 1: ACTIVE → COMPLETION_PENDING
    # =========================================
    result1 = await trips_collection.update_many(
        {
            "status": "active",
            "end_date": {"$lt": now}
        },
        {
            "$set": {
                "status": "completion_pending",
                "completion_requested_at": now
            }
        }
    )

    print("Moved ACTIVE → completion_pending:", result1.modified_count)

    # =========================================
    # 🔹 CASE 2: COMPLETION_PENDING → COMPLETED
    # =========================================
    result2 = await trips_collection.update_many(
        {
            "status": "completion_pending",
            "grace_end_date": {"$lt": now}
        },
        {
            "$set": {
                "status": "completed",
                "completed_at": now
            }
        }
    )

    print("Moved completion_pending → completed:", result2.modified_count)