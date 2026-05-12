import requests
import os
import time

from dotenv import load_dotenv

# ======================
# LOAD ENV
# ======================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = os.getenv("CHAT_ID")

# ======================
# VALIDATE
# ======================

if not BOT_TOKEN:
    raise ValueError(
        "Missing BOT_TOKEN in .env"
    )

if not CHAT_ID:
    raise ValueError(
        "Missing CHAT_ID in .env"
    )

# ======================
# TELEGRAM API
# ======================

BASE_URL = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)

# ======================
# SEND MESSAGE
# ======================

def send_message(text):

    try:

        url = f"{BASE_URL}/sendMessage"

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text
            },
            timeout=10
        )

        print(
            "[TELEGRAM] Message sent",
            response.status_code
        )

    except Exception as e:

        print(
            "[TELEGRAM MESSAGE ERROR]",
            e
        )

# ======================
# SEND IMAGE
# ======================

def send_image(
    image_path,
    caption="Fall Detected"
):

    try:

        if not os.path.exists(image_path):

            print(
                "[TELEGRAM] Image not found"
            )

            return

        url = f"{BASE_URL}/sendPhoto"

        with open(image_path, "rb") as img:

            response = requests.post(
                url,
                files={
                    "photo": img
                },
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption
                },
                timeout=20
            )

        print(
            "[TELEGRAM] Image sent",
            response.status_code
        )

    except Exception as e:

        print(
            "[TELEGRAM IMAGE ERROR]",
            e
        )

# ======================
# SEND VIDEO
# ======================

def send_video(
    video_path,
    caption="Emergency Video"
):

    try:

        if not os.path.exists(video_path):

            print(
                "[TELEGRAM] Video not found"
            )

            return

        url = f"{BASE_URL}/sendVideo"

        with open(video_path, "rb") as vid:

            response = requests.post(
                url,
                files={
                    "video": vid
                },
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption
                },
                timeout=60
            )

        print(
            "[TELEGRAM] Video sent",
            response.status_code
        )

    except Exception as e:

        print(
            "[TELEGRAM VIDEO ERROR]",
            e
        )

# ======================
# ALERT FORMATTER
# ======================

def send_alert(severity):

    current_time = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # ======================
    # LEVEL MESSAGE
    # ======================

    if severity == 1:

        text = (
            "⚠️ MINOR FALL DETECTED\n\n"
            f"Severity: Level {severity}\n"
            f"Time: {current_time}"
        )

    elif severity == 2:

        text = (
            "⚠️ DANGEROUS FALL DETECTED\n\n"
            f"Severity: Level {severity}\n"
            f"Time: {current_time}"
        )

    else:

        text = (
            "🚨 CRITICAL EMERGENCY DETECTED\n\n"
            f"Severity: Level {severity}\n"
            f"Time: {current_time}"
        )

    send_message(text)