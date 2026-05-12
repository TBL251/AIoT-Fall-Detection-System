import firebase_admin

from firebase_admin import (
    credentials,
    db
)

from dotenv import load_dotenv

import os
import time


# ======================
# LOAD ENV
# ======================

load_dotenv()

FIREBASE_KEY = os.getenv("FIREBASE_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")


# ======================
# VALIDATE CONFIG
# ======================

if not FIREBASE_KEY:
    raise ValueError(
        "Missing FIREBASE_KEY in .env"
    )

if not DATABASE_URL:
    raise ValueError(
        "Missing DATABASE_URL in .env"
    )


# ======================
# INIT FIREBASE (SAFE)
# ======================

if not firebase_admin._apps:

    cred = credentials.Certificate(
        FIREBASE_KEY
    )

    firebase_admin.initialize_app(
        cred,
        {
            "databaseURL": DATABASE_URL
        }
    )

    print("[FIREBASE] Connected")


# ======================
# SAVE EVENT
# ======================

def save_event(
    event_type,
    severity,
    video_path,
    email=None,
    image_path=None
):

    try:

        ref = db.reference("events")

        data = {

            "event": event_type,

            "severity": severity,

            "video_path": video_path,

            "image_path": image_path,

            "email": email,

            "timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "unix_time": int(time.time())
        }

        result = ref.push(data)

        print(
            "[FIREBASE] Event saved:",
            result.key
        )

        return result.key

    except Exception as e:

        print(
            "[FIREBASE ERROR]",
            e
        )

        return None