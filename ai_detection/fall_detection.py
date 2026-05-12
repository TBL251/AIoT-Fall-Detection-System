from .utils import calculate_angle


class FallDetector:

    def __init__(self):
        self.prev_state = "normal"

    def detect(self, landmarks):

        if not landmarks:
            return False, 0

        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_hip = landmarks[23]
        right_hip = landmarks[24]

        # center of body (shoulder midpoint → hip midpoint)
        sx = (left_shoulder.x + right_shoulder.x) / 2
        sy = (left_shoulder.y + right_shoulder.y) / 2

        hx = (left_hip.x + right_hip.x) / 2
        hy = (left_hip.y + right_hip.y) / 2

        angle = calculate_angle(sx, sy, hx, hy)

        # fall severity thresholds based on body tilt angle
        if angle > 65:
            return True, 3   # critical
        elif angle > 45:
            return True, 2   # dangerous
        elif angle > 30:
            return True, 1   # minor

        return False, 0