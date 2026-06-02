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

# FIX: read secret key from environment so it is not hardcoded.
app.secret_key = os.environ.get("SECRET_KEY", "aiot_fall_detection_2024")

app.config["SESSION_PERMANENT"]       = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"]   = False
# FIX: SameSite=Lax required so the session cookie is sent by browsers
# when SESSION_COOKIE_SECURE is False (i.e. plain HTTP).
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# FIX: do NOT pin async_mode here; it is inferred from the eventlet
# monkey-patch applied at the top of main.py.  Pinning it to "eventlet"
# while standard threading is also active caused intermittent errors.
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

# =============================================================================
# GLOBALS
# =============================================================================

engine_started = False

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


# FIX: converted to a proper decorator so routes can be written as:
#
#   @app.route("/dashboard")
#   @login_required
#   def dashboard(): ...
#
# The old pattern `return require_login() or render_template(…)` was
# correct but returned None (no redirect) if is_login() happened to
# return a falsy non-None value, which is a subtle latent bug.
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
# PAGES  (FIX: use @login_required decorator)
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
    FIX: the placeholder is encoded and yielded immediately instead of
    sleeping and continuing, which prevented the multipart boundary from
    being flushed and caused browsers to show a broken stream.
    """
    import shared_camera  # local import avoids circular-dependency issues

    while True:
        # ── Thread-safe frame read ────────────────────────────────────────
        with shared_camera.frame_lock:
            raw = shared_camera.latest_frame
            frame = raw.copy() if raw is not None else None

        if frame is None:
            frame = _get_placeholder()

        # ── Encode to JPEG ────────────────────────────────────────────────
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            # FIX: still yield the boundary so the browser doesn't stall;
            # yield the placeholder instead of skipping the frame entirely.
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

        # ~30 fps cap
        time.sleep(0.03)


@app.route("/video")
def video():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

# =============================================================================
# REALTIME ENGINE (SocketIO)
# =============================================================================

def realtime_engine():
    import shared_camera

    while True:
        with shared_camera.frame_lock:
            state = shared_camera.current_state
            risk = shared_camera.current_risk
            level = shared_camera.current_level
            severity = shared_camera.current_severity
    

        socketio.emit("update", {
            "status": state or "NO_DATA",
            "state": state or "NO_DATA",

            "risk": risk if risk is not None else 0,

            "l1": severity if level == "MINOR" else 0,
            "l2": severity if level == "DANGEROUS" else 0,
            "l3": severity if level == "CRITICAL" else 0,

            "severity": severity or 0,
            "level": level or "",

            "time": time.strftime("%H:%M:%S"),
        })
        socketio.sleep(0.2)


@socketio.on("connect")
def handle_connect():
    global engine_started
    if not engine_started:
        socketio.start_background_task(realtime_engine)
        engine_started = True

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

    for level in ("Minor", "Dangerous", "Critical Emergency"):
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