import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHAT_ID in .env")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text):
    url = f"{BASE_URL}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})


def send_image(image_path, caption="Fall Detected"):

    url = f"{BASE_URL}/sendPhoto"

    with open(image_path, "rb") as img:
        requests.post(
            url,
            files={"photo": img},
            data={"chat_id": CHAT_ID, "caption": caption}
        )


def send_video(video_path, caption="Emergency Video"):

    url = f"{BASE_URL}/sendVideo"

    with open(video_path, "rb") as vid:
        requests.post(
            url,
            files={"video": vid},
            data={"chat_id": CHAT_ID, "caption": caption}
        )


def send_alert(severity):

    if severity == 3:
        send_message("🚨 CRITICAL EMERGENCY DETECTED")
    elif severity == 2:
        send_message("⚠️ Dangerous Fall Detected")
    else:
        send_message("⚠️ Fall Detected")
