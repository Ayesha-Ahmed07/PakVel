from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime

from app.db.mongodb import (
    broker_reviews_collection,
    broker_itineraries_collection,
    itineraries_collection,
)
from app.routes.auth_routes import get_current_user_obj
from app.db.mongodb import broker_reviews_collection, users_collection


router = APIRouter(prefix="/reviews", tags=["Reviews"])

from pymongo.errors import DuplicateKeyError




@router.post("/")
async def submit_review(
    data: dict,
    current_user: dict = Depends(get_current_user_obj)
):
    # ---------- Validation ----------
    itinerary_id = data.get("itineraryId")
    rating = data.get("rating")
    comment = data.get("comment", "")

    if not itinerary_id or rating is None:
        raise HTTPException(
            status_code=400,
            detail="itineraryId and rating are required"
        )

    try:
        rating = int(rating)
    except ValueError:
        raise HTTPException(status_code=400, detail="Rating must be an integer")

    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be between 1 and 5"
        )

    # ---------- Validate itinerary ----------
    try:
        itinerary_obj_id = ObjectId(itinerary_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itineraryId")

    itinerary = await broker_itineraries_collection.find_one(
        {"_id": itinerary_obj_id}
    )
    if not itinerary:
        itinerary = await itineraries_collection.find_one({"_id": itinerary_obj_id})

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    # ❌ Prevent reviewing unpublished itineraries
    if not itinerary.get("is_published", False):
        raise HTTPException(
            status_code=400,
            detail="Cannot review an unpublished itinerary"
        )

    # ❌ Prevent broker reviewing their own itinerary
    if itinerary["brokerId"] == ObjectId(current_user["_id"]):
        raise HTTPException(
            status_code=403,
            detail="You cannot review your own itinerary"
        )

    # ---------- Create review ----------
    review_doc = {
        "itineraryId": itinerary_obj_id,
        "brokerId": itinerary.get("brokerId"),
        "userId": ObjectId(current_user["_id"]),
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow()
    }

    try:
        await broker_reviews_collection.insert_one(review_doc)
    except DuplicateKeyError:
        # Unique index (userId + itineraryId) violation
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this itinerary"
        )

    return {
        "message": "Review submitted successfully"
    }

#fetch all reviews
@router.get("/itinerary/{itinerary_id}")
async def get_reviews_for_itinerary(itinerary_id: str):
    try:
        itinerary_obj_id = ObjectId(itinerary_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary id")

    reviews = await broker_reviews_collection.find(
        {"itineraryId": itinerary_obj_id}
    ).to_list(None)

    response = []

    for r in reviews:
        # fetch user name (optional but recommended)
        user = await users_collection.find_one(
            {"_id": r["userId"]},
            {"_id": 0, "full_name": 1, "email": 1}
        )

        response.append({
            "rating": r["rating"],
            "comment": r.get("comment", ""),
            "user": user.get("full_name") if user else "Anonymous",
            "created_at": r["created_at"]
        })

    return {
        "count": len(response),
        "reviews": response
    }

@router.get("/broker-reviews")
async def get_all_reviews_for_broker(
    current_user: dict = Depends(get_current_user_obj)
):
    try:
        broker_id = ObjectId(current_user["_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid broker ID")

    # ============================================================
    # ✅ Fetch ALL reviews directly using brokerId
    # ============================================================
    reviews = await broker_reviews_collection.find(
        {"brokerId": broker_id}
    ).sort("created_at", -1).to_list(None)

    response = []

    for r in reviews:
        user = await users_collection.find_one(
            {"_id": r["userId"]},
            {"_id": 0, "full_name": 1}
        )

        response.append({
            "rating": r["rating"],
            "comment": r.get("comment", ""),
            "user": user.get("full_name") if user else "Anonymous",
            "created_at": r["created_at"],
            "itinerary_id": str(r["itineraryId"])
        })

    return {
        "count": len(response),
        "reviews": response
    }