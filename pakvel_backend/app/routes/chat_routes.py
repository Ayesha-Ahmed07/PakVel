from fastapi import APIRouter, Depends, HTTPException 
import requests
import os
from bson import ObjectId

from app.routes.auth_routes import get_current_user_obj
from app.services.cometchat_services import ensure_cometchat_user
from app.db.mongodb import trips_collection, users_collection, brokers_collection

router = APIRouter(prefix="/chat", tags=["Chat"])

COMETCHAT_APP_ID = os.getenv("COMETCHAT_APP_ID")
COMETCHAT_REGION = os.getenv("COMETCHAT_REGION")
COMETCHAT_AUTH_KEY = os.getenv("COMETCHAT_AUTH_KEY")


@router.post("/token")
async def get_chat_token(current_user: dict = Depends(get_current_user_obj)):
    print("CHAT routes loaded")
    user_id = str(current_user["_id"])
    name = current_user.get("full_name", "User")

    # 1️⃣ Ensure CURRENT user exists in CometChat
    ensure_cometchat_user(user_id, name)

    # 2️⃣ Find active trip for this user
    trip = await trips_collection.find_one({
        "$or": [
            {"user_id": ObjectId(user_id)},
            {"broker_id": ObjectId(user_id)}
        ],
        "status": {"$in": ["chatting", "active" , "complete"]}
    })

    if not trip:
        raise HTTPException(status_code=400, detail="No active trip found")

   # 3️⃣ Determine PEER user (NO DB lookups)
    if trip["user_id"] == ObjectId(user_id):
        peer_id = str(trip["broker_id"])
        peer_name = "Broker"
    else:
        peer_id = str(trip["user_id"])
        peer_name = "Traveler"
    print("chat peer ID:", peer_id)
# 4️⃣ Ensure PEER exists in CometChat (idempotent)
    ensure_cometchat_user(peer_id, peer_name)

    # 6️⃣ Generate CometChat AUTH TOKEN
    url = (
        f"https://{COMETCHAT_APP_ID}.api-{COMETCHAT_REGION}.cometchat.io"
        f"/v3/users/{user_id}/auth_tokens"
    )

    headers = {
        "Content-Type": "application/json",
        "apiKey": COMETCHAT_AUTH_KEY,
        "appId": COMETCHAT_APP_ID,
    }

    res = requests.post(url, headers=headers)

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail=res.text)

    return {
        "uid": user_id,
        "authToken": res.json()["data"]["authToken"]
    }