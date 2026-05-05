import os
import firebase_admin
from firebase_admin import credentials, messaging
from app.config import settings
from typing import Optional

def _init_fcm() -> bool:
    if not settings.FCM_CREDENTIALS_PATH:
        print("[SKIP] FCM not configured — skipping push notification")
        return False

    if not os.path.exists(settings.FCM_CREDENTIALS_PATH):
        print(f"[WARNING] FCM credentials file not found: {settings.FCM_CREDENTIALS_PATH}")
        return False

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            print("[OK] Firebase FCM initialized")
        return True
    except Exception as e:
        print(f"[WARNING] FCM init failed: {e}")
        return False

async def send_digest_notification(fcm_token: str, digest_date: str, action_item_count: int, topic_count: int) -> Optional[str]:
    """
    Send a daily digest notification via Firebase Cloud Messaging.
    """
    if not _init_fcm():
        return None

    try:
        title = f"Your Daily Digest ({digest_date})"
        body = f"You have {action_item_count} action items across {topic_count} topics."
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=fcm_token,
        )
        # messaging.send is synchronous, but typically fast enough for this use case
        response = messaging.send(message)
        print(f"[OK] FCM notification sent: {response}")
        return response
    except Exception as e:
        print(f"[WARNING] FCM send failed: {e}")
        return None
