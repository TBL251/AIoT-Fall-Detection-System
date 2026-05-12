from .pose_detection import PoseDetector
from .fall_detection import FallDetector
from .emergency_detection import EmergencyDetector


class AIPipeline:

    def __init__(self):
        self.pose_detector = PoseDetector()
        self.fall_detector = FallDetector()
        self.emergency_detector = EmergencyDetector()

    def process(self, frame):

        frame, landmarks = self.pose_detector.detect(frame)
        fall_flag, severity = self.fall_detector.detect(landmarks)
        emergency_level = self.emergency_detector.classify(fall_flag, severity)

        return frame, fall_flag, severity, emergency_level