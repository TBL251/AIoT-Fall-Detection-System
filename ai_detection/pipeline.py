import cv2

from .pose_detection import (
    PoseDetector
)

from .fall_detection import (
    FallDetector
)

from .emergency_detection import (
    EmergencyDetector
)


class AIPipeline:

    def __init__(self):

        self.pose_detector = (
            PoseDetector()
        )

        self.fall_detector = (
            FallDetector()
        )

        self.emergency_detector = (
            EmergencyDetector()
        )

    def process(self, frame):

        # =========================
        # SMALL FRAME
        # =========================

        small = cv2.resize(
            frame,
            (640, 360)
        )

        # =========================
        # POSE
        # =========================

        small, landmarks = (
            self.pose_detector.detect(
                small
            )
        )

        # =========================
        # FALL DETECTION
        # =========================

        fall_flag, severity = (
            self.fall_detector.detect(
                landmarks
            )
        )

        # =========================
        # EMERGENCY
        # =========================

        emergency_level = (
            self.emergency_detector.classify(
                fall_flag,
                severity
            )
        )

        return (
            small,
            fall_flag,
            severity,
            emergency_level
        )