import cv2
import time
import threading
import os

from services.local_storage import save_video
from services.firebase_service import save_event
from services.telegram_service import send_image, send_video, send_alert
from services.esp32_service import ESP32Controller


class EventManager:

    def __init__(self):
        self.frames = []
        self.recording = False
        self.esp32 = ESP32Controller()

    # =====================
    # RECORD FRAME BUFFER
    # =====================
    def add_frame(self, frame):

        if not self.recording:
            self.recording = True
            self.frames = []

        self.frames.append(frame)

    # =====================
    # SAVE SNAPSHOT IMAGE
    # =====================
    def save_snapshot(self, frame):

        os.makedirs("temp", exist_ok=True)

        path = f"temp/fall_{int(time.time())}.jpg"
        cv2.imwrite(path, frame)

        return path

    # =====================
    # HANDLE EVENT (MAIN)
    # =====================
    def handle_event(self, frame, severity):

        # 1. snapshot
        image_path = self.save_snapshot(frame)

        # 2. send image immediately
        send_image(image_path, f"⚠️ Fall detected - Level {severity}")

        # 3. start recording
        self.add_frame(frame)

        # 4. async process
        def worker():

            time.sleep(3)

            video_path = save_video(self.frames)

            # firebase
            save_event("Fall Detection", severity, video_path)

            # telegram video
            if video_path:
                send_video(video_path)

            # alert text
            send_alert(severity)

            # esp32
            self.esp32.send_alert(severity)

            print("[EVENT] Completed")

        threading.Thread(target=worker).start()