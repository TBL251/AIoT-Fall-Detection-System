
import json
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser

import cv2

import shared_camera

from AI_Training.realtime.pipeline import FallDetectionPipeline
from services.event_manager import EventManager
from services.camera_thread import CameraStream
from dashboard.security import decrypt_text          # single import, not per-frame

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "dashboard", "users.json")

# Camera index: 0 = default webcam, 1 = second camera, or an RTSP URL string.
# FIX: was 1 — if your machine only has one webcam this caused a silent crash
#      that killed the process before Flask ever started.  Set back to 1 only
#      if you physically have a second camera attached.
CAMERA_INDEX = 0

# How many consecutive seconds without a fall before returning to NORMAL.
RECOVERY_SECONDS = 1

# Risk score change per frame.
RISK_INCREMENT = 5
RISK_DECREMENT = 3

# Set True to open a local cv2.imshow preview (requires a display).
SHOW_PREVIEW = False

# Flask dashboard configuration.
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# How long (seconds) to wait for Flask to bind its port before the main
# loop starts.  Increased from 1 s — model loading can be slow.
DASHBOARD_STARTUP_TIMEOUT = 15


# ── Dashboard launcher ────────────────────────────────────────────────────────

def _wait_for_port(host: str, port: int, timeout: float = DASHBOARD_STARTUP_TIMEOUT) -> bool:
    """
    Block until the given TCP port is accepting connections or timeout
    expires.  Returns True if the port opened in time, False otherwise.
    Used so the main loop only starts printing after Flask is ready.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host if host != "0.0.0.0" else "127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _start_dashboard() -> None:
    """
    Import and run the Flask/SocketIO app in this thread.

    Called from a daemon Thread so it shuts down automatically when
    main.py exits.  Any import or startup error is printed but does NOT
    kill the AI loop — monitoring continues even if the web UI fails.
    """
    try:
        # Late import: shared_camera.camera is already set by the time
        # this thread actually calls socketio.run(), because the main
        # thread sets shared_camera.camera *before* starting this thread
        # and then does a small sleep.
        from dashboard.app import socketio, app
        print(f"[DASHBOARD] Starting on http://127.0.0.1:{DASHBOARD_PORT}")
        socketio.run(
            app,
            host=DASHBOARD_HOST,
            port=DASHBOARD_PORT,
            debug=False,        # debug=True would spawn a second process and break things
            use_reloader=False, # reloader is incompatible with threading mode
        )
    except Exception:
        print("[DASHBOARD ERROR] Failed to start dashboard — web UI unavailable.", file=sys.stderr)
        traceback.print_exc()


# ── User helper ───────────────────────────────────────────────────────────────

def get_current_logged_user() -> str | None:
    """
    Return the decrypted e-mail of the currently logged-in user,
    or None if no user is logged in or the users file does not exist.

    FIX: decrypt_text is now imported once at module level instead of
    being re-imported inside this function on every single frame.
    """
    if not os.path.exists(USERS_FILE):
        return None

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users: dict = json.load(f)

        for enc_email, data in users.items():
            if data.get("is_logged_in") is True:
                try:
                    return decrypt_text(enc_email)
                except Exception:
                    traceback.print_exc()

    except Exception:
        traceback.print_exc()

    return None


# ── Risk score helper ─────────────────────────────────────────────────────────

def _update_risk(risk_score: int, fall_flag: bool) -> int:
    if fall_flag:
        return min(100, risk_score + RISK_INCREMENT)
    return max(0, risk_score - RISK_DECREMENT)


# ── Initialisation ────────────────────────────────────────────────────────────

# 1. Open the camera ONCE and store it in shared_camera so no other
#    module ever needs to open a second VideoCapture.
try:
    camera = CameraStream(CAMERA_INDEX)
except Exception:
    print(f"[CAMERA ERROR] Could not open camera index {CAMERA_INDEX}.", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

with shared_camera.frame_lock:
    shared_camera.camera = camera

# 2. Initialise AI pipeline and event manager.
pipeline      = FallDetectionPipeline()
event_manager = EventManager()

# 3. Launch the Flask dashboard in a background daemon thread.
#    FIX: started here, AFTER shared_camera.camera is set, so Flask
#    can immediately serve the /video stream without hitting None.
dashboard_thread = threading.Thread(
    target=_start_dashboard,
    name="FlaskDashboard",
    daemon=True,
)
dashboard_thread.start()

# FIX: wait until Flask actually binds its port instead of sleeping a
# fixed 1 second (which was too short on slow machines / cold starts).
print(f"[MAIN] Waiting for dashboard to bind port {DASHBOARD_PORT} …")
if _wait_for_port("0.0.0.0", DASHBOARD_PORT, timeout=DASHBOARD_STARTUP_TIMEOUT):
    print(f"[MAIN] Dashboard ready → http://127.0.0.1:{DASHBOARD_PORT}")
    
    try:
        webbrowser.open(f"http://127.0.0.1:{DASHBOARD_PORT}")
    except Exception:
        traceback.print_exc()
else:
    print(
        f"[MAIN WARNING] Dashboard did not bind within {DASHBOARD_STARTUP_TIMEOUT} s — "
        "web UI may be unavailable, but AI monitoring will continue.",
        file=sys.stderr,
    )

# ── State ─────────────────────────────────────────────────────────────────────

state          : str          = "NORMAL"
risk_score     : int          = 0
recovery_start : float | None = None

print("🏥 ICU MONITORING SYSTEM STARTED")

# ── Main loop ─────────────────────────────────────────────────────────────────

try:
    while True:

        # ── Identify logged-in user (read file at most once per frame) ───
        current_user = get_current_logged_user()

        # ── Read frame from the shared camera ────────────────────────────
        ret, frame = camera.read()

        if not ret or frame is None:
            print("[CAMERA] Failed to read frame — retrying in 1 s")
            time.sleep(1.0)
            continue

        # ── Buffer frame for recording ───────────────────────────────────
        event_manager.add_frame(frame)

        # ── AI inference ─────────────────────────────────────────────────
        try:
            frame, fall_flag, severity, emergency_level = pipeline.process(frame)
        except Exception:
            traceback.print_exc()
            continue

        # ── Publish annotated frame (thread-safe) ─────────────────────────
        with shared_camera.frame_lock:
            shared_camera.latest_frame = frame.copy()


        # ── State machine ────────────────────────────────────────────────
        if fall_flag:
            recovery_start = None
            state          = "FALLING"

            if not event_manager.recording:
                print("🚨 FALL DETECTED")
                if current_user:
                    print(f"[USER] {current_user}")
                else:
                    print("[WARNING] No user logged in — alert will not be sent")

            event_manager.start_recording(
                severity=emergency_level,
                email=current_user,
            )

        else:
            if not event_manager.recording:
                state = "NORMAL"

            else:
                if recovery_start is None:
                    recovery_start = time.time()

                if time.time() - recovery_start >= RECOVERY_SECONDS:
                    state = "NORMAL"

                    try:
                        event_manager.stop_and_save()
                    except Exception:
                        traceback.print_exc()

                    recovery_start = None
        
        # ── Risk score ───────────────────────────────────────────────────
        risk_score = _update_risk(risk_score, fall_flag)

        with shared_camera.frame_lock:
            shared_camera.latest_frame = frame.copy()

            shared_camera.current_state = state
            shared_camera.current_risk = risk_score

            shared_camera.current_level = emergency_level
            shared_camera.current_severity = severity
        

        # ── Optional local preview ───────────────────────────────────────
        if SHOW_PREVIEW:
            cv2.imshow("ICU Monitor", frame)
            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                print("[PREVIEW] Quit key pressed — stopping")
                break

# ── Graceful shutdown ─────────────────────────────────────────────────────────

finally:
    print("[SYSTEM] Releasing resources …")

    if event_manager.recording:
        try:
            event_manager.stop_and_save()
        except Exception:
            traceback.print_exc()

    try:
        camera.release()
    except Exception:
        traceback.print_exc()

    # Clear the shared reference so Flask gen_frames() renders the
    # "waiting" placeholder rather than a stale frozen frame.
    with shared_camera.frame_lock:
        shared_camera.camera       = None
        shared_camera.latest_frame = None

    cv2.destroyAllWindows()
    print("🏥 System stopped")

