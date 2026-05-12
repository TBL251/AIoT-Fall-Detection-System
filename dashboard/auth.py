import os
from flask import session

BASE_RECORD_FOLDER = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "recorded_videos"
    )
)

def create_user_folder(email: str):

    safe_email = email.replace("@", "_").replace(".", "_")

    user_folder = os.path.join(
        BASE_RECORD_FOLDER,
        safe_email
    )

    low_folder = os.path.join(user_folder, "Minor")
    medium_folder = os.path.join(user_folder, "Dangerous")
    critical_folder = os.path.join(user_folder, "Critical Emergency")

    os.makedirs(low_folder, exist_ok=True)
    os.makedirs(medium_folder, exist_ok=True)
    os.makedirs(critical_folder, exist_ok=True)

    print("CREATED:", user_folder)

    return user_folder


def login_user(email: str) -> None:
    session["user"] = email
    session.permanent = False


def logout_user() -> None:
    session.clear()


def is_login() -> bool:
    return "user" in session and bool(session["user"])


def current_user() -> str:
    return session.get("user", "")