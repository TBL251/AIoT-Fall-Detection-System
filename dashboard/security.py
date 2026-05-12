from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY").encode()

cipher = Fernet(SECRET_KEY)


# =========================================================
# ENCRYPT
# =========================================================

def encrypt_text(text):

    return cipher.encrypt(
        text.encode()
    ).decode()


# =========================================================
# DECRYPT
# =========================================================

def decrypt_text(text):

    return cipher.decrypt(
        text.encode()
    ).decode()