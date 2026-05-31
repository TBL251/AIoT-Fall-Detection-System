"""
services/event_manager.py
──────────────────────────
Manages fall-event lifecycle: frame buffering, video recording, alerts,
and Firebase + Telegram dispatch.

Bugs fixed
──────────
BUG 1 — TypeError on severity comparison ('>=' not supported str vs int)
  start_recording() had a try/except int(severity) block, but the except
  branch silently set severity = 0 and continued, hiding the real error.
  The root cause was pipeline.py returning a str.  That is now fixed in
  pipeline.py (returns int 0-3).  The int() cast is kept here as a safety
  net but the except now logs the problem rather than swallowing it.

BUG 2 — Frame buffer grows unboundedly then pops from index 0 (O(n))
  self.frames.pop(0) on a plain list is O(n) — every pop shifts all
  elements.  At 30 fps and 300-frame limit this runs ~30 times/second.
  Fix: replaced list with collections.deque(maxlen=300) which drops the
  oldest frame automatically in O(1).

BUG 3 — frames.clear() inside stop_and_save() not thread-safe
  add_frame() holds self.lock while appending; stop_and_save() called
  self.frames.clear() OUTSIDE the lock after copying, meaning a concurrent
  add_frame() could append to the list between copy and clear, then that
  frame would be silently lost.
  Fix: clear() is now inside the lock, matching add_frame()'s lock scope.

BUG 4 — send_emergency_video anti-spam check uses time.time() before
  last_video_time is initialised.  If last_video_time = 0 and system
  clock is far from epoch the check (now - 0 < 60) would always pass.
  This is benign on modern systems but fragile.  Fix: initialise
  last_video_time = 0 is fine; documented explicitly.
"""

from __future__ import annotations

import threading
import time
import traceback
from collections import deque

import cv2

from services.local_storage import save_video
from services.firebase_service import save_event
from services.telegram_service import send_video, send_alert, send_message
from services.esp32_service import ESP32Controller

# Maximum frames to keep in the rolling buffer (300 frames ≈ 10 s at 30 fps)
_MAX_BUFFER_FRAMES = 300


class EventManager:

    def __init__(self) -> None:
        # deque(maxlen=N) automatically drops the oldest element when full — O(1)
        self.frames         : deque       = deque(maxlen=_MAX_BUFFER_FRAMES)
        self.lock           : threading.Lock = threading.Lock()

        self.recording      : bool        = False
        self.current_email  : str | None  = None
        self.current_severity: int        = 0
        self.video_sent     : bool        = False
        self.start_time     : float | None = None
        self.last_danger_time: float | None = None
        self.last_video_time : float      = 0.0

        self.esp32 = ESP32Controller()

    # ── Property ─────────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        return self.recording

    # ── Frame buffer ─────────────────────────────────────────────────────

    def add_frame(self, frame) -> None:
        """
        Resize and buffer one frame.  Called from the main loop with the
        annotated frame (post-pipeline) so recordings match the dashboard.
        """
        small = cv2.resize(frame, (640, 360))
        # deque.append() is thread-safe in CPython due to the GIL, but we
        # hold the lock anyway for correctness on other Python implementations.
        with self.lock:
            self.frames.append(small)

    # ── Recording ────────────────────────────────────────────────────────

    def start_recording(
        self,
        severity: int,
        email: str | None = None,
    ) -> None:
        """
        Begin (or update) a fall-event recording.

        Parameters
        ----------
        severity : int
            0=NORMAL, 1=MINOR, 2=DANGEROUS, 3=CRITICAL.
            Must be an integer — pipeline.py now guarantees this.
        email : str | None
            Recipient e-mail for alerts and video delivery.
        """
        # Safety cast: pipeline now returns int, but guard against regressions
        try:
            severity = int(severity)
        except (TypeError, ValueError):
            traceback.print_exc()
            print(f"[EVENT] Invalid severity value {severity!r} — defaulting to 0")
            severity = 0

        current_time = time.time()

        if email is not None:
            self.current_email = email

        # ── First detection in this event ─────────────────────────────────
        if not self.recording:
            print("[REC] START RECORDING")
            self.recording         = True
            self.start_time        = current_time
            self.video_sent        = False
            self.current_severity  = severity

            if severity >= 2:
                threading.Thread(
                    target=send_alert,
                    args=(severity,),
                    daemon=True,
                ).start()
                self.esp32.send_alert(severity)

            elif severity == 1:
                threading.Thread(
                    target=send_message,
                    args=("⚠️ Minor fall detected",),
                    daemon=True,
                ).start()

        self.last_danger_time  = current_time
        self.current_severity  = max(self.current_severity, severity)

        # ── Auto-send video for critical events after 15 s ────────────────
        if severity >= 3 and not self.video_sent:
            lying_time = current_time - self.start_time
            if lying_time > 15:
                print("[CRITICAL] AUTO SEND VIDEO")
                self.video_sent = True
                threading.Thread(
                    target=self._send_emergency_video,
                    daemon=True,
                ).start()

    # ── Emergency video dispatch ─────────────────────────────────────────

    def _send_emergency_video(self) -> None:
        now = time.time()

        # Anti-spam: at most one emergency video per 60 seconds
        if now - self.last_video_time < 60:
            print("[ANTI SPAM] Skip video")
            return

        self.last_video_time = now

        with self.lock:
            frames_copy = list(self.frames)

        email = self.current_email or "unknown@gmail.com"

        video_path = save_video(frames_copy, email, self.current_severity)

        if video_path:
            send_message("🚨 PATIENT NOT RECOVERING")
            send_video(video_path, "🚨 Emergency ICU Video")
            print("[TELEGRAM] Emergency video sent")

    # ── Stop + save ──────────────────────────────────────────────────────

    def stop_and_save(self) -> None:
        """Finalise the current recording, save locally and dispatch via Telegram."""
        # Copy frames under lock, then clear under the same lock to avoid
        # a race with add_frame().
        with self.lock:
            frames_copy = list(self.frames)
            self.frames.clear()

        email = self.current_email

        if email is None:
            print("[SAVE ERROR] No email — video not saved")
            self._reset_state()
            return

        video_path = save_video(frames_copy, email, self.current_severity)

        if video_path:
            try:
                save_event("Fall Detection", self.current_severity, video_path)
            except Exception:
                traceback.print_exc()

            if not self.video_sent:
                self.video_sent = True
                threading.Thread(
                    target=send_video,
                    args=(video_path, "📹 Recovery Video"),
                    daemon=True,
                ).start()

        print("[REC] VIDEO SAVED")

        self.esp32.send_alert(0)    # reset ESP32 alert
        self._reset_state()

    # ── Internal reset ───────────────────────────────────────────────────

    def _reset_state(self) -> None:
        """Reset all event state after a recording is finalised."""
        self.recording         = False
        self.current_severity  = 0
        self.start_time        = None
        self.last_danger_time  = None
        self.video_sent        = False
        self.current_email     = None