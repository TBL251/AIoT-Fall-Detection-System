import math


def calculate_angle(x1, y1, x2, y2):

    angle = math.degrees(
        math.atan2(y2 - y1, x2 - x1)
    )

    return abs(angle)


def euclidean_distance(x1, y1, x2, y2):

    return ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
