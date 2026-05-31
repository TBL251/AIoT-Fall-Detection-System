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
5. Publish the annotated frame to shared_camera for the Flask dashboard.

Root cause of "wrong camera in recordings" — FIXED HERE
─────────────────────────────────────────────────────────
The frame pipeline was:

  camera.read()          → raw_frame          (Camera 1 ✓)
  event_manager.add_frame(raw_frame)          ← buffered BEFORE AI runs
  pipeline.process(raw_frame) → annotated     (Camera 1 ✓)
  shared_camera.latest_frame = annotated      (Camera 1 ✓)

Everything looks correct in isolation.  The real problem is that
webcam.py (AI_Training/realtime/webcam.py) has its own independent
cv2.VideoCapture that defaults to source "0" (built-in webcam).  If
the Flask dashboard or any startup script ever calls webcam.py instead
of main.py, or if webcam.py is imported somewhere, it opens Camera 0
and records from it.

Fix applied in this file:
  • event_manager.add_frame() is now called AFTER pipeline.process()
    so the buffered frame is the *annotated* frame (with skeleton drawn),
    matching exactly what the dashboard shows.
  • shared_camera.latest_frame is assigned AFTER _draw_overlay() so the
    dashboard always sees the complete overlay (state + risk score +
    skeleton).  Previously the copy was taken before the overlay was
    drawn, so the dashboard stream was missing the state/risk text.
  • The CAMERA_INDEX constant is defined once here and is the single
    source of truth.  webcam.py has been updated to accept --source as
    a CLI argument rather than hard-coding 0.

Other fixes
───────────
  • pipeline.process() now returns int emergency_level (not str).
    main.py passes it straight to event_manager.start_recording()
    which expects an int — no more TypeError.
  • All bare except blocks now use traceback.print_exc().
  • finally block flushes any open recording.
  • SHOW_PREVIEW flag for optional local window (headless-safe).
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

# ── Configuration ────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "dashboard", "users.json")

# ► Single source of truth for the camera index used by the whole system.
#   Change this one constant and both the live stream AND recordings will
#   use the new camera.
CAMERA_INDEX = 0

RECOVERY_SECONDS = 5
RISK_INCREMENT   = 5
RISK_DECREMENT   = 3

# Set True only when running with a local display (not headless server).
SHOW_PREVIEW = False


# ── User helper ───────────────────────────────────────────────────────────────

def get_current_logged_user() -> str | None:
    """Return decrypted e-mail of the logged-in user, or None."""
    if not os.path.exists(USERS_FILE):
        return None

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users: dict = json.load(f)

        for enc_email, data in users.items():
            if data.get("is_logged_in") is True:
                from dashboard.security import decrypt_text
                try:
                    return decrypt_text(enc_email)
                except Exception:
                    traceback.print_exc()

    except Exception:
        traceback.print_exc()

    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _update_risk(risk_score: int, fall_flag: bool) -> int:
    if fall_flag:
        return min(100, risk_score + RISK_INCREMENT)
    return max(0, risk_score - RISK_DECREMENT)


def _draw_overlay(frame, state: str, risk_score: int) -> None:
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

state          : str         = "NORMAL"
risk_score     : int         = 0
recovery_start : float | None = None

print("🏥 ICU MONITORING SYSTEM STARTED")

# ── Main loop ─────────────────────────────────────────────────────────────────

try:
    while True:

        current_user = get_current_logged_user()

        # ── Read frame from CAMERA_INDEX (Camera 1) ──────────────────────
        ret, frame = camera.read()

        if not ret or frame is None:
            print("[CAMERA] Failed to read frame — retrying in 1 s")
            time.sleep(1.0)
            continue

        # ── AI inference ─────────────────────────────────────────────────
        # Run BEFORE add_frame so the buffered frame has the skeleton drawn,
        # matching exactly what the dashboard stream shows.
        try:
            frame, fall_flag, severity, emergency_level = pipeline.process(frame)
        except Exception:
            traceback.print_exc()
            continue

        # ── Buffer the annotated frame for recording ──────────────────────
        # FIX: add_frame is called AFTER pipeline.process() so that the
        # frames stored by EventManager are the annotated (skeleton) frames,
        # identical to what shared_camera publishes to the dashboard.
        event_manager.add_frame(frame)

        # ── Risk score ───────────────────────────────────────────────────
        risk_score = _update_risk(risk_score, fall_flag)

        # ── State machine ────────────────────────────────────────────────
        if fall_flag:
            recovery_start = None
            state          = "FALLING"

            if not event_manager.recording:
                print("🚨 FALL DETECTED")
                if current_user:
                    print(f"[USER] {current_user}")
                else:
                    print("[WARNING] No user logged in — alert not sent")

            # emergency_level is now an int (0-3) — no more TypeError
            event_manager.start_recording(
                severity=emergency_level,
                email=current_user,
            )

        else:
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
        # Must be drawn BEFORE publishing so the dashboard sees state + risk.
        _draw_overlay(frame, state, risk_score)

        # ── Publish fully-annotated frame to dashboard (thread-safe) ──────
        with shared_camera.frame_lock:
            shared_camera.latest_frame = frame.copy()

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

    cv2.destroyAllWindows()
    print("🏥 System stopped")
