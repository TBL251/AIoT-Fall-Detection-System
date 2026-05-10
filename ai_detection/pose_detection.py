import mediapipe as mp
import cv2

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils


class PoseDetector:

    def __init__(self):

        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def detect(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        landmarks = None

        if results.pose_landmarks:

            mp_draw.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS
            )

            landmarks = results.pose_landmarks.landmark

        return frame, landmarks