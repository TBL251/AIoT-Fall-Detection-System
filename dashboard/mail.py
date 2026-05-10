import random
import time
import logging
import smtplib
import os

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =========================
# CONFIG EMAIL
# =========================
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# =========================
# OTP STORE
# =========================
_otp_store: dict[str, dict] = {}

OTP_TTL_SECONDS = 600   # 10 phút


# =========================
# SEND OTP
# =========================
def send_otp(email: str) -> str:

    otp = str(random.randint(100000, 999999))

    _otp_store[email] = {
        "otp": otp,
        "expires": time.time() + OTP_TTL_SECONDS,
    }

    _deliver_otp(email, otp)

    return otp


# =========================
# VERIFY OTP
# =========================
def verify_otp(email: str, otp: str) -> bool:

    record = _otp_store.get(email)

    if not record:
        return False

    # hết hạn
    if time.time() > record["expires"]:
        del _otp_store[email]
        logger.info("[OTP] Expired for %s", email)
        return False

    # OTP sai
    if str(record["otp"]) != str(otp).strip():
        return False

    # dùng 1 lần
    del _otp_store[email]

    return True


# =========================
# EMAIL DELIVERY
# =========================
def _deliver_otp(email: str, otp: str) -> None:

    subject = "Your OTP Verification Code"

    body = f"""
Hello,

Your OTP code is: {otp}

This code will expire in 10 minutes.

AIOT Dashboard
"""

    msg = MIMEMultipart()

    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        # Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)

        server.starttls()

        # login gmail
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        # send email
        server.send_message(msg)

        logger.info("[OTP] Sent to %s", email)

        server.quit()

    except Exception as e:
        logger.error("Failed to send OTP: %s", e)