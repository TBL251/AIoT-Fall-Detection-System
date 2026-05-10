from cryptography.fernet import Fernet

# =========================================================
# IMPORTANT:
# Generate ONE key only.
# Keep this key forever.
# If changed -> old users cannot decrypt anymore.
# =========================================================

SECRET_KEY = b'Q7z9rjv7vQ8b2xWz4QkYjK9y8Y4Nf1Y5JmV0aBcDeFg='

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