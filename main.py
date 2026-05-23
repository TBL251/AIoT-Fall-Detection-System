import cv2
import time
import json
import os
import shared_camera

from ai_detection.pipeline import AIPipeline

from services.event_manager import (
    EventManager
)

from services.camera_thread import (
    CameraStream
)

# =========================
# PATH
# =========================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

USERS_FILE = os.path.join(
    BASE_DIR,
    "dashboard",
    "users.json"
)

# =========================
# GET CURRENT USER
# =========================

def get_current_logged_user():

    if not os.path.exists(
        USERS_FILE
    ):

        return None

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            users = json.load(f)

        for enc_email, data in users.items():

            if data.get(
                "is_logged_in"
            ) is True:

                from dashboard.security import (
                    decrypt_text
                )

                try:

                    return decrypt_text(
                        enc_email
                    )

                except Exception as e:

                    print(
                        "[DECRYPT ERROR]",
                        e
                    )

    except Exception as e:

        print(
            "[USER ERROR]",
            e
        )

    return None

# =========================
# INIT
# =========================

pipeline = AIPipeline()

event_manager = EventManager()

# =========================
# CAMERA
# =========================

try:

    camera = CameraStream(1)

except Exception as e:

    print(
        "[CAMERA INIT ERROR]",
        e
    )

    exit(1)

# =========================
# STATES
# =========================

state = "NORMAL"

risk_score = 0

recovery_start = None

RECOVERY_SECONDS = 5

print(
    "🏥 ICU MONITORING SYSTEM STARTED"
)

# =========================
# MAIN LOOP
# =========================

try:

    while True:

        # =========================
        # GET USER
        # =========================

        current_user = (
            get_current_logged_user()
        )

        # =========================
        # READ CAMERA
        # =========================

        ret, frame = camera.read()

        if not ret or frame is None:

            print(
                "[CAMERA] Failed to read frame"
            )

            time.sleep(1)

            continue

        # =========================
        # SAVE BUFFER
        # =========================

        event_manager.add_frame(
            frame
        )

        # =========================
        # AI PROCESS
        # =========================

        try:

            (
                frame,
                fall_flag,
                severity,
                emergency_level
            ) = pipeline.process(
                frame
            )
            shared_camera.latest_frame = frame.copy()

        except Exception as e:

            print(
                "[AI ERROR]",
                e
            )

            continue

        # =========================
        # RISK SCORE
        # =========================

        if fall_flag:

            risk_score = min(
                100,
                risk_score + 5
            )

        else:

            risk_score = max(
                0,
                risk_score - 3
            )

        # =========================
        # FALL DETECTED
        # =========================

        if fall_flag:

            recovery_start = None

            state = "FALLING"

            if not event_manager.recording:

                print(
                    "🚨 FALL DETECTED"
                )

                if current_user:

                    print(
                        f"[USER] {current_user}"
                    )

                else:

                    print(
                        "[WARNING] No user logged in"
                    )

            # ALWAYS UPDATE RECORDING
            event_manager.start_recording(

                severity=emergency_level,

                email=current_user
            )

        # =========================
        # RECOVERY
        # =========================

        else:

            if event_manager.recording:

                if recovery_start is None:

                    recovery_start = time.time()

                recovery_duration = (
                    time.time()
                    - recovery_start
                )

                if (
                    recovery_duration
                    >= RECOVERY_SECONDS
                ):

                    print(
                        "✅ RECOVERY STABLE"
                    )

                    state = "NORMAL"

                    try:

                        event_manager.stop_and_save()

                    except Exception as e:

                        print(
                            "[SAVE ERROR]",
                            e
                        )

                    recovery_start = None

        # =========================
        # DISPLAY INFO
        # =========================

        cv2.putText(

            frame,

            f"State: {state}",

            (20, 40),

            cv2.FONT_HERSHEY_SIMPLEX,

            1,

            (
                0,
                255,
                0
            ) if state == "NORMAL"
            else (
                0,
                0,
                255
            ),

            2
        )

        cv2.putText(

            frame,

            f"Risk Score: {risk_score}",

            (20, 80),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.8,

            (
                255,
                255,
                0
            ),

            2
        )


finally:

    print(
        "[SYSTEM] Releasing resources..."
    )

    try:

        camera.release()

    except Exception as e:

        print(
            "[CAMERA RELEASE ERROR]",
            e
        )

    cv2.destroyAllWindows()

    print(
        "🏥 System stopped"
    )