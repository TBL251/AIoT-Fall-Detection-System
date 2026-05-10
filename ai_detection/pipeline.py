import random
import time

class AIPipeline:

    def __init__(self):
        self.last_state = "NORMAL"

    def process(self, frame):

        # =====================
        # MOCK AI LOGIC
        # =====================

        # giả lập xác suất té ngã
        fall_prob = random.random()

        if fall_prob < 0.05:
            fall_flag = True
            severity = random.randint(2, 4)
        elif fall_prob < 0.15:
            fall_flag = True
            severity = 1
        else:
            fall_flag = False
            severity = 0

        # return frame + AI result
        return frame, fall_flag, severity