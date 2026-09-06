# app/routes/auth_routes.py

from fastapi import APIRouter, HTTPException, Depends, Body, status
from fastapi.security import OAuth2PasswordBearer
from app.db.mongodb import users_collection
from app.models.user_model import UserCreate, UserLogin
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from bson import ObjectId
import httpx

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# -------------------------------------------------------------------
# 1️⃣ TEST ROUTE
# -------------------------------------------------------------------
@router.get("/debug/dbinfo")
async def debug_dbinfo():
    from app.db.mongodb import database
    return {"database_name": database.name}


# -------------------------------------------------------------------
# 2️⃣ MANUAL REGISTRATION
# -------------------------------------------------------------------
@router.post("/register")
async def register_user(user: UserCreate):
    if user.role not in ["broker", "traveler"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pwd = hash_password(user.password)

    # TEMP USER (cannot login yet)
    new_user = {
        "email": user.email,
        "password": hashed_pwd,
        "full_name": user.full_name,
        "role": user.role,
        "auth_provider": "manual",
        "can_login": False,                       # 🔥 Cannot login yet
        "is_verified": False if user.role == "broker" else True,
        "verification_details": None
    }

    await users_collection.insert_one(new_user)

    # broker goes to verify screen
    if user.role == "broker":
        return {
            "message": "Broker registered. Please complete verification.",
            "redirect": "/broker/verify",
            "email": user.email
        }

    # traveler goes to login screen
    return {
        "message": "Traveler registered. Please login.",
        "redirect": "/login"
    }

# -------------------------------------------------------------------
# 3️⃣ MANUAL LOGIN
# -------------------------------------------------------------------
@router.post("/login")
async def login_user(credentials: UserLogin):
    user = await users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": str(user["_id"]),       # ⭐ KEEP user_id in sub
        "email": user["email"],
        "role": user["role"],
    })

    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


# -------------------------------------------------------------------
# 4️⃣ CURRENT USER
# -------------------------------------------------------------------
async def get_current_user_obj(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # ⭐ EXPECTS user_id in sub — Option A
    user = await users_collection.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["_id"] = str(user["_id"])
    user.pop("password", None)
    return user


@router.get("/me")
async def get_current_user(current_user: dict = Depends(get_current_user_obj)):
    return current_user


# -------------------------------------------------------------------
# 5️⃣ GOOGLE MOBILE LOGIN (Alternative #3 – FINAL)
# -------------------------------------------------------------------
@router.post("/google/mobile")
async def google_mobile_login(
    id_token: str = Body(...),
    role: str = Body(...)
):
    """
    Mobile Google login:
    - Frontend sends Google id_token + role (traveler/broker)
    - Backend verifies token with Google
    - Finds/creates user
    - Returns our own JWT access_token

    ⭐ No redirects
    ⭐ No backend OAuth flow
    ⭐ Works in Expo Go / Android / local network
    """

    if role not in ("traveler", "broker"):
        raise HTTPException(status_code=400, detail="Invalid role")

    # 1️⃣ Verify Google ID token
    async with httpx.AsyncClient() as client:
        google_resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )

    if google_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    token_info = google_resp.json()

    email = token_info.get("email")
    full_name = token_info.get("name", "Google User")
    picture = token_info.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Email missing from Google token")

    # 2️⃣ Find or create user
    user = await users_collection.find_one({"email": email})

    if not user:
        # new Google user
        new_user = {
            "email": email,
            "full_name": full_name,
            "picture": picture,
            "role": role,
            "auth_provider": "google",
        }
        result = await users_collection.insert_one(new_user)
        user_id = str(result.inserted_id)
    else:
        user_id = str(user["_id"])

        # Optionally update role
        if user.get("role") != role:
            await users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"role": role}}
            )

    # 3️⃣ Create JWT — ⭐ KEEP sub = user_id
    access_token = create_access_token({
        "sub": user_id,
        "email": email,
        "role": role,
    })

    return {"access_token": access_token, "token_type": "bearer"}