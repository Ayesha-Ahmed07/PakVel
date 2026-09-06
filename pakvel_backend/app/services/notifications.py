# app/services/notifications.py

async def send_weather_alert(user_id: str, city: str, condition: str):
    """
    Stub for FYP:
    Sends weather emergency alert to traveler
    """

    print(
        f"⚠️ ALERT: {city} has {condition} — notify user {user_id}"
    )

    # 🔔 Future integrations (mention in FYP):
    # - Firebase Cloud Messaging (FCM)
    # - Expo Push Notifications