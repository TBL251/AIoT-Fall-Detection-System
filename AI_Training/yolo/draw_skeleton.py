"""
yolo/draw_skeleton.py
──────────────────────
OpenCV skeleton drawing utilities for COCO 17-keypoint format.
"""

import cv2
import numpy as np

# ─── COCO 17-keypoint skeleton edges ─────────────────────────────────────────
SKELETON: list[tuple[int, int]] = [
    (0, 1), (0, 2),               # nose → eyes
    (1, 3), (2, 4),               # eyes → ears
    (5, 6),                       # shoulder span
    (5, 7), (7, 9),               # left  arm
    (6, 8), (8, 10),              # right arm
    (5, 11), (6, 12),             # torso sides
    (11, 12),                     # hip span
    (11, 13), (13, 15),           # left  leg
    (12, 14), (14, 16),           # right leg
]

# ─── Colours (BGR) ───────────────────────────────────────────────────────────
_COLOR_KP_NORMAL  = (0,  255, 100)
_COLOR_BONE_NORMAL= (0,  200, 255)
_COLOR_FALL       = (0,  0,   255)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def draw_points(
    frame: np.ndarray,
    points: np.ndarray,
    color: tuple[int, int, int] = _COLOR_KP_NORMAL,
    radius: int = 4,
) -> None:
    """
    Draw filled circles at each valid keypoint.

    Parameters
    ----------
    frame  : BGR image (modified in-place)
    points : (17, 2) float32  — zero coords are skipped
    color  : BGR tuple
    radius : circle radius in pixels
    """
    if points is None:
        return

    for x, y in points:
        if x > 0 and y > 0:
            cv2.circle(frame, (int(x), int(y)), radius, color, -1)


def draw_skeleton(
    frame: np.ndarray,
    points: np.ndarray,
    is_fall: bool = False,
    line_thickness: int = 2,
) -> None:
    """
    Draw the full body skeleton on *frame* in-place.

    Parameters
    ----------
    frame          : BGR image (modified in-place)
    points         : (17, 2) float32 keypoints
    is_fall        : if True, draw in red (FALL colour)
    line_thickness : bone line width
    """
    if points is None or len(points) == 0:
        return

    bone_color = _COLOR_FALL      if is_fall else _COLOR_BONE_NORMAL
    pt_color   = _COLOR_FALL      if is_fall else _COLOR_KP_NORMAL

    for i, j in SKELETON:
        if i >= len(points) or j >= len(points):
            continue

        x1, y1 = points[i]
        x2, y2 = points[j]

        if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:
            cv2.line(
                frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                bone_color,
                line_thickness,
                cv2.LINE_AA,
            )

    draw_points(frame, points, pt_color)