import cv2
import time

from ai_detection.pipeline import AIPipeline
from services.event_manager import EventManager


pipeline = AIPipeline()
event_manager = EventManager()

cap = cv2.VideoCapture(0)

# =========================
# ICU VARIABLES
# =========================

state = "NORMAL"
fall_time = None
lie_time = None
risk_score = 0
cooldown = 0

print("🏥 ICU MONITORING SYSTEM STARTED")


while True:

    ret, frame = cap.read()
    if not ret:
        break

    current_time = time.time()

    frame, fall_flag, severity = pipeline.process(frame)

    # =========================
    # RISK SCORE SYSTEM (0–100)
    # =========================

    risk_score = severity * 25

    # =========================
    # STATE TRANSITION
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
    # ICU CRITICAL CHECK
    # =========================

    if state == "LYING_MONITORING":

        lie_duration = current_time - lie_time

        # ICU EMERGENCY CONDITION
        if lie_duration > 5 and risk_score >= 50 and current_time > cooldown:

            print("🚨 ICU ALERT: CRITICAL PATIENT CONDITION")

            event_manager.handle_event(frame, 4)

            cooldown = current_time + 10
            state = "NORMAL"

    # =========================
    # RECOVERY CHECK
    # =========================

    if not fall_flag and state != "NORMAL":

        # nếu đứng lại → reset nhẹ
        if risk_score < 30:
            state = "NORMAL"
            fall_time = None
            lie_time = None

    # =========================
    # ICU DASHBOARD INFO
    # =========================

    cv2.putText(frame,
                f"ICU STATE: {state}",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2)

    cv2.putText(frame,
                f"RISK SCORE: {risk_score}",
                (30, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2)

    cv2.putText(frame,
                f"LEVEL: {severity}",
                (30, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2)

    cv2.imshow("🏥 ICU MONITORING SYSTEM", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break


cap.release()
cv2.destroyAllWindows()

print("System stopped")