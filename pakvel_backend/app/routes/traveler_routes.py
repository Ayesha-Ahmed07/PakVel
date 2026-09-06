# app/routes/traveler_routes.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from app.db.mongodb import (
    users_collection,
    itineraries_collection,
    preferences_collection,
    messages_collection
)
from app.core.security import decode_access_token
from bson import ObjectId
import datetime
import random
import hashlib
import json , re
import os
import uuid
from dotenv import load_dotenv
from app.LLM.main import generate_itinerary_llm
load_dotenv()

router = APIRouter(prefix="/traveler", tags=["Traveler"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

from groq import Groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Pakistan cities for validation
PAKISTAN_CITIES = [
    "islamabad", "rawalpindi", "lahore", "karachi", "quetta",
    "peshawar", "skardu", "hunza", "gilgit", "kashmir",
    "swat", "murree", "multan", "bahawalpur", "gwadar",
    "chitral", "hyderabad", "faisalabad", "sialkot"
]

# --------------------------
# HYBRID CITY DETECTION (B4)
# --------------------------
async def detect_city_hybrid(message: str):
    msg = message.lower()

    # STEP 1: REGEX TOKENIZE
    words = re.findall(r"[a-zA-Z]+", msg)

    # STEP 2: DIRECT MATCH AGAINST PAKISTAN CITIES
    for w in words:
        if w in PAKISTAN_CITIES:
            print("DEBUG: Regex detected city =", w)
            return w

    # STEP 3: LLM FALLBACK
    print("DEBUG: Regex failed. Using LLM city extraction...")

    llm_prompt = f"""
    Extract ONLY the Pakistan city mentioned in this message.
    If the city is outside Pakistan or none exists, reply: none

    Message: "{message}"
    """

    res = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": llm_prompt}]
    )

    city = res.choices[0].message.content.strip().lower()
    print("DEBUG: LLM extracted city =", city)

    if city in PAKISTAN_CITIES:
        return city

    return None


# -------------------------------------------
# 🔵 LOGGING FUNCTION (Message saving)
# -------------------------------------------
async def log_message(
    conversationId: str,
    senderId,
    receiverId,
    senderType: str,
    receiverType: str,
    text: str,
    meta=None
):
    await messages_collection.insert_one({
        "conversationId": conversationId,
        "senderId": senderId,
        "receiverId": receiverId,
        "senderType": senderType,
        "receiverType": receiverType,
        "message": text,
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "meta": meta or []
    })


# -------------------------------------------
# 🔵 CHATBOT ROUTE (UPDATED)
# -------------------------------------------
@router.post("/chat")
async def travel_chatbot(message: dict, token: str = Depends(oauth2_scheme)):

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload["email"]
    user_msg = message.get("message", "").strip()
    msg_lower = user_msg.lower()

    # Fetch user to get userID
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user["_id"]
    conversationId = f"conv-{user_id}"   # persistent conversation ID

    # -------------------------------------------
    # 🔵 Log USER MESSAGE
    # -------------------------------------------
    await log_message(
        conversationId=conversationId,
        senderId=user_id,
        receiverId=None,
        senderType="traveler",
        receiverType="ai",
        text=user_msg
    )

    # 0️⃣ GREETINGS
    greetings = ["hi", "hello", "hey", "salam", "assalamualaikum",
                 "good morning", "good evening"]

    if msg_lower in greetings or any(msg_lower.startswith(g) for g in greetings):

        bot_reply = "Hello! 👋 How can I help you with your travel planning today?"

        # Log bot reply
        await log_message(
            conversationId=conversationId,
            senderId=None,
            receiverId=user_id,
            senderType="ai",
            receiverType="traveler",
            text=bot_reply
        )

        return {"reply": bot_reply}

    # 1️⃣ FETCH USER'S STORED ITINERARIES
    itineraries = await itineraries_collection.find({"user_email": email}).to_list(None)
    known_cities = [it["destination"].lower() for it in itineraries]

    # 2️⃣ DETECT IF USER WANTS MODIFICATION
    modification_keywords = [
        "shorten", "modify", "fix", "adjust", "update",
        "change", "edit", "remove", "replace", "add",
        "revise", "rearrange"
    ]
    is_modification = any(kw in msg_lower for kw in modification_keywords)

    # 3️⃣ HYBRID CITY DETECTION
    detected_city = await detect_city_hybrid(user_msg)

    # --------------------------
    # MODE 1 — GENERAL TRAVEL INFO
    # --------------------------
    if not is_modification:

        system_prompt = """
You are a Pakistan-specific travel assistant.

RULES:
1. Only answer travel-related questions about Pakistan.
2. If the city is outside Pakistan, reply:
   "Sorry, I can only provide travel information for places inside Pakistan."
3. Do NOT mention itineraries in this mode.
4. Respond naturally and keep answers short.
"""

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ]
        )

        bot_reply = response.choices[0].message.content

        # Log bot reply
        await log_message(
            conversationId=conversationId,
            senderId=None,
            receiverId=user_id,
            senderType="ai",
            receiverType="traveler",
            text=bot_reply
        )

        return {"reply": bot_reply}

    # --------------------------
    # MODE 2 — ITINERARY MODIFICATION
    # --------------------------
    if not detected_city:
        bot_reply = "Please specify a Pakistan city for the itinerary you want to modify."

        await log_message(
            conversationId=conversationId,
            senderId=None,
            receiverId=user_id,
            senderType="ai",
            receiverType="traveler",
            text=bot_reply
        )

        return {"reply": bot_reply}

    # Check if itinerary exists
    itinerary = next((it for it in itineraries if it["destination"].lower() == detected_city), None)

    if not itinerary:
        bot_reply = f"You do not have an itinerary for {detected_city.capitalize()}. Please generate one first."

        await log_message(conversationId, None, user_id, "ai", "traveler", bot_reply)

        return {"reply": bot_reply}

    itinerary_days = itinerary["itinerary_days"]
    itinerary_json = json.dumps(itinerary_days)

    # LLM Prompt
    system_prompt = f"""
You are an itinerary editor for {detected_city.capitalize()}.

RULES:
- Only modify activities inside existing days.
- Do NOT add or remove days.
- No empty fields.
- No duplicates.
- Return ONLY valid JSON.
"""

    user_prompt = f"""
Existing itinerary:
{itinerary_json}

User request:
"{user_msg}"
"""

    res = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    ai_raw = res.choices[0].message.content

    try:
        ai_json = json.loads(ai_raw)
    except:
        bot_reply = "Sorry, I couldn't process that request. Please try again."

        await log_message(conversationId, None, user_id, "ai", "traveler", bot_reply)

        return {"reply": bot_reply}

    # Fallback responses
    if ai_json.get("operation") == "chat":
        bot_reply = ai_json["reply"]

        await log_message(conversationId, None, user_id, "ai", "traveler", bot_reply)

        return {"reply": bot_reply}

    # Apply modification
    updated = ai_json.get("updated_itinerary", [])

    # Validation
    if len(updated) != len(itinerary_days):
        bot_reply = "Error: Number of days cannot be changed."

        await log_message(conversationId, None, user_id, "ai", "traveler", bot_reply)

        return {"reply": bot_reply}

    for day in updated:
        seen = set()
        for item in day["schedule"]:
            if not item.get("time") or not item.get("activity"):
                bot_reply = "Error: Time and activity must not be empty."

                await log_message(conversationId, None, user_id, "ai", "traveler", bot_reply)

                return {"reply": bot_reply}

            if item["activity"] in seen:
                bot_reply = "Error: Duplicate activities found."

                await log_message(conversationId, None, user_id, "ai", "traveler", bot_reply)

                return {"reply": bot_reply}

            seen.add(item["activity"])

    # Save updated itinerary
    await itineraries_collection.update_one(
        {"_id": itinerary["_id"]},
        {"$set": {"itinerary_days": updated}}
    )

    bot_reply = f"Your {detected_city.capitalize()} itinerary has been updated! 🎉"

    # Log success message
    await log_message(conversationId, None, user_id, "ai", "traveler", bot_reply, meta=updated)

    return {
        "reply": bot_reply,
        "updated_itinerary": updated
    }


# 1️⃣ Traveler Dashboard
@router.get("/dashboard")
async def get_dashboard(token: str = Depends(oauth2_scheme)):
    """Get traveler dashboard data (My Trips + Suggested Itineraries)"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload["email"]

    # Fetch My Trips
    my_trips = await itineraries_collection.find({"user_email": email}).to_list(None)
    for trip in my_trips:
        trip["_id"] = str(trip["_id"])

    # Fetch 3 random suggested itineraries
    suggested = await itineraries_collection.aggregate([{"$sample": {"size": 3}}]).to_list(None)
    for s in suggested:
        s["_id"] = str(s["_id"])

    return {
        "message": "Traveler dashboard loaded successfully",
        "my_trips": my_trips,
        "suggested_trips": suggested,
    }


# 2️⃣ Save Preferences
@router.post("/preferences")
async def save_preferences(preferences: dict, token: str = Depends(oauth2_scheme)):
    """Save user preferences temporarily before AI generation"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload["email"]

    # Remove previous preferences for this user
    await preferences_collection.delete_many({"user_email": email})

    preferences["user_email"] = email
    preferences["created_at"] = datetime.datetime.now(datetime.timezone.utc)

    result = await preferences_collection.insert_one(preferences)
    preferences["_id"] = str(result.inserted_id)

    return {"message": "Preferences saved successfully", "preferences": preferences}


# 3️⃣ Generate AI Itinerary   - everytime a traveler generates an itinerary  it gets stored in itinerary collection, 
@router.post("/generate-itinerary")
async def generate_itinerary(preferences: dict, token: str = Depends(oauth2_scheme)):

    # ------------------------
    # Auth Validation
    # ------------------------
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = payload["email"]

    # ------------------------
    # Extract Preferences
    # ------------------------
    destination = preferences.get("destination", "Unknown Destination")
    duration = int(preferences.get("duration", 3))
    raw_budget = preferences.get("budget", "moderate")
    # Convert numeric → category
    if isinstance(raw_budget, (int, float)):
        if raw_budget < 20000:
            budget = "low"
        elif raw_budget < 60000:
            budget = "moderate"
        else:
            budget = "high"
    else:
        budget = str(raw_budget).lower()
    interests = preferences.get("interests", ["Culture", "Adventure"])

    # ------------------------
    # Generate Unique Hash (for duplicate prevention)
    # ------------------------
    hash_input = json.dumps({
        "user_email": email,
        "destination": destination.lower(),
        "duration": duration,
        "budget": budget,
        "interests": sorted(interests),
    }, sort_keys=True)

    unique_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    # ------------------------
    # Check if itinerary already exists
    # ------------------------
    existing = await itineraries_collection.find_one({"unique_hash": unique_hash})
    if existing:
        existing["_id"] = str(existing["_id"])
        return {
            "message": "Itinerary already existed — returning saved version.",
            "duplicate": True,
            "itinerary": existing
        }

    # ------------------------
    # Call RAG LLM
    # ------------------------
    try:
        llm_output = generate_itinerary_llm(
            destination=destination,
            days=duration,
            budget=budget,
            interests=interests
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

    # ------------------------
    # Prepare Itinerary Object
    # ------------------------
    itinerary = {
        "user_email": email,
        "destination": destination,
        "duration": duration,
        "budget": budget,
        "interests": interests,
        "itinerary_days": llm_output,  # ← Now real AI output
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "source": "RAG AI Generator v2.0",
        "unique_hash": unique_hash,
    }

    # ------------------------
    # Save to MongoDB
    # ------------------------
    result = await itineraries_collection.insert_one(itinerary)
    itinerary["_id"] = str(result.inserted_id)

    # ------------------------
    # Return Response
    # ------------------------
    return {
        "message": "AI itinerary generated successfully!",
        "duplicate": False,
        "itinerary": itinerary
    }

# 4️⃣ View Specific Itinerary
@router.get("/itinerary/{itinerary_id}")
async def get_itinerary(itinerary_id: str, token: str = Depends(oauth2_scheme)):
    """Fetch a specific itinerary by its ID"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    itinerary = await itineraries_collection.find_one({"_id": ObjectId(itinerary_id)})
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    itinerary["_id"] = str(itinerary["_id"])
    return itinerary


# 5️⃣ Update Itinerary
@router.put("/itinerary/{itinerary_id}/update")
async def update_itinerary(itinerary_id: str, updates: dict, token: str = Depends(oauth2_scheme)):
    """Update an itinerary (e.g., after AI modifies it)."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    result = await itineraries_collection.update_one(
        {"_id": ObjectId(itinerary_id)}, {"$set": updates}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Itinerary not updated")

    return {"message": "Itinerary updated successfully"}


# 6️⃣ Suggested Itineraries - suggest top5 itineraries on dashboard
@router.get("/suggested-itineraries")
async def get_suggested_itineraries():
    """
    Suggest itineraries from previously AI-generated trips.
    Picks a few random ones from the database (no hardcoding).
    """
    total_itineraries = await itineraries_collection.count_documents({})

    if total_itineraries == 0:
        return {"message": "No itineraries available yet. Generate one to get started!", "suggested_itineraries": []}

    # Randomly sample up to 5 itineraries from your DB
    sample_size = min(5, total_itineraries)
    suggested = await itineraries_collection.aggregate([{"$sample": {"size": sample_size}}]).to_list(None)
    
    for s in suggested:
        s["_id"] = str(s["_id"])

    return {"suggested_itineraries": suggested}