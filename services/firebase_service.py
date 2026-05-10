import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
import os
import time

load_dotenv()

FIREBASE_KEY = os.getenv("FIREBASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not FIREBASE_KEY or not DATABASE_URL:
    raise ValueError("Missing Firebase configuration in .env")

cred = credentials.Certificate(FIREBASE_KEY)

firebase_admin.initialize_app(cred, {
    "databaseURL": DATABASE_URL
})

def save_event(event_type, severity, video_path):

    ref = db.reference("events")

    data = {
        "event": event_type,
        "severity": severity,
        "video_path": video_path,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    ref.push(data)

