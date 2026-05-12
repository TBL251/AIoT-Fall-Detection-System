import time
import threading

from services.local_storage import save_video
from services.firebase_service import save_event

from services.telegram_service import (
    send_video,
    send_alert
)

from services.esp32_service import ESP32Controller


class EventManager:

    def __init__(self):

        self.frames = []

        self.recording = False

        self.max_frames = 120

        self.lock = threading.Lock()

        self.esp32 = ESP32Controller()

    # =====================
    # FRAME BUFFER
    # =====================

    def add_frame(self, frame):

        with self.lock:

            frame_copy = frame.copy()

            self.frames.append(frame_copy)

            # limit RAM
            if len(self.frames) > self.max_frames:

                self.frames.pop(0)

    # =====================
    # MAIN EVENT
    # =====================

    def handle_event(
        self,
        frame,
        severity,
        email
    ):

        # avoid duplicate trigger
        if self.recording:
            return

        self.recording = True

        print(
            f"[EVENT] FALL DETECTED LEVEL {severity}"
        )

        # =====================
        # BACKGROUND WORKER
        # =====================

        def worker():

            try:

                # keep recording
                time.sleep(3)

                with self.lock:

                    frames_copy = self.frames.copy()

                # =====================
                # SAVE VIDEO
                # =====================

                video_path = save_video(
                    frames=frames_copy,
                    email=email,
                    severity=severity
                )

                # =====================
                # FIREBASE
                # =====================

                save_event(
                    "Fall Detection",
                    severity,
                    video_path
                )

                # =====================
                # TELEGRAM VIDEO
                # =====================

                if video_path:

                    send_video(
                        video_path,
                        f"⚠️ Fall Level {severity}"
                    )

                # =====================
                # TEXT ALERT
                # =====================

                send_alert(severity)

                # =====================
                # ESP32
                # =====================

                self.esp32.send_alert(
                    severity
                )

                print("[EVENT COMPLETED]")

            except Exception as e:

                print("[EVENT ERROR]", e)

            finally:

                self.recording = False

                with self.lock:

                    self.frames.clear()

        # =====================
        # START THREAD
        # =====================

        threading.Thread(
            target=worker,
            daemon=True
        ).start()