"""
main.py
────────
ICU Monitoring System — entry point.

Responsibilities
────────────────
1. Open the camera via CameraStream (background-threaded).
2. Feed frames through FallDetectionPipeline (pose → TCN → label).
3. Manage a risk score and a state machine (NORMAL / FALLING).
4. Trigger EventManager to start/stop video recording and send alerts.
5. Publish the most recent annotated frame to shared_camera so the
   Flask dashboard can serve it as an MJPEG stream.

State machine
─────────────
  NORMAL  → FALLING  : when pipeline returns fall_flag = True
  FALLING → NORMAL   : when fall_flag is False for RECOVERY_SECONDS
                        consecutive seconds

Changes vs. original
─────────────────────
- shared_camera writes now use frame_lock (thread-safe).
- Camera index is configurable via CAMERA_INDEX constant.
- CameraStream failure during runtime is handled with a reconnect
  back-off instead of calling exit() inside the loop.
- Risk score update logic is unchanged but extracted to _update_risk()
  for clarity.
- Removed unused cv2.putText display block (no cv2.imshow in server
  mode); kept it as optional behind SHOW_PREVIEW flag.
- All bare `except Exception` blocks now print the full traceback so
  silent bugs surface immediately.
- Imports are consolidated at the top (PEP 8).
- `finally` block now calls event_manager.stop_and_save() to flush any
  open recording when the process is killed.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback

import cv2

import shared_camera

from AI_Training.realtime.pipeline import FallDetectionPipeline
from services.event_manager import EventManager
from services.camera_thread import CameraStream

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "dashboard", "users.json")

# Camera index (0 = default webcam, 1 = second camera, or an RTSP URL)
CAMERA_INDEX = 1

# How many seconds without a fall before transitioning back to NORMAL
RECOVERY_SECONDS = 5

# Risk score change per frame
RISK_INCREMENT = 5
RISK_DECREMENT = 3

# Set to True to open a local preview window (requires a display)
SHOW_PREVIEW = False


# ── User helper ───────────────────────────────────────────────────────────────

def get_current_logged_user() -> str | None:
    """
    Return the decrypted e-mail address of the currently logged-in user,
    or None if no user is logged in or the users file does not exist.
    """
    if not os.path.exists(USERS_FILE):
        return None

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users: dict = json.load(f)

        for enc_email, data in users.items():
            if data.get("is_logged_in") is True:
                # Import lazily to avoid a circular dependency at module load
                from dashboard.security import decrypt_text
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


# ── Overlay helper ────────────────────────────────────────────────────────────

def _draw_overlay(frame, state: str, risk_score: int) -> None:
    """Draw state and risk-score text onto *frame* in-place."""
    state_color = (0, 255, 0) if state == "NORMAL" else (0, 0, 255)

    cv2.putText(
        frame, f"State: {state}",
        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
        state_color, 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, f"Risk Score: {risk_score}",
        (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
        (255, 255, 0), 2, cv2.LINE_AA,
    )


# ── Initialisation ────────────────────────────────────────────────────────────

pipeline      = FallDetectionPipeline()
event_manager = EventManager()

try:
    camera = CameraStream(CAMERA_INDEX)
except Exception:
    traceback.print_exc()
    sys.exit(1)

# ── State ─────────────────────────────────────────────────────────────────────

state           : str         = "NORMAL"
risk_score      : int         = 0
recovery_start  : float | None = None

print("🏥 ICU MONITORING SYSTEM STARTED")

# ── Main loop ─────────────────────────────────────────────────────────────────

try:
    while True:

        # ── Identify logged-in user ──────────────────────────────────────
        current_user = get_current_logged_user()

        # ── Read frame ───────────────────────────────────────────────────
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

        # ── Publish annotated frame (thread-safe) ────────────────────────
        with shared_camera.frame_lock:
            shared_camera.latest_frame = frame.copy()

        # ── Risk score ───────────────────────────────────────────────────
        risk_score = _update_risk(risk_score, fall_flag)

        # ── State machine ────────────────────────────────────────────────
        if fall_flag:
            # ── FALL detected ────────────────────────────────────────────
            recovery_start = None
            state          = "FALLING"

            if not event_manager.recording:
                print("🚨 FALL DETECTED")
                if current_user:
                    print(f"[USER] {current_user}")
                else:
                    print("[WARNING] No user logged in — alert not sent")

            # Always update recording (refreshes severity on every frame)
            event_manager.start_recording(
                severity=emergency_level,
                email=current_user,
            )

        else:
            # ── No fall — start / advance recovery timer ─────────────────
            if event_manager.recording:
                if recovery_start is None:
                    recovery_start = time.time()

                if time.time() - recovery_start >= RECOVERY_SECONDS:
                    print("✅ RECOVERY STABLE — stopping recording")
                    state = "NORMAL"

                    try:
                        event_manager.stop_and_save()
                    except Exception:
                        traceback.print_exc()

                    recovery_start = None

        # ── Overlay ──────────────────────────────────────────────────────
        _draw_overlay(frame, state, risk_score)

        # ── Optional local preview ───────────────────────────────────────
        if SHOW_PREVIEW:
            cv2.imshow("ICU Monitor", frame)
            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                print("[PREVIEW] Quit key pressed — stopping")
                break

# ── Graceful shutdown ─────────────────────────────────────────────────────────

finally:
    print("[SYSTEM] Releasing resources …")

    # Flush any open recording before exiting
    if event_manager.recording:
        try:
            event_manager.stop_and_save()
        except Exception:
            traceback.print_exc()

    try:
        camera.release()
    except Exception:
        traceback.print_exc()

    cv2.destroyAllWindows()
    print("🏥 System stopped")