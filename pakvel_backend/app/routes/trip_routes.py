from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime, timedelta
import logging
from app.db.mongodb import trips_collection, itineraries_collection, broker_itineraries_collection
from app.routes.auth_routes import get_current_user_obj

router = APIRouter(prefix="/trips", tags=["Trips"])

logger = logging.getLogger(__name__)

# ============================================================
# 1️⃣ CREATE TRIP (REUSE SAFE)
# ============================================================
@router.post("/")
async def create_trip(
    data: dict,
    current_user: dict = Depends(get_current_user_obj)
):
    """
    Create or reuse a trip.
    Used for:
    - AI itinerary → broker discussion
    - Broker pre-designed itinerary → discussion
    """

    # 🔎 LOG AUTH CONTEXT
    logger.info("CREATE_TRIP called")
    logger.info(f"Authenticated user ID: {current_user.get('_id')}")
    logger.info(f"User email: {current_user.get('email')}")

    itinerary_id = data.get("itinerary_id")
    trip_type = data.get("trip_type")  # "ai" | "broker"
    broker_id = data.get("broker_id")  # optional
    destination = data.get("destination")
    budget = data.get("budget")

    if not itinerary_id or not trip_type:
        raise HTTPException(
            status_code=400,
            detail="itinerary_id and trip_type are required"
        )

    # ✅ Validate itinerary id
    try:
        itinerary_obj_id = ObjectId(itinerary_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary_id")

    # ✅ Validate broker id (optional)
    broker_obj_id = None
    if broker_id:
        try:
            broker_obj_id = ObjectId(broker_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid broker_id")

    # ============================================================
    # 🔁 STEP 1: CHECK EXISTING TRIP (CRITICAL)
    # ============================================================
    existing_trip = await trips_collection.find_one({
        "user_id": ObjectId(current_user["_id"]),
        "itinerary_source_id": itinerary_obj_id,
        "trip_type": trip_type,
        
    })

    if existing_trip:
        logger.info(
            f"Trip reused | trip_id={existing_trip['_id']} | user={current_user['_id']}"
        )
        return {
            "trip_id": str(existing_trip["_id"]),
            "reused": True
        }

    # ============================================================
    # ➕ STEP 2: CREATE NEW TRIP
    # ============================================================
    trip_doc = {
        "user_id": ObjectId(current_user["_id"]),
        "trip_type": trip_type,                      # ai | broker
        "itinerary_source_id": itinerary_obj_id,     # ai itinerary OR broker itinerary
        "broker_id": broker_obj_id,                  # nullable
        "status": "chatting" if broker_obj_id else "draft",
        "destination": destination,
        "budget": budget,
        "chat_id": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await trips_collection.insert_one(trip_doc)

    logger.info(
        f"New trip created | trip_id={result.inserted_id} | user={current_user['_id']}"
    )

    return {
        "trip_id": str(result.inserted_id),
        "reused": False,
        "message": "Trip created successfully"
    }
#------------------------------------------------------------
#Route for showing detailed itinerary in broker modal whether it's AI or BROKER
#------------------------------------------------------------
@router.get("/{trip_id}/itinerary-context")
async def get_trip_itinerary_context(
    trip_id: str,
    current_user: dict = Depends(get_current_user_obj)
):
    # 1️⃣ Fetch trip
    trip = await trips_collection.find_one(
        {"_id": ObjectId(trip_id)}
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # 2️⃣ Access control (traveler OR broker)
    user_id = str(trip["user_id"])
    broker_id = str(trip.get("broker_id")) if trip.get("broker_id") else None

    if current_user["_id"] not in [user_id, broker_id]:
        raise HTTPException(status_code=403, detail="Not allowed")

    trip_type = trip.get("trip_type")
    source_id = trip.get("itinerary_source_id")

    if not source_id:
        raise HTTPException(status_code=400, detail="Trip has no itinerary source")

    # 3️⃣ Fetch itinerary based on trip type
    if trip_type in ["ai_self", "ai_broker"]:
        itinerary = await itineraries_collection.find_one(
            {"_id": ObjectId(source_id)}
        )
        source = "ai"

    elif trip_type == "broker":
        itinerary = await broker_itineraries_collection.find_one(
            {"_id": ObjectId(source_id)}
        )
        source = "broker"

    else:
        raise HTTPException(status_code=400, detail="Invalid trip type")

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # 4️⃣ Normalize ObjectIds
    itinerary["_id"] = str(itinerary["_id"])

    if itinerary.get("brokerId"):
        itinerary["brokerId"] = str(itinerary["brokerId"])

    return {
        "source": source,              # "ai" or "broker"
        "tripType": trip_type,
        "itinerary": itinerary
    }

# ============================================================
# 2️⃣ GET MY TRIPS (USER DASHBOARD)
# ============================================================
@router.get("/my")
async def get_my_trips(
    current_user: dict = Depends(get_current_user_obj)
):
    """
    Fetch all trips created by the logged-in user.
    Used for:
    - Active Trips
    - Past Trips
    """

    trips = await trips_collection.find(
        {"user_id": ObjectId(current_user["_id"])}
    ).sort("created_at", -1).to_list(None)

    response = []

    for t in trips:
        response.append({
            "trip_id": str(t["_id"]),
            "trip_type": t.get("trip_type"),
            "status": t.get("status"),
            "destination": t.get("destination"),
            "budget": t.get("budget"),
            "broker_id": str(t["broker_id"]) if t.get("broker_id") else None,
            "created_at": t.get("created_at")
        })

    return {
        "count": len(response),
        "trips": response
    }


# ============================================================
# 3️⃣ GET TRIP BY ID
# ============================================================
@router.get("/{trip_id}")
async def get_trip_by_id(
    trip_id: str,
    current_user: dict = Depends(get_current_user_obj)
):
    """
    Fetch a single trip.
    Used for:
    - Chat screen
    - Trip details
    - Weather alerts
    """

    try:
        trip_obj_id = ObjectId(trip_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid trip_id")

    trip = await trips_collection.find_one(
        {
            "_id": trip_obj_id,
            "user_id": ObjectId(current_user["_id"])
        }
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return {
        "trip_id": str(trip["_id"]),
        "trip_type": trip.get("trip_type"),
        "status": trip.get("status"),
        "destination": trip.get("destination"),
        "budget": trip.get("budget"),
        "itinerary_source_id": str(trip["itinerary_source_id"]),
        "broker_id": str(trip["broker_id"]) if trip.get("broker_id") else None,
        "chat_id": trip.get("chat_id"),
        "created_at": trip.get("created_at"),
        "updated_at": trip.get("updated_at")
    }

#=================================================================
#route for chat access - traveler and broker used by chat screen
#=================================================================
@router.get("/{trip_id}/chat-context")
async def get_trip_for_chat(
    trip_id: str,
    current_user: dict = Depends(get_current_user_obj)
):
    trip = await trips_collection.find_one(
        {"_id": ObjectId(trip_id)}
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    user_id = str(trip["user_id"])
    broker_id = str(trip.get("broker_id"))

    if (
        current_user["_id"] != user_id and
        current_user["_id"] != broker_id
    ):
        raise HTTPException(status_code=403, detail="Not allowed")

    trip["_id"] = str(trip["_id"])
    trip["user_id"] = str(trip["user_id"])
    if trip.get("broker_id"):
        trip["broker_id"] = str(trip["broker_id"])
    
    if trip.get("itinerary_source_id") and isinstance(trip["itinerary_source_id"], ObjectId):
        trip["itinerary_source_id"] = str(trip["itinerary_source_id"])

    if trip.get("chat_id") and isinstance(trip["chat_id"], ObjectId):
        trip["chat_id"] = str(trip["chat_id"])
    return trip


@router.get("/{trip_id}/chat-peer")
async def get_trip_chat_peer(
    trip_id: str,
    current_user: dict = Depends(get_current_user_obj)
):
    """
    Returns the OTHER user's CometChat UID for this trip
    """
    print("Trip ID:", trip_id)
    try:
        trip_obj_id = ObjectId(trip_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid trip_id")

    trip = await trips_collection.find_one({"_id": trip_obj_id})

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    current_user_id = ObjectId(current_user["_id"])

    # 🧠 Determine peer
    if trip["user_id"] == current_user_id:
        # Traveler → Broker
        if not trip.get("broker_id"):
            raise HTTPException(
                status_code=400,
                detail="Trip has no broker assigned yet"
            )

        peer_id = trip["broker_id"]
        peer_role = "broker"

    elif trip.get("broker_id") == current_user_id:
        # Broker → Traveler
        peer_id = trip["user_id"]
        peer_role = "traveler"

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not part of this trip"
        )

    return {
        "peerUid": str(peer_id),
        "peerRole": peer_role
    }

@router.patch("/{trip_id}/activate")
async def activate_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user_obj),
):
    print("🔵 Activate trip called")
    print("trip_id:", trip_id)
    print("current_user:", current_user)

    # 1️⃣ Validate trip ID
    try:
        trip_obj_id = ObjectId(trip_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid trip_id")

    # 2️⃣ Fetch trip
    trip = await trips_collection.find_one({"_id": trip_obj_id})
    print("Fetched trip:", trip)

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # 3️⃣ Ensure caller is TRAVELER
    try:
        current_user_id = ObjectId(current_user["_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    if trip["user_id"] != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Only traveler can activate the trip"
        )

    # 4️⃣ Ensure correct state
    if trip["status"] not in ["chatting", "draft"]:
        raise HTTPException(
            status_code=400,
            detail=f"Trip cannot be activated from {trip['status']} state"
        )

    # ============================================================
    # 🔹 5️⃣ Get itinerary days (AI or Broker)
    # ============================================================
    if trip["trip_type"] in ["ai_self", "ai_broker"]:
        itinerary = await itineraries_collection.find_one(
            {"_id": trip["itinerary_source_id"]}
        )
    else:
        itinerary = await broker_itineraries_collection.find_one(
            {"_id": trip["itinerary_source_id"]}
        )

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # supports both structures (AI: duration, Broker: days)
    days = itinerary.get("duration") or itinerary.get("duration_days") or 1

    # ============================================================
    # 🔹 6️⃣ Calculate dates
    # ============================================================
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=days + 2)
    grace_end_date = end_date + timedelta(days=4)

    # ============================================================
    # 🔹 7️⃣ Update trip (FULL STATE INIT)
    # ============================================================
    await trips_collection.update_one(
        {"_id": trip_obj_id},
        {"$set": {
            "status": "active",
            "start_date": start_date,
            "end_date": end_date,
            "grace_end_date": grace_end_date,

            # 🔥 Completion system fields
            "traveler_completed": False,
            "broker_completed": False,
            "completion_requested_at": None,
            "completed_at": None,

            "updated_at": datetime.utcnow()
        }}
    )

    # 8️⃣ Fetch updated trip
    updated_trip = await trips_collection.find_one({"_id": trip_obj_id})

    # 🔹 Normalize ObjectIds
    updated_trip["_id"] = str(updated_trip["_id"])
    updated_trip["user_id"] = str(updated_trip["user_id"])

    if updated_trip.get("broker_id"):
        updated_trip["broker_id"] = str(updated_trip["broker_id"])

    if updated_trip.get("itinerary_source_id"):
        updated_trip["itinerary_source_id"] = str(updated_trip["itinerary_source_id"])

    print("✅ Trip activated successfully")

    return {
        "message": "Trip activated successfully",
        "trip": updated_trip
    }

@router.get("/active/current")
async def get_current_active_trip(
    current_user: dict = Depends(get_current_user_obj)
):
    if current_user["role"] != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers allowed")

    trip = await trips_collection.find_one(
        {
            "user_id": ObjectId(current_user["_id"]),
            "status": { "$in": ["active", "completion_pending"] }
        },
        sort=[
            ("start_date", -1),   # preferred
            ("created_at", -1)    # fallback
        ]
    )

    if not trip:
        return {"hasActiveTrip": False}

    return {
        "hasActiveTrip": True,
        "trip": {
            "trip_id": str(trip["_id"]),
            "trip_type": trip.get("trip_type"),
            "status": trip.get("status"),
            "destination": trip.get("destination"),
            "budget": trip.get("budget"),

            "start_date": trip.get("start_date") or trip.get("created_at"),

            "itinerary_source_id": (
                str(trip["itinerary_source_id"])
                if trip.get("itinerary_source_id")
                else None
            ),

            "broker_id": (
                str(trip["broker_id"])
                if trip.get("broker_id")
                else None
            ),

            "chat_id": (
                str(trip["chat_id"])
                if trip.get("chat_id")
                else None
            ),

            "created_at": trip.get("created_at"),
            "updated_at": trip.get("updated_at"),
        }
    }

@router.patch("/{trip_id}/complete")
async def complete_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user_obj)
):
    try:
        trip_obj_id = ObjectId(trip_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid trip_id")

    trip = await trips_collection.find_one({"_id": trip_obj_id})

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    user_id = ObjectId(current_user["_id"])

    # ❌ Only allow after trip ended
    if trip["status"] not in ["completion_pending", "active"]:
        raise HTTPException(
            status_code=400,
            detail="Trip not eligible for completion"
        )

    update_fields = {}

    # ============================================================
    # 🔹 CASE 1: AI SELF TRIP
    # ============================================================
    if trip["trip_type"] == "ai_self":

        if trip["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not allowed")

        update_fields["status"] = "completed"
        update_fields["completed_at"] = datetime.utcnow()

        await trips_collection.update_one(
            {"_id": trip_obj_id},
            {"$set": update_fields}
        )

        return {"message": "Trip completed successfully"}

    # ============================================================
    # 🔹 CASE 2: BROKER TRIP (DUAL CONFIRMATION)
    # ============================================================

    if trip["user_id"] == user_id:
        # Traveler clicks
        update_fields["traveler_completed"] = True

    elif trip.get("broker_id") == user_id:
        # Broker clicks
        update_fields["broker_completed"] = True

    else:
        raise HTTPException(status_code=403, detail="Not part of trip")

    # Update current user's confirmation
    await trips_collection.update_one(
        {"_id": trip_obj_id},
        {"$set": update_fields}
    )

    # 🔄 Fetch updated trip
    updated_trip = await trips_collection.find_one({"_id": trip_obj_id})

    # ✅ Check both confirmations
    if updated_trip.get("traveler_completed") and updated_trip.get("broker_completed"):
        await trips_collection.update_one(
            {"_id": trip_obj_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow()
            }}
        )

        return {"message": "Trip fully completed"}

    return {"message": "Completion recorded. Waiting for other party."}

@router.get("/completed/review-pending")
async def get_review_pending_trip(
    current_user: dict = Depends(get_current_user_obj)
):
    if current_user["role"] != "traveler":
        raise HTTPException(status_code=403, detail="Only travelers allowed")

    user_id = ObjectId(current_user["_id"])

    # 1️⃣ Get completed trips
    trips = await trips_collection.find(
        {
            "user_id": user_id,
            "status": "completed"
        }
    ).sort("updated_at", -1).to_list(None)

    if not trips:
        return {"hasReviewPending": False}

    # 2️⃣ Check if already reviewed
    from app.db.mongodb import broker_reviews_collection

    for trip in trips:
        itinerary_id = trip.get("itinerary_source_id")

        if not itinerary_id:
            continue

        existing_review = await broker_reviews_collection.find_one({
            "userId": user_id,
            "itineraryId": itinerary_id
        })

        if not existing_review:
            # 👇 FOUND trip needing review
            return {
                "hasReviewPending": True,
                "trip": {
                    "trip_id": str(trip["_id"]),
                    "destination": trip.get("destination"),
                    "itinerary_source_id": str(itinerary_id),
                    "updated_at": trip.get("updated_at"),
                }
            }

    return {"hasReviewPending": False}