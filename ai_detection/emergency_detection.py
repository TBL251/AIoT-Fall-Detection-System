class EmergencyDetector:

    def classify(self, fall_flag, severity):

        if not fall_flag:
            return 0

        if severity >= 3:
            return 3   # critical emergency
        elif severity == 2:
            return 2   # dangerous
        elif severity == 1:
            return 1   # minor fall

        return 0