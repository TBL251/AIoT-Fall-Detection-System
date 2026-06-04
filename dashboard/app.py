import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from flask import (
    Flask,
    render_template,
    redirect,
    request,
    jsonify,
    Response,
    session,
)
from flask_socketio import SocketIO
from flask import send_from_directory

import functools
import threading
import cv2
import time
import json
import re
import numpy as np

from werkzeug.security import generate_password_hash, check_password_hash

from dashboard.auth import login_user, logout_user, is_login, create_user_folder
from dashboard.mail import send_otp, verify_otp
from dashboard.security import encrypt_text, decrypt_text

# =============================================================================
# APP
# =============================================================================

app = Flask(__name__)

# Read secret key from environment; fall back to a dev default with a warning.
_secret = os.environ.get("SECRET_KEY")
if not _secret:
    import warnings
    warnings.warn(
        "SECRET_KEY env-var is not set — using insecure default. "
        "Set SECRET_KEY in production!",
        stacklevel=1,
    )
    _secret = "aiot_fall_detection_2024"

app.secret_key = _secret

app.config["SESSION_PERMANENT"]       = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"]   = False   # set True behind HTTPS
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",   # matches the threading async_mode in main.py
)

# =============================================================================
# GLOBALS
# =============================================================================

# FIX: protect engine_started with a lock to prevent two concurrent
# "connect" events from each spawning their own background task.
_engine_lock    = threading.Lock()
_engine_started = False

# FIX: single ESP32 controller instance shared by the background engine.
# Lazily created the first time it is needed so that import-time serial
# errors don't crash the whole dashboard process.
_esp32_controller      = None
_esp32_controller_lock = threading.Lock()


def _get_esp32():
    """Return (creating if necessary) the shared ESP32Controller instance."""
    global _esp32_controller
    with _esp32_controller_lock:
        if _esp32_controller is None:
            try:
                from services.esp32_service import ESP32Controller
                _esp32_controller = ESP32Controller()
            except Exception as e:
                print("[ESP32] Could not create controller:", e)
        return _esp32_controller

# =============================================================================
# USER DATABASE
# =============================================================================

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")

# =============================================================================
# LOAD / SAVE USERS
# =============================================================================

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users_data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=4, ensure_ascii=False)


users = load_users()

# =============================================================================
# HELPERS
# =============================================================================

def valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)


def email_exists(email):
    for enc_email in users:
        try:
            if decrypt_text(enc_email) == email:
                return True
        except Exception:
            pass
    return False


def get_user_by_email(email):
    for enc_email, user_data in users.items():
        try:
            if decrypt_text(enc_email) == email:
                return user_data
        except Exception:
            pass
    return None


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not is_login():
            return redirect("/")
        return f(*args, **kwargs)
    return decorated

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

    data  = request.get_json()
    email = data.get("email", "").strip()
    pw    = data.get("password", "").strip()

    if not email or not pw:
        return jsonify({"ok": False, "msg": "Please enter email and password"})

    user = get_user_by_email(email)
    if not user:
        return jsonify({"ok": False, "msg": "Email does not exist"})

    if not check_password_hash(user.get("password", ""), pw):
        return jsonify({"ok": False, "msg": "Wrong password"})

    login_user(email)

    for enc_email in users:
        users[enc_email]["is_logged_in"] = False
    for enc_email in users:
        try:
            if decrypt_text(enc_email) == email:
                users[enc_email]["is_logged_in"] = True
        except Exception:
            pass

    save_users(users)
    print(f"[LOGIN] {email}")
    return jsonify({"ok": True, "msg": "Login success"})

# =============================================================================
# REGISTER PAGE
# =============================================================================

@app.route("/register")
def register_page():
    return render_template("register.html")

# =============================================================================
# SEND OTP
# =============================================================================

@app.route("/send-otp", methods=["POST"])
def route_send_otp():
    data  = request.get_json()
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"ok": False, "msg": "Email is required"})
    if not valid_email(email):
        return jsonify({"ok": False, "msg": "Invalid email format"})
    if email_exists(email):
        return jsonify({"ok": False, "msg": "Email already exists"})

    try:
        send_otp(email)
        return jsonify({"ok": True, "msg": "OTP sent to your email"})
    except Exception as e:
        print("OTP ERROR:", e)
        return jsonify({"ok": False, "msg": "Failed to send OTP"})

# =============================================================================
# VERIFY OTP
# =============================================================================

@app.route("/verify-otp", methods=["POST"])
def route_verify_otp():
    global users
    users = load_users()

    data  = request.get_json()
    email = data.get("email", "").strip()
    otp   = data.get("otp",   "").strip()
    name  = data.get("name",  "User").strip()
    pw    = data.get("password", "").strip()

    if not email or not otp or not pw:
        return jsonify({"ok": False, "msg": "Missing required fields"})
    if not verify_otp(email, otp):
        return jsonify({"ok": False, "msg": "Invalid or expired OTP"})
    if email_exists(email):
        return jsonify({"ok": False, "msg": "Email already exists"})

    hashed_password = generate_password_hash(pw)
    encrypted_email = encrypt_text(email)
    encrypted_name  = encrypt_text(name)

    for enc_email in users:
        users[enc_email]["is_logged_in"] = False

    users[encrypted_email] = {
        "name":         encrypted_name,
        "password":     hashed_password,
        "is_logged_in": True,
    }

    save_users(users)
    create_user_folder(email)
    login_user(email)
    print(f"[REGISTER] {email}")
    return jsonify({"ok": True, "msg": "Register success"})

# =============================================================================
# LOGOUT
# =============================================================================

@app.route("/logout")
def logout():
    global users
    # FIX: always reload from disk so we act on the current state.
    users = load_users()

    current_user = session.get("user")
    for enc_email in users:
        try:
            if decrypt_text(enc_email) == current_user:
                users[enc_email]["is_logged_in"] = False
        except Exception:
            pass

    save_users(users)
    logout_user()
    print("[LOGOUT]")
    return redirect("/")

# =============================================================================
# PAGES
# =============================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/charts")
@login_required
def charts():
    return render_template("charts.html")


@app.route("/live")
@login_required
def live():
    return render_template("live.html")


@app.route("/replay")
@login_required
def replay():
    return render_template("replay.html")


@app.route("/profile")
@login_required
def profile():
    current_user = session.get("user", "")
    user_name    = "Unknown"
    user_data    = get_user_by_email(current_user)

    if user_data:
        try:
            user_name = decrypt_text(user_data["name"])
        except Exception:
            pass

    return render_template(
        "profile.html",
        user_email=current_user,
        user_name=user_name,
    )

# =============================================================================
# VIDEO STREAM
# =============================================================================

_PLACEHOLDER_FRAME: np.ndarray | None = None


def _get_placeholder() -> np.ndarray:
    """Return (and cache) a dark 640×480 'waiting' frame."""
    global _PLACEHOLDER_FRAME
    if _PLACEHOLDER_FRAME is None:
        f = np.ones((480, 640, 3), dtype=np.uint8) * 30
        cv2.putText(
            f, "WAITING FOR AI CAMERA...",
            (80, 240), cv2.FONT_HERSHEY_SIMPLEX, 1,
            (255, 255, 255), 2,
        )
        _PLACEHOLDER_FRAME = f
    return _PLACEHOLDER_FRAME


def gen_frames():
    """
    MJPEG generator.

    Reads shared_camera.latest_frame under frame_lock on every iteration.
    Falls back to a placeholder when no frame is available so the multipart
    boundary is always flushed and browsers never see a broken stream.
    """
    import shared_camera  # local import avoids circular-dependency issues

    while True:
        with shared_camera.frame_lock:
            raw   = shared_camera.latest_frame
            frame = raw.copy() if raw is not None else None

        if frame is None:
            frame = _get_placeholder()

        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            # Yield placeholder so the browser doesn't stall.
            success, buffer = cv2.imencode(".jpg", _get_placeholder())
            if not success:
                time.sleep(0.03)
                continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )

        time.sleep(0.03)   # ~30 fps cap


# FIX: /video requires authentication — without this anyone on the network
# could watch the camera stream without logging in.
@app.route("/video")
@login_required
def video():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

# =============================================================================
# REALTIME ENGINE (SocketIO background task)
# =============================================================================

# FIX: track last sent severity inside the engine function scope via a
# mutable container so the value persists across iterations without relying
# on a module-level variable that can be clobbered by other threads.
_last_sent_severity = [-1]   # list used as mutable cell


def realtime_engine():
    import shared_camera

    while True:
        with shared_camera.frame_lock:
            state    = shared_camera.current_state
            risk     = shared_camera.current_risk
            level    = shared_camera.current_level
            # FIX: read current_severity (now written by main.py).
            severity = shared_camera.current_severity

        severity = int(severity or 0)

        # Send ESP32 alert only when severity changes.
        if severity != _last_sent_severity[0]:
            _last_sent_severity[0] = severity
            try:
                esp = _get_esp32()
                if esp is not None:
                    esp.send_alert(severity)
            except Exception as e:
                print("[ESP32 ERROR]", e)

        socketio.emit("update", {
            "status":   state or "NO_DATA",
            "state":    state or "NO_DATA",
            "risk":     risk  or 0,

            "l1": severity if level == "MINOR"     else 0,
            "l2": severity if level == "DANGEROUS" else 0,
            "l3": severity if level == "CRITICAL"  else 0,

            "severity": severity,
            "level":    level or "",
            "time":     time.strftime("%H:%M:%S"),
        })

        # FIX: async_mode=threading → use time.sleep, NOT socketio.sleep.
        # socketio.sleep() is only valid under eventlet/gevent async modes
        # and would block or raise under the threading backend.
        time.sleep(0.2)


@socketio.on("connect")
def handle_connect():
    global _engine_started
    # FIX: lock prevents two concurrent connect events from each starting
    # their own background engine task.
    with _engine_lock:
        if not _engine_started:
            socketio.start_background_task(realtime_engine)
            _engine_started = True

# =============================================================================
# REPLAY API
# =============================================================================

BASE_RECORDED_FOLDER = os.path.abspath(
    os.path.join(BASE_DIR, "..", "recorded_videos")
)


@app.route("/api/replays")
def api_replays():
    if not is_login():
        return jsonify([])

    email       = session.get("user", "")
    safe_email  = email.replace("@", "_").replace(".", "_")
    user_folder = os.path.join(BASE_RECORDED_FOLDER, safe_email)
    result      = []

    if not os.path.exists(user_folder):
        return jsonify(result)

    for level in ("Minor", "Dangerous", "Critical_Emergency"):
        level_path = os.path.join(user_folder, level)
        if not os.path.exists(level_path):
            continue
        for file in os.listdir(level_path):
            if file.endswith(".mp4"):
                result.append({
                    "level": level,
                    "file":  file,
                    "url":   f"/recorded/{safe_email}/{level}/{file}",
                })

    result.reverse()   # newest first
    return jsonify(result)


@app.route("/recorded/<user>/<level>/<filename>")
def recorded_video(user, level, filename):
    folder = os.path.join(BASE_RECORDED_FOLDER, user, level)
    return send_from_directory(folder, filename)

# =============================================================================
# DO NOT add an `if __name__ == "__main__"` block here.
# The app is started by main.py via _start_dashboard().
# =============================================================================