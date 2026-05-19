import requests
import os
import time

from dotenv import load_dotenv

# ======================
# LOAD ENV
# ======================

load_dotenv()

BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)

CHAT_ID = os.getenv(
    "CHAT_ID"
)

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
# SESSION
# ======================

session = requests.Session()

session.headers.update({
    "Connection": "close"
})

# ======================
# SEND MESSAGE
# ======================

def send_message(text):

    try:

        url = (
            f"{BASE_URL}/sendMessage"
        )

        response = session.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text
            },
            timeout=30
        )

        result = response.json()

        if result.get("ok"):

            print(
                "[TELEGRAM] Message sent"
            )

        else:

            print(
                "[TELEGRAM ERROR]",
                result
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

        if not os.path.exists(
            image_path
        ):

            print(
                "[TELEGRAM] Image not found"
            )

            return

        url = (
            f"{BASE_URL}/sendPhoto"
        )

        with open(
            image_path,
            "rb"
        ) as img:

            response = session.post(
                url,
                files={
                    "photo": img
                },
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption
                },
                timeout=60
            )

        result = response.json()

        if result.get("ok"):

            print(
                "[TELEGRAM] Image sent"
            )

        else:

            print(
                "[TELEGRAM IMAGE ERROR]",
                result
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

        if not os.path.exists(
            video_path
        ):

            print(
                "[TELEGRAM] Video not found"
            )

            return

        file_size = os.path.getsize(
            video_path
        ) / (1024 * 1024)

        print(
            f"[VIDEO SIZE] {file_size:.2f} MB"
        )

        url = (
            f"{BASE_URL}/sendVideo"
        )

        for attempt in range(3):

            try:

                print(
                    f"[TELEGRAM] Upload attempt {attempt + 1}"
                )

                with open(
                    video_path,
                    "rb"
                ) as vid:

                    response = session.post(

                        url,

                        files={
                            "video": (
                                os.path.basename(
                                    video_path
                                ),
                                vid,
                                "video/mp4"
                            )
                        },

                        data={

                            "chat_id": CHAT_ID,

                            "caption": caption,

                            "supports_streaming": True,

                            "disable_notification": False
                        },

                        timeout=300
                    )

                result = response.json()

                if result.get("ok"):

                    print(
                        "[TELEGRAM] Video delivered successfully"
                    )

                    return

                else:

                    print(
                        "[TELEGRAM ERROR]",
                        result
                    )

            except Exception as e:

                print(
                    "[TELEGRAM RETRY ERROR]",
                    e
                )

            time.sleep(2)

        print(
            "[TELEGRAM] Failed after retries"
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