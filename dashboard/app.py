
from flask import Flask, render_template, redirect
from flask import request, jsonify, Response, session

from flask_socketio import SocketIO

import random
import cv2
import time
import json
import os
import re

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from auth import (
    login_user,
    logout_user,
    is_login,
    create_user_folder
)

from mail import (
    send_otp,
    verify_otp
)

from security import (
    encrypt_text,
    decrypt_text
)

# =============================================================================
# APP
# =============================================================================

app = Flask(__name__)

app.secret_key = "aiot_fall_detection_2024"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# =============================================================================
# GLOBALS
# =============================================================================

engine_started = False

# =============================================================================
# USER DATABASE
# =============================================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

USERS_FILE = os.path.join(
    BASE_DIR,
    "users.json"
)


def load_users():

    if not os.path.exists(USERS_FILE):

        with open(
            USERS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump({}, f)

        return {}

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_users(users_data):

    with open(
        USERS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            users_data,
            f,
            indent=4,
            ensure_ascii=False
        )


users = load_users()

# =============================================================================
# HELPERS
# =============================================================================

def valid_email(email):

    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    return re.match(pattern, email)


def email_exists(email):

    for enc_email in users:

        try:

            real_email = decrypt_text(
                enc_email
            )

            if real_email == email:
                return True

        except:
            pass

    return False


def get_user_by_email(email):

    for enc_email, user_data in users.items():

        try:

            real_email = decrypt_text(
                enc_email
            )

            if real_email == email:
                return user_data

        except:
            pass

    return None


# =============================================================================
# AUTH ROUTES
# =============================================================================

@app.route("/")
def index():

    if is_login():
        return redirect("/dashboard")

    return render_template("login.html")


# =============================================================================
# LOGIN
# =============================================================================

@app.route("/login", methods=["POST"])
def do_login():

    data = request.get_json()

    email = data.get(
        "email",
        ""
    ).strip()

    pw = data.get(
        "password",
        ""
    ).strip()

    if not email or not pw:

        return jsonify({
            "ok": False,
            "msg": "Please enter email and password"
        })

    user = get_user_by_email(email)

    if not user:

        return jsonify({
            "ok": False,
            "msg": "Email does not exist"
        })

    saved_password = user.get(
        "password",
        ""
    )

    if not check_password_hash(
        saved_password,
        pw
    ):

        return jsonify({
            "ok": False,
            "msg": "Wrong password"
        })

    login_user(email)

    return jsonify({
        "ok": True,
        "msg": "Login success"
    })


# =============================================================================
# REGISTER PAGE
# =============================================================================

@app.route("/register")
def register_page():

    return render_template(
        "register.html"
    )


# =============================================================================
# SEND OTP
# =============================================================================

@app.route("/send-otp", methods=["POST"])
def route_send_otp():

    data = request.get_json()

    email = data.get(
        "email",
        ""
    ).strip()

    if not email:

        return jsonify({
            "ok": False,
            "msg": "Email is required"
        })

    if not valid_email(email):

        return jsonify({
            "ok": False,
            "msg": "Invalid email format"
        })

    if email_exists(email):

        return jsonify({
            "ok": False,
            "msg": "Email already exists"
        })

    try:

        send_otp(email)

        return jsonify({
            "ok": True,
            "msg": "OTP sent to your email"
        })

    except Exception as e:

        print("OTP ERROR:", e)

        return jsonify({
            "ok": False,
            "msg": "Failed to send OTP"
        })


# =============================================================================
# VERIFY OTP + REGISTER
# =============================================================================

@app.route("/verify-otp", methods=["POST"])
def route_verify_otp():

    data = request.get_json()

    email = data.get(
        "email",
        ""
    ).strip()

    otp = data.get(
        "otp",
        ""
    ).strip()

    name = data.get(
        "name",
        "User"
    ).strip()

    pw = data.get(
        "password",
        ""
    ).strip()

    if not email or not otp or not pw:

        return jsonify({
            "ok": False,
            "msg": "Missing required fields"
        })

    if not verify_otp(email, otp):

        return jsonify({
            "ok": False,
            "msg": "Invalid or expired OTP"
        })

    if email_exists(email):

        return jsonify({
            "ok": False,
            "msg": "Email already exists"
        })

    hashed_password = generate_password_hash(
        pw
    )

    encrypted_email = encrypt_text(
        email
    )

    encrypted_name = encrypt_text(
        name
    )

    users[encrypted_email] = {

        "name": encrypted_name,

        "password": hashed_password
    }

    save_users(users)
    
    create_user_folder(email)

    print("USER SAVED:", email)

    login_user(email)

    return jsonify({
        "ok": True,
        "msg": "Register success"
    })


# =============================================================================
# LOGOUT
# =============================================================================

@app.route("/logout")
def logout():

    logout_user()

    return redirect("/")


# =============================================================================
# LOGIN CHECK
# =============================================================================

def require_login():

    if not is_login():
        return redirect("/")

    return None


# =============================================================================
# PAGES
# =============================================================================

@app.route("/dashboard")
def dashboard():

    return require_login() or render_template(
        "dashboard.html"
    )


@app.route("/charts")
def charts():

    return require_login() or render_template(
        "charts.html"
    )


@app.route("/live")
def live():

    return require_login() or render_template(
        "live.html"
    )


@app.route("/replay")
def replay():

    return require_login() or render_template(
        "replay.html"
    )


@app.route("/profile")
def profile():

    current_user = session.get(
        "user",
        ""
    )

    user_name = "Unknown"

    user_data = get_user_by_email(
        current_user
    )

    if user_data:

        try:

            user_name = decrypt_text(
                user_data["name"]
            )

        except:
            pass

    return require_login() or render_template(

        "profile.html",

        user_email=current_user,

        user_name=user_name
    )


# =============================================================================
# ESP32 VIDEO STREAM
# =============================================================================

ESP32_STREAM_URL = "http://192.168.1.100/stream"


def gen_frames():

    cap = cv2.VideoCapture(
        ESP32_STREAM_URL
    )

    use_cap = cap.isOpened()

    while True:

        if use_cap:

            success, frame = cap.read()

            if not success:

                use_cap = False

                cap.release()

        else:

            import numpy as np

            frame = np.ones(
                (360, 640, 3),
                dtype="uint8"
            ) * 120

            cv2.putText(
                frame,
                "ESP32-CAM OFFLINE",
                (140, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )

        _, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        frame_bytes = buffer.tobytes()

        yield (

            b"--frame\r\n"

            b"Content-Type: image/jpeg\r\n\r\n"

            + frame_bytes +

            b"\r\n"
        )

        time.sleep(0.05)


@app.route("/video")
def video():

    if not is_login():
        return "", 403

    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# =============================================================================
# REALTIME ENGINE
# =============================================================================

def realtime_engine():

    states = [
        "NORMAL",
        "UNBALANCED",
        "FALLING",
        "CRITICAL"
    ]

    weights = [
        0.70,
        0.15,
        0.10,
        0.05
    ]

    while True:

        state = random.choices(
            states,
            weights=weights
        )[0]

        risk = {

            "NORMAL": 0,

            "UNBALANCED": 25,

            "FALLING": 75,

            "CRITICAL": 99

        }[state]

        socketio.emit(

            "update",

            {

                "l1": random.randint(0, 5),

                "l2": random.randint(0, 8),

                "l3": random.randint(0, 3),

                "status": state,

                "state": state,

                "risk": risk,

                "time": time.strftime("%H:%M:%S")
            }
        )

        socketio.sleep(2)


@socketio.on("connect")
def handle_connect():

    global engine_started

    if not engine_started:

        socketio.start_background_task(
            realtime_engine
        )

        engine_started = True


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":

    import webbrowser
    from threading import Timer
    import os

    def open_browser():

        webbrowser.open_new(
            "http://127.0.0.1:5000"
        )

    # chỉ mở 1 lần
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":

        Timer(
            1,
            open_browser
        ).start()

    socketio.run(

        app,

        debug=True,

        host="0.0.0.0",

        port=5000
    )