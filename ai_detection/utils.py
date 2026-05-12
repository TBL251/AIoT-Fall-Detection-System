import math


def calculate_angle(x1, y1, x2, y2):
    """
    Returns the angle (in degrees) of the vector from (x1, y1) to (x2, y2)
    relative to the horizontal axis, normalized to [0, 180].
    """
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    return abs(angle) % 180


def euclidean_distance(x1, y1, x2, y2):

    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5