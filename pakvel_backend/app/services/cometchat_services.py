import requests
import os

COMETCHAT_APP_ID = os.getenv("COMETCHAT_APP_ID")
COMETCHAT_REGION = os.getenv("COMETCHAT_REGION")
COMETCHAT_REST_API_KEY = os.getenv("COMETCHAT_API_KEY")

BASE_URL = f"https://{COMETCHAT_APP_ID}.api-{COMETCHAT_REGION}.cometchat.io/v3"

print("🔗 CometChat BASE_URL:", BASE_URL)
HEADERS = {
    "Content-Type": "application/json",
    "apiKey": COMETCHAT_REST_API_KEY,
    "appId": COMETCHAT_APP_ID,
}

def ensure_cometchat_user(user_id: str, name: str):
    # 1️⃣ Check if user exists
    res = requests.get(
        f"{BASE_URL}/users/{user_id}",
        headers=HEADERS
    )

    if res.status_code == 200:
        return

    # 2️⃣ Create user
    payload = {
        "uid": user_id,
        "name": name
    }

    create_res = requests.post(
        f"{BASE_URL}/users",
        json=payload,
        headers=HEADERS
    )

    create_res.raise_for_status() 