import cv2
import time
import json
import os

from ai_detection.pipeline import AIPipeline
from services.event_manager import EventManager

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

    if not os.path.exists(USERS_FILE):
        return None

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            users = json.load(f)

        for enc_email, data in users.items():

            if data.get("is_logged_in") is True:

                # lấy email thật
                from dashboard.security import decrypt_text

                try:

                    real_email = decrypt_text(
                        enc_email
                    )

                    return real_email

                except:
                    pass

    except Exception as e:

        print("[USER READ ERROR]", e)

    return None

# =========================
# INIT SYSTEM
# =========================

pipeline = AIPipeline()

event_manager = EventManager()

cap = cv2.VideoCapture(0)

# camera quality
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():

    print("ERROR: Cannot open camera")

    exit(1)

# =========================
# ICU VARIABLES
# =========================

state = "NORMAL"

fall_time = None

lie_time = None

risk_score = 0

cooldown = 0

last_frame_time = 0

FPS_LIMIT = 20

print("🏥 ICU MONITORING SYSTEM STARTED")

# =========================
# MAIN LOOP
# =========================

try:

    while True:

        current_time = time.time()

        # =========================
        # FPS LIMITER
        # =========================

        if current_time - last_frame_time < 1 / FPS_LIMIT:
            continue

        last_frame_time = current_time

        # =========================
        # CURRENT USER
        # =========================

        current_user = get_current_logged_user()

        # =========================
        # READ CAMERA
        # =========================

        ret, frame = cap.read()

        if not ret:
            break

        # =========================
        # SAVE BUFFER
        # =========================

        event_manager.add_frame(frame)

        # =========================
        # AI PIPELINE
        # =========================

        frame, fall_flag, severity, emergency_level = (
            pipeline.process(frame)
        )

        # =========================
        # RISK SCORE
        # =========================

        if fall_flag:

            risk_score = max(
                risk_score,
                severity * 25
            )

        else:

            risk_score = max(
                0,
                risk_score - 5
            )

        # =========================
        # STATE MACHINE
        # =========================

        if fall_flag:

            if state == "NORMAL":

                state = "UNBALANCED"

                fall_time = current_time

            elif state == "UNBALANCED":

                if current_time - fall_time > 1.5:

                    state = "FALLING"

            elif state == "FALLING":

                if current_time - fall_time > 3:

                    state = "LYING_MONITORING"

                    lie_time = current_time

        # =========================
        # ICU ALERT
        # =========================

        if state == "LYING_MONITORING":

            lie_duration = (
                current_time - lie_time
            )

            if (
                lie_duration > 5
                and risk_score >= 50
                and current_time > cooldown
            ):

                print("🚨 ICU ALERT")

                if current_user is not None:

                    print(
                        f"[CURRENT USER] {current_user}"
                    )

                    event_manager.handle_event(
                        frame=frame,
                        severity=emergency_level,
                        email=current_user
                    )

                else:

                    print(
                        "No user logged in"
                    )

                cooldown = current_time + 10

                state = "NORMAL"

                fall_time = None

                lie_time = None

        # =========================
        # RECOVERY
        # =========================

        if not fall_flag:

            if risk_score < 30:

                state = "NORMAL"

                fall_time = None

                lie_time = None

        # =========================
        # UI
        # =========================

        cv2.putText(
            frame,
            f"STATE: {state}",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"RISK SCORE: {risk_score}",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        cv2.putText(
            frame,
            f"LEVEL: {severity}",
            (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0),
            2
        )

        cv2.putText(
            frame,
            f"USER: {current_user}",
            (30, 160),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        # =========================
        # SHOW WINDOW
        # =========================

        cv2.imshow(
            "🏥 ICU MONITORING SYSTEM",
            frame
        )

        # ESC
        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:

    cap.release()

    cv2.destroyAllWindows()

    print("System stopped")