import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

from flask import (
    Flask,
    render_template,
    redirect,
    request,
    jsonify,
    Response,
    session
)

from flask_socketio import SocketIO
from flask import send_from_directory

import random
import cv2
import time
import json
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

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "aiot_fall_detection_2024")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False

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

# =============================================================================
# LOAD USERS
# =============================================================================

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

# =============================================================================
# SAVE USERS
# =============================================================================

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

# =============================================================================
# EMAIL EXISTS
# =============================================================================

def email_exists(email):

    for enc_email in users:

        try:

            real_email = decrypt_text(enc_email)

            if real_email == email:
                return True

        except:
            pass

    return False

# =============================================================================
# GET USER
# =============================================================================

def get_user_by_email(email):

    for enc_email, user_data in users.items():

        try:

            real_email = decrypt_text(enc_email)

            if real_email == email:
                return user_data

        except:
            pass

    return None

# =============================================================================
# REQUIRE LOGIN
# =============================================================================

def require_login():

    if not is_login():
        return redirect("/")

    return None

# =============================================================================
# HOME
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

    global users

    users = load_users()

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

    # reset login state
    for enc_email in users:

        users[enc_email]["is_logged_in"] = False

    # current login
    for enc_email in users:

        try:

            real_email = decrypt_text(enc_email)

            if real_email == email:

                users[enc_email]["is_logged_in"] = True

        except:
            pass

    save_users(users)

    print(f"[LOGIN] {email}")

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
# VERIFY OTP
# =============================================================================

@app.route("/verify-otp", methods=["POST"])
def route_verify_otp():

    global users

    users = load_users()

    data = request.get_json()

    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()
    name = data.get("name", "User").strip()
    pw = data.get("password", "").strip()

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

    hashed_password = generate_password_hash(pw)

    encrypted_email = encrypt_text(email)

    encrypted_name = encrypt_text(name)

    # logout all users
    for enc_email in users:

        users[enc_email]["is_logged_in"] = False

    users[encrypted_email] = {

        "name": encrypted_name,

        "password": hashed_password,

        "is_logged_in": True
    }

    save_users(users)

    create_user_folder(email)

    login_user(email)

    print(f"[REGISTER] {email}")

    return jsonify({
        "ok": True,
        "msg": "Register success"
    })

# =============================================================================
# LOGOUT
# =============================================================================

@app.route("/logout")
def logout():

    global users

    users = load_users()

    current_user = session.get("user")

    for enc_email in users:

        try:

            real_email = decrypt_text(enc_email)

            if real_email == current_user:

                users[enc_email]["is_logged_in"] = False

        except:
            pass

    save_users(users)

    logout_user()

    print("[LOGOUT]")

    return redirect("/")

# =============================================================================
# DASHBOARD
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

    user_data = get_user_by_email(current_user)

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
# VIDEO STREAM
# =============================================================================


def gen_frames():

    import shared_camera
    import numpy as np
    import time

    while True:

        frame = shared_camera.latest_frame

        if frame is None:

            frame = np.ones(
                (480, 640, 3),
                dtype=np.uint8
            ) * 30

            cv2.putText(
                frame,
                "WAITING FOR AI CAMERA...",
                (100, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )

        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if not success:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes +
            b"\r\n"
        )

        time.sleep(0.03)

@app.route("/video")
def video():

    if not is_login():
        return Response("Unauthorized", status=401)

    print("SESSION:", session)

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
# REPLAY API
# =============================================================================

BASE_RECORDED_FOLDER = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        "recorded_videos"
    )
)


@app.route("/api/replays")
def api_replays():

    if not is_login():
        return jsonify([])

    email = session.get("user", "")

    safe_email = (
        email
        .replace("@", "_")
        .replace(".", "_")
    )

    user_folder = os.path.join(
        BASE_RECORDED_FOLDER,
        safe_email
    )

    result = []

    if not os.path.exists(user_folder):
        return jsonify(result)

    level_labels = {
        "Minor":              "Minor",
        "Dangerous":          "Dangerous",
        "Critical_Emergency": "Critical Emergency",
    }

    for level, label in level_labels.items():

        level_path = os.path.join(
            user_folder,
            level
        )

        if not os.path.exists(level_path):
            continue

        for file in os.listdir(level_path):

            if file.endswith(".mp4"):

                result.append({

                    "level": level,

                    "label": label,

                    "file": file,

                    "url": f"/recorded/{safe_email}/{level}/{file}"
                })

    # newest first — filenames are timestamped (event_YYYYMMDD_HHMMSS.mp4)
    result.sort(key=lambda x: x["file"], reverse=True)

    return jsonify(result)


# =============================================================================
# VIDEO STREAM FILE
# =============================================================================

@app.route(
    "/recorded/<user>/<path:level>/<filename>"
)
def recorded_video(
    user,
    level,
    filename
):

    if not is_login():
        return Response("Unauthorized", status=401)

    # Prevent accessing another user's videos
    current_email = session.get("user", "")
    safe_email = (
        current_email
        .replace("@", "_")
        .replace(".", "_")
    )
    if user != safe_email:
        return Response("Forbidden", status=403)

    folder = os.path.join(
        BASE_RECORDED_FOLDER,
        user,
        level
    )

    return send_from_directory(
        folder,
        filename
    )
    
# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":

    import webbrowser
    from threading import Timer

    def open_browser():

        webbrowser.open_new(
            "http://127.0.0.1:5000"
        )

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