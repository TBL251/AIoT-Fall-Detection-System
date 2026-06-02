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
from dashboard.security import decrypt_text


# =========================
# CONFIG
# =========================

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "dashboard", "users.json")

CAMERA_INDEX = 0
RECOVERY_SECONDS = 2.5

DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000
DASHBOARD_STARTUP_TIMEOUT = 15

SHOW_PREVIEW = False


# =========================
# WAIT PORT
# =========================

def _wait_for_port(host, port, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection(
                ("127.0.0.1" if host == "0.0.0.0" else host, port),
                timeout=0.5,
            ).close()
            return True
        except Exception:
            time.sleep(0.2)
    return False


# =========================
# DASHBOARD THREAD
# =========================

def _start_dashboard():
    try:
        from dashboard.app import socketio, app
        print(f"[DASHBOARD] http://127.0.0.1:{DASHBOARD_PORT}")

        socketio.run(
            app,
            host=DASHBOARD_HOST,
            port=DASHBOARD_PORT,
            debug=False,
            use_reloader=False,
        )

    except Exception:
        traceback.print_exc()


# =========================
# USER LOGIN
# =========================

def get_current_logged_user():
    if not os.path.exists(USERS_FILE):
        return None

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)

        for enc_email, data in users.items():
            if data.get("is_logged_in"):
                try:
                    return decrypt_text(enc_email)
                except Exception:
                    pass
    except Exception:
        pass

    return None


# =========================
# INIT CAMERA
# =========================

# FIX: start the dashboard thread first so that it can begin accepting
# connections while the camera and pipeline initialise, avoiding a
# potential race where the dashboard is not ready when the main loop
# starts writing to shared_camera.
threading.Thread(target=_start_dashboard, daemon=True).start()

print("[MAIN] Waiting for dashboard...")
_wait_for_port("0.0.0.0", DASHBOARD_PORT, DASHBOARD_STARTUP_TIMEOUT)

try:
    webbrowser.open(f"http://127.0.0.1:{DASHBOARD_PORT}")
except Exception:
    pass

print("[MAIN] STARTED")

# Initialise heavy objects after the dashboard is up.
camera = CameraStream(CAMERA_INDEX)

with shared_camera.frame_lock:
    shared_camera.camera = camera

pipeline      = FallDetectionPipeline()
event_manager = EventManager()


# =========================
# STATE
# =========================

state          = "NORMAL"
recovery_start = None

last_fall_flag = False


# =========================
# MAIN LOOP
# =========================

try:
    while True:

        user = get_current_logged_user()

        ret, frame = camera.read()
        if not ret:
            continue

        event_manager.add_frame(frame)

        try:
            # pipeline.process returns (annotated_frame, fall_flag, severity, level_str)
            # severity  – numeric score (float or int)
            # level_str – human label: "MINOR" | "DANGEROUS" | "CRITICAL" | ""
            frame, fall_flag, severity, level_str = pipeline.process(frame)
        except Exception:
            traceback.print_exc()
            continue

        # Clamp severity to a valid int in [0, 3].
        try:
            severity_int = int(severity)
        except Exception:
            severity_int = 0
        severity_int = max(0, min(severity_int, 3))

        # =========================
        # FALL LOGIC
        # =========================
        if fall_flag:

            state          = "FALLING"
            recovery_start = None

            # The pipeline can return fall_flag=True with severity=0 on the
            # first frame before its internal timer accumulates a score.
            # Clamp to 1 (MINOR) so we never send a NORMAL/STOP signal to
            # the ESP32 while a fall is actively detected.
            if severity_int == 0:
                severity_int = 1

            # Trigger a new recording event on the rising edge.
            if not last_fall_flag:
                print("🚨 FALL DETECTED")
                event_manager.start_recording(
                    severity=severity_int,
                    email=user,
                )

            # Keep the ESP32 buzzer alive on EVERY tick while falling.
            # send_alert() has its own 200 ms rate-limit so this is safe
            # to call at camera frame-rate; it feeds the ESP32 safety
            # timeout (10 s) so the buzzer never silences mid-fall.
            event_manager.keepalive_esp32(severity_int)

        else:

            event_manager.keepalive_esp32(0)

            if not event_manager.recording:
                state = "NORMAL"
            else:
                if recovery_start is None:
                    recovery_start = time.time()

                if time.time() - recovery_start > RECOVERY_SECONDS:
                    state          = "NORMAL"
                    recovery_start = None
                    event_manager.stop_and_save()

        last_fall_flag = fall_flag

        # =========================
        # SHARED STATE
        # =========================
        with shared_camera.frame_lock:
            shared_camera.latest_frame    = frame.copy()
            shared_camera.current_state   = state
            # FIX: risk_score comes from the pipeline's severity score so
            # the dashboard gauge shows real data instead of always 0.
            shared_camera.current_risk    = severity_int
            # FIX: keep level as the original string so app.py can do
            # level == "MINOR" / "DANGEROUS" / "CRITICAL" comparisons.
            shared_camera.current_level   = level_str
            # FIX: write current_severity — app.py's realtime_engine reads
            # this field; it was never set before, causing AttributeError.
            shared_camera.current_severity = severity_int

        # =========================
        # PREVIEW
        # =========================
        if SHOW_PREVIEW:
            cv2.imshow("ICU", frame)
            if cv2.waitKey(1) == 27:
                break

finally:
    print("[SYSTEM STOP]")

    try:
        camera.release()
    except Exception:
        pass

    with shared_camera.frame_lock:
        shared_camera.camera       = None
        shared_camera.latest_frame = None

    cv2.destroyAllWindows()