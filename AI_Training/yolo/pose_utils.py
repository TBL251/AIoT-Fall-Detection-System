"""
yolo/pose_utils.py
───────────────────
Lightweight keypoint validation and shape utilities.
"""

import numpy as np


def flatten_keypoints(points: np.ndarray) -> np.ndarray | None:
    """
    Convert (17, 2) → (34,).

    Returns None if *points* is None.
    """
    if points is None:
        return None
    return points.reshape(-1).astype(np.float32)


def keypoints_valid(
    keypoints: np.ndarray | None,
    min_nonzero: int = 10,
) -> bool:
    """
    Return True if *keypoints* has at least *min_nonzero* non-zero joints.

    Parameters
    ----------
    keypoints   : (34,) flat array or None
    min_nonzero : minimum number of visible joints required

    Notes
    -----
    A joint is considered visible when at least one of its x, y
    coordinates is non-zero.
    """
    if keypoints is None:
        return False

    if keypoints.size < 34:
        return False

    pts     = keypoints.reshape(-1, 2)
    nonzero = int(np.sum(np.any(pts != 0, axis=1)))

    return nonzero >= min_nonzero