import collections
import cv2
import time
import threading

from services.local_storage import save_video
from services.firebase_service import save_event
from services.telegram_service import send_video, send_alert, send_message
from services.esp32_service import ESP32Controller


class EventManager:

    def __init__(self):

        # ======================
        # BUFFER
        # FIX: use deque(maxlen=300) instead of a plain list so that
        # popping the oldest frame is O(1) not O(n).
        # ======================
        self.frames: collections.deque = collections.deque(maxlen=300)
        self.lock = threading.Lock()

        # ======================
        # STATE
        # ======================
        self.recording         = False
        self.current_email     = None
        self.current_severity  = 0

        self.video_sent        = False
        self.start_time        = None
        self.last_danger_time  = None

        # FIX: protect last_video_time with the main lock to prevent a
        # race where two threads both pass the anti-spam check at the
        # same moment.
        self.last_video_time   = 0

        # ======================
        # ESP32
        # FIX: EventManager owns the single ESP32 instance.
        # main.py's update_esp32() delegates here so there is only ever
        # one serial connection to the device.
        # ======================
        self.esp32             = ESP32Controller()
        self.last_sent_severity = -1

        # Alarm mode flag
        self.alarm_active = False

    # =========================================================
    # ESP32 — KEEPALIVE  (called every camera tick from main.py)
    # =========================================================
    def keepalive_esp32(self, severity: int):
        """
        Feed the ESP32 safety timeout on every main-loop tick.

        send_alert() already rate-limits to 200 ms, so calling this at
        camera frame-rate (30+ fps) is safe. It intentionally does NOT
        deduplicate on severity so the ESP32 keeps receiving heartbeats
        and never silences itself mid-fall via its 10 s safety timeout.
        """
        try:
            severity = max(0, min(int(severity), 3))
        except Exception:
            severity = 0
        try:
            self.esp32.send_alert(severity)
        except Exception as e:
            print("[ESP32 ERROR]", e)

    # =========================================================
    # ESP32 — ONE-SHOT ALERT  (called internally for level changes)
    # =========================================================
    def _send_esp32(self, severity: int):
        """Send only when the severity level actually changes."""
        try:
            severity = max(0, min(int(severity), 3))
        except Exception:
            severity = 0

        if severity == self.last_sent_severity:
            return
        self.last_sent_severity = severity
        self.keepalive_esp32(severity)

    # =========================================================
    # ADD FRAME
    # =========================================================
    def add_frame(self, frame):
        # FIX: deque(maxlen=300) handles eviction automatically;
        # no explicit pop() needed.
        with self.lock:
            small = cv2.resize(frame, (640, 360))
            self.frames.append(small)

    # =========================================================
    # START RECORDING
    # =========================================================
    def start_recording(self, severity: int, email=None):

        try:
            severity = int(severity)
        except Exception:
            severity = 0

        current_time = time.time()

        if email is not None:
            self.current_email = email

        # ======================
        # FIRST DETECTION ONLY
        # ======================
        if not self.recording:

            print("[REC] START RECORDING")

            self.recording        = True
            self.start_time       = current_time
            self.video_sent       = False
            self.current_severity = severity

            # FIX: check severity ONCE here using elif so both branches
            # are reachable regardless of the severity value, and we
            # don't enter a second if-chain after setting recording=True.
            if severity >= 2:
                # Telegram alert (async)
                threading.Thread(
                    target=send_alert,
                    args=(severity,),
                    daemon=True,
                ).start()

                self.alarm_active = True
                self._send_esp32(severity)

            elif severity == 1:
                threading.Thread(
                    target=send_message,
                    args=("⚠️ Minor fall detected",),
                    daemon=True,
                ).start()

        # Always update timing and severity ceiling.
        self.last_danger_time = current_time
        self.current_severity = max(self.current_severity, severity)

        # NOTE: ESP32 keepalive is handled by main.py calling
        # keepalive_esp32() on every camera tick, so no extra send needed here.

        # ======================
        # AUTO VIDEO (CRITICAL)
        # ======================
        if severity >= 3 and not self.video_sent:

            lying_time = current_time - (self.start_time or current_time)

            if lying_time > 15:
                print("[CRITICAL] AUTO SEND VIDEO")
                self.video_sent = True

                # FIX: capture email NOW before spawning the thread so
                # that current_email can't be mutated mid-flight.
                email_snapshot = self.current_email

                threading.Thread(
                    target=self._send_emergency_video,
                    args=(email_snapshot,),
                    daemon=True,
                ).start()

    # =========================================================
    # EMERGENCY VIDEO  (internal — called from thread)
    # =========================================================
    def _send_emergency_video(self, email_snapshot: str):
        """
        Send the buffered frames as an emergency video clip.

        FIX: last_video_time check is now done inside the lock so that
        concurrent calls cannot both pass the anti-spam guard.
        email_snapshot is passed as a parameter to avoid relying on
        self.current_email which may have changed by the time this runs.
        """
        with self.lock:
            now = time.time()
            if now - self.last_video_time < 60:
                print("[ANTI SPAM] Skip video")
                return
            self.last_video_time = now
            frames_copy = list(self.frames)

        final_email = email_snapshot or "unknown@gmail.com"

        video_path = save_video(frames_copy, final_email, self.current_severity)

        if video_path:
            send_message("🚨 PATIENT NOT RECOVERING")
            send_video(video_path, "🚨 Emergency ICU Video")
            print("[TELEGRAM] Emergency video sent")

    # =========================================================
    # STOP + SAVE
    # =========================================================
    def stop_and_save(self):

        # FIX: clear the buffer immediately after copying so that new
        # frames added during the (potentially long) save operation are
        # not included in this clip and the buffer doesn't grow unbounded.
        with self.lock:
            frames_copy = list(self.frames)
            self.frames.clear()

        final_email = self.current_email

        if final_email is None:
            print("[SAVE ERROR] No email — skipping save")
            self._reset_state()
            return

        video_path = save_video(frames_copy, final_email, self.current_severity)

        if video_path:

            save_event("Fall Detection", self.current_severity, video_path)

            if not self.video_sent:
                self.video_sent = True

                threading.Thread(
                    target=send_video,
                    args=(video_path, "📹 Recovery Video"),
                    daemon=True,
                ).start()

        print("[REC] VIDEO SAVED")

        # Stop ESP32 alarm and reset all state.
        self.alarm_active = False
        self.esp32.send_stop()

        self._reset_state()

    # =========================================================
    # RESET STATE  (internal helper)
    # =========================================================
    def _reset_state(self):
        self.recording          = False
        self.current_severity   = 0
        self.start_time         = None
        self.last_danger_time   = None
        self.video_sent         = False
        self.current_email      = None
        self.last_sent_severity = -1