# app/routes/broker_routes.py
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime
from app.db.mongodb import (
    users_collection,
    broker_itineraries_collection,
    broker_collection,
    trips_collection,
    broker_reviews_collection,
)
from app.routes.auth_routes import get_current_user_obj

router = APIRouter(prefix="/broker", tags=["Broker"])

from typing import List

@router.post("/verify")
async def broker_verification(data: dict):
    """
    {
      "email": "...",
      "org_name": "...",
      "phone": "...",
      "cnic": "...",
      "license_number": "...",
      "tagline": "...",
      "years_of_experience": 5,
      "specialized_areas": ["Adventure and Nature Tourism", "Luxury Travel"]
    }
    """

    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    email= email.strip().lower()
    org_name = data.get("org_name")
    tagline = data.get("tagline")
    years_of_experience = data.get("years_of_experience")
    specialized_areas = data.get("specialized_areas")

    if not org_name:
        raise HTTPException(status_code=400, detail="Organization name is required")

    if not tagline:
        raise HTTPException(status_code=400, detail="Tagline is required")

    if not years_of_experience:
        raise HTTPException(status_code=400, detail="Years of experience is required")

    if not specialized_areas or not isinstance(specialized_areas, list):
        raise HTTPException(status_code=400, detail="Specialized areas are required")

    print("Incoming email", email)
    user = await users_collection.find_one({"email": email})
    print("User found:", user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["role"] != "broker":
        raise HTTPException(status_code=403, detail="User is not a broker")

    await users_collection.update_one(
        {"email": email},
        {"$set": {
            "org_name": org_name,
            "tagline": tagline,
            "years_of_experience": years_of_experience,
            "specialized_areas": specialized_areas,
            "verification_details": {
                "phone": data.get("phone"),
                "cnic": data.get("cnic"),
                "license_number": data.get("license_number"),
            },
            "can_login": True,
            "is_verified": False
        }}
    )

    return {"message": "Verification submitted successfully"}

# ------------------------------------------------------
# 1️⃣ CREATE ITINERARY
# ------------------------------------------------------
@router.post("/itineraries")
async def create_itinerary(data: dict, current_user: dict = Depends(get_current_user_obj)):

    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers can create itineraries")

    itinerary = {
        "brokerId": ObjectId(current_user["_id"]),
        "title": data["title"],
        "departure_location": data["departure_location"],
        "arrival_location": data["arrival_location"],
        "trip_locations": data.get("trip_locations", []),

        "duration_days": data["duration_days"],
        "price_per_person": data["price_per_person"],
        "description": data["description"],
        "days": data.get("days", []),
        "cover_image": data.get("cover_image", ""),

        "contact_info": {
            "phone": data.get("phone", ""),
            "whatsapp": data.get("whatsapp", ""),
            "email": data.get("email", "")
        },

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_published": False,
    }

    result = await broker_itineraries_collection.insert_one(itinerary)

    return {
        "message": "Itinerary created successfully",
        "id": str(result.inserted_id)
    }

# ------------------------------------------------------
# 2️⃣ UPDATE ITINERARY
# ------------------------------------------------------
# ------------------------------------------------------
# UPDATE ITINERARY (FINAL VERSION)
# ------------------------------------------------------
@router.put("/update-itineraries/{itinerary_id}")
async def update_itinerary(
    itinerary_id: str,
    updates: dict,
    current_user: dict = Depends(get_current_user_obj)
):

    # Check role
    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers allowed")

    # Fetch itinerary
    itinerary = await broker_itineraries_collection.find_one(
        {"_id": ObjectId(itinerary_id)}
    )

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # Ownership validation
    if str(itinerary["brokerId"]) != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this")

    # Auto-update timestamp
    updates["updated_at"] = datetime.utcnow()

    # Apply update
    await broker_itineraries_collection.update_one(
        {"_id": ObjectId(itinerary_id)},
        {"$set": updates}
    )

    # Fetch updated itinerary
    updated_itinerary = await broker_itineraries_collection.find_one(
        {"_id": ObjectId(itinerary_id)}
    )

    # Convert ObjectIds → strings
    updated_itinerary["_id"] = str(updated_itinerary["_id"])
    updated_itinerary["brokerId"] = str(updated_itinerary["brokerId"])

    return {
        "message": "Itinerary updated successfully",
        "itinerary": updated_itinerary
    }

# ------------------------------------------------------
# 3️⃣ DELETE ITINERARY
# ------------------------------------------------------
@router.delete("/delete-itineraries/{itinerary_id}")
async def delete_itinerary(itinerary_id: str, current_user: dict = Depends(get_current_user_obj)):

    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers allowed")

    itinerary = await broker_itineraries_collection.find_one({"_id": ObjectId(itinerary_id)})

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    if str(itinerary["brokerId"]) != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    await broker_itineraries_collection.delete_one({"_id": ObjectId(itinerary_id)})

    return {"message": "Itinerary deleted successfully"}


# ------------------------------------------------------
# 6️⃣ GET DETAILED ITINERARY
# ------------------------------------------------------
@router.get("/itineraries/{itinerary_id}")
async def get_itinerary_detail(itinerary_id: str):
    try:
        obj_id = ObjectId(itinerary_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary id")

    itinerary = await broker_itineraries_collection.find_one({"_id": obj_id})
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # Convert ObjectIds
    itinerary["_id"] = str(itinerary["_id"])
    broker_id = itinerary.get("brokerId")

    if broker_id:
        itinerary["brokerId"] = str(broker_id)

        # 🔹 Fetch broker org name + contact info
        broker = await users_collection.find_one(
            {"_id": broker_id},
            {"org_name": 1}
        )

        broker_contact = await broker_collection.find_one(
            {"brokerId": broker_id},
            {"_id": 0, "phone": 1, "whatsapp": 1, "email": 1}
        )

        itinerary["broker_org_name"] = broker.get("org_name", "Independent Broker") if broker else "Independent Broker"
    else:
        broker_contact = None
        itinerary["broker_org_name"] = "Independent Broker"

    itinerary["contact_info"] = broker_contact or {
        "phone": "",
        "whatsapp": "",
        "email": ""
    }

    itinerary.setdefault("departure_location", "")
    itinerary.setdefault("arrival_location", "")
    itinerary.setdefault("trip_locations", [])

    return {"itinerary": itinerary}

# ------------------------------------------------------
# 4️⃣ GET ALL ITINERARIES OF LOGGED-IN BROKER
# ------------------------------------------------------
@router.get("/show-itineraries")
async def get_broker_itineraries(current_user: dict = Depends(get_current_user_obj)):

    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers allowed")

    itineraries = await broker_itineraries_collection.find(
        {"brokerId": ObjectId(current_user["_id"])}
    ).to_list(length=None)

    for i in itineraries:
        i["_id"] = str(i["_id"])
        i["brokerId"] = str(i["brokerId"])

    return itineraries

# ------------------------------------------------------
# GLOBAL CONTACT INFO ROUTE (Create/Update)
# ------------------------------------------------------
@router.put("/contact-info")
async def update_broker_contact_info(
    data: dict,
    current_user: dict = Depends(get_current_user_obj)
):

    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers allowed")

    broker_id = ObjectId(current_user["_id"])

    contact_info = {
        "phone": data.get("phone", ""),
        "whatsapp": data.get("whatsapp", ""),
        "email": data.get("email", ""),
        "updated_at": datetime.utcnow()
    }

    # Check if record exists
    existing = await broker_collection.find_one(
        {"brokerId": broker_id}
    )

    if existing:
        # Update existing contact info
        await broker_collection.update_one(
            {"brokerId": broker_id},
            {"$set": contact_info}
        )
    else:
        # Create new contact info record
        await broker_collection.insert_one(
            { "brokerId": broker_id, **contact_info }
        )

    # ALSO update all itineraries with new contact info
    await broker_itineraries_collection.update_many(
        {"brokerId": broker_id},
        {"$set": {"contact_info": contact_info}}
    )

    return {"message": "Contact info updated for broker and all itineraries"}
# ------------------------------------------------------
# GET BROKER CONTACT INFO
# ------------------------------------------------------
@router.get("/contact-info")
async def get_broker_contact_info(
    current_user: dict = Depends(get_current_user_obj)
):

    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers allowed")

    broker_id = ObjectId(current_user["_id"])

    info = await broker_collection.find_one(
        {"brokerId": broker_id}
    )

    if not info:
        return {
            "phone": "",
            "whatsapp": "",
            "email": "",
        }

    info["_id"] = str(info["_id"])
    info["brokerId"] = str(info["brokerId"])

    return info
# ------------------------------------------------------
# GLOBAL CONTACT INFO ROUTE (Create/Update)
# ------------------------------------------------------
@router.put("/contact-info")
async def update_broker_contact_info(
    data: dict,
    current_user: dict = Depends(get_current_user_obj)
):

    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers allowed")

    broker_id = ObjectId(current_user["_id"])

    contact_info = {
        "phone": data.get("phone", ""),
        "whatsapp": data.get("whatsapp", ""),
        "email": data.get("email", ""),
        "updated_at": datetime.utcnow()
    }

    # Check if record exists
    existing = await broker_collection.find_one(
        {"brokerId": broker_id}
    )

    if existing:
        # Update existing contact info
        await broker_collection.update_one(
            {"brokerId": broker_id},
            {"$set": contact_info}
        )
    else:
        # Create new contact info record
        await broker_collection.insert_one(
            { "brokerId": broker_id, **contact_info }
        )

    # ALSO update all itineraries with new contact info
    await broker_itineraries_collection.update_many(
        {"brokerId": broker_id},
        {"$set": {"contact_info": contact_info}}
    )

    return {"message": "Contact info updated for broker and all itineraries"}

from typing import Optional
from bson import ObjectId
from app.db.mongodb import (
    broker_itineraries_collection,
    broker_reviews_collection
)

@router.get("/public/itineraries")
async def get_all_published_itineraries(
    city: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_rating: Optional[float] = None,
):
    filters = []

    # ✅ Published OR legacy docs
    filters.append({
        "$or": [
            {"is_published": True},
            {"is_published": {"$exists": False}}
        ]
    })

    # ✅ City filter
    if city:
        filters.append({
            "$or": [
                {"arrival_location": {"$regex": city, "$options": "i"}},
                {
                    "trip_locations": {
                        "$elemMatch": {
                            "$regex": city,
                            "$options": "i"
                        }
                    }
                }
            ]
        })

    # ✅ Budget filter
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price

        filters.append({"price_per_person": price_query})

    query = {"$and": filters} if filters else {}

    itineraries = await broker_itineraries_collection.find(query).to_list(None)

    enriched = []

    for it in itineraries:
        itinerary_id = it["_id"]

        # ⭐ Aggregate reviews
        pipeline = [
            {"$match": {"itineraryId": itinerary_id}},
            {
                "$group": {
                    "_id": "$itineraryId",
                    "avgRating": {"$avg": "$rating"},
                    "reviewCount": {"$sum": 1}
                }
            }
        ]

        rating_data = await broker_reviews_collection.aggregate(pipeline).to_list(1)

        avg_rating = round(rating_data[0]["avgRating"], 1) if rating_data else 0
        review_count = rating_data[0]["reviewCount"] if rating_data else 0

        # ⭐ Rating filter
        if min_rating is not None and avg_rating < min_rating:
            continue

        # 🔹 Fetch broker org name
        broker = await users_collection.find_one(
            {"_id": it["brokerId"]},
            {"org_name": 1}
        )

        it["_id"] = str(it["_id"])
        it["brokerId"] = str(it["brokerId"])
        it["avgRating"] = avg_rating
        it["reviewCount"] = review_count
        it["broker_org_name"] = broker.get("org_name", "Independent Broker") if broker else "Independent Broker"

        enriched.append(it)

    return enriched

# ------------------------------------------------------
# 📥 BROKER INCOMING REQUESTS (CHAT INBOX)
# ------------------------------------------------------

@router.get("/incoming-requests")
async def get_broker_incoming_requests(
    current_user: dict = Depends(get_current_user_obj)
):
    # 🔐 Only brokers allowed
    if current_user["role"] != "broker":
        raise HTTPException(status_code=403, detail="Only brokers allowed")

    broker_id = ObjectId(current_user["_id"])

    # 🔎 Fetch trips assigned to this broker
    trips_cursor = trips_collection.find(
        {
            "broker_id": broker_id,
            "status": {"$in": ["chatting", "active", "completion_pending"]}
        }
    ).sort("updated_at", -1)

    trips = await trips_cursor.to_list(length=None)

    response = []

    for trip in trips:
        # 👤 Fetch traveler info
        traveler = await users_collection.find_one(
            {"_id": trip["user_id"]},
            {"full_name": 1}
        )

        response.append({
            "tripId": str(trip["_id"]),
            "travelerName": traveler.get("full_name", "Traveler") if traveler else "Traveler",
            "destination": trip.get("destination", ""),
            "budget": trip.get("budget", 0),
            "status": trip.get("status"),
            "tripType": trip.get("trip_type"),
            "lastMessage": trip.get("last_message"),  # may be None
            "updatedAt": trip.get("updated_at")
        })

    return response

@router.get("/marketplace")
async def broker_marketplace():

    brokers = await users_collection.find(
        {
            "role": "broker",
            "can_login": True
        }
    ).to_list(None)

    result = []

    for broker in brokers:

        broker_id = broker["_id"]  # ObjectId

        # ✅ Count itineraries
        total_itineraries = await broker_itineraries_collection.count_documents({
            "brokerId": broker_id
        })

        # ✅ Get reviews
        reviews = await broker_reviews_collection.find({
            "brokerId": broker_id
        }).to_list(None)

        review_count = len(reviews)

        if review_count > 0:
            avg_rating = sum(r.get("rating", 0) for r in reviews) / review_count
        else:
            avg_rating = 0

        result.append({
            "broker_id": str(broker_id),
            "org_name": broker.get("org_name", "Unnamed Broker"),
            "tagline": broker.get("tagline", ""),
            "years_of_experience": broker.get("years_of_experience", 0),
            "specialized_areas": broker.get("specialized_areas", []),
            "rating": round(avg_rating, 1),
            "review_count": review_count,
            "total_itineraries": total_itineraries,
        })

    # 🔥 Sort by rating (descending)
    result.sort(key=lambda x: x["rating"], reverse=True)

    return result