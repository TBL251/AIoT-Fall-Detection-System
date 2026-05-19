import cv2
import time
import threading

from services.local_storage import save_video

from services.firebase_service import (
    save_event
)

from services.telegram_service import (
    send_video,
    send_alert,
    send_message
)

from services.esp32_service import (
    ESP32Controller
)


class EventManager:

    def __init__(self):

        self.frames = []

        self.lock = threading.Lock()

        self.recording = False

        self.current_email = None

        self.current_severity = 0

        self.video_sent = False

        self.start_time = None

        self.last_danger_time = None

        self.last_video_time = 0

        self.esp32 = ESP32Controller()

    # ====================================
    # PROPERTY
    # ====================================

    @property
    def is_recording(self):

        return self.recording

    # ====================================
    # ADD FRAME
    # ====================================

    def add_frame(self, frame):

        with self.lock:

            small = cv2.resize(
                frame,
                (640, 360)
            )

            self.frames.append(
                small
            )

            # keep latest frames
            if len(self.frames) > 300:

                self.frames.pop(0)

    # ====================================
    # START RECORDING
    # ====================================

    def start_recording(
        self,
        severity,
        email=None
    ):

        current_time = time.time()

        if email is not None:

            self.current_email = email

        # FIRST DETECTION
        if not self.recording:

            print("[REC] START RECORDING")

            self.recording = True

            self.start_time = current_time

            self.video_sent = False

            self.current_severity = severity

            # ALERTS
            if severity >= 2:

                threading.Thread(

                    target=send_alert,

                    args=(severity,),

                    daemon=True

                ).start()

                self.esp32.send_alert(
                    severity
                )

            elif severity == 1:

                threading.Thread(

                    target=send_message,

                    args=(
                        "⚠️ Minor fall detected",
                    ),

                    daemon=True

                ).start()

        self.last_danger_time = current_time

        self.current_severity = max(
            self.current_severity,
            severity
        )

        # ====================================
        # AUTO SEND VIDEO
        # ====================================

        if (
            severity >= 3
            and not self.video_sent
        ):

            lying_time = (
                current_time - self.start_time
            )

            if lying_time > 15:

                print(
                    "[CRITICAL] AUTO SEND VIDEO"
                )

                # LOCK BEFORE SEND
                self.video_sent = True

                threading.Thread(
                    target=self.send_emergency_video,
                    daemon=True
                ).start()

    # ====================================
    # SEND EMERGENCY VIDEO
    # ====================================

    def send_emergency_video(self):

        now = time.time()

        # ANTI SPAM
        if now - self.last_video_time < 60:

            print("[ANTI SPAM] Skip video")

            return

        self.last_video_time = now

        with self.lock:

            frames_copy = (
                self.frames.copy()
            )

        final_email = (
            self.current_email
            or "unknown@gmail.com"
        )

        video_path = save_video(
            frames_copy,
            final_email,
            self.current_severity
        )

        if video_path:

            send_message(
                "🚨 PATIENT NOT RECOVERING"
            )

            send_video(
                video_path,
                "🚨 Emergency ICU Video"
            )

            print(
                "[TELEGRAM] Emergency video sent"
            )

    # ====================================
    # STOP + SAVE
    # ====================================

    def stop_and_save(self):

        with self.lock:

            frames_copy = (
                self.frames.copy()
            )

        final_email = (
            self.current_email
        )

        if final_email is None:

            print(
                "[SAVE ERROR] No email"
            )

            return

        video_path = save_video(
            frames_copy,
            final_email,
            self.current_severity
        )

        if video_path:

            save_event(
                "Fall Detection",
                self.current_severity,
                video_path
            )

            if not self.video_sent:

                self.video_sent = True

                threading.Thread(

                    target=send_video,

                    args=(
                        video_path,
                        "📹 Recovery Video"
                    ),

                    daemon=True

                ).start()

        print("[REC] VIDEO SAVED")

        # RESET ESP32
        self.esp32.send_alert(0)

        # RESET
        self.frames.clear()

        self.recording = False

        self.current_severity = 0

        self.start_time = None

        self.last_danger_time = None

        self.video_sent = False

        self.current_email = None