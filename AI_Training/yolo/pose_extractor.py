"""
yolo/pose_extractor.py
───────────────────────
Thin wrapper around YOLOv8s-Pose for single-person keypoint extraction.

Returns
───────
extract_keypoints     →  (34,)  flat float32 array  [x1,y1,...,x17,y17]
extract_keypoints_xy  →  (34,)  identical but documented as (17,2) logically
"""

from __future__ import annotations

import numpy as np
from ultralytics import YOLO

from AI_Training.configs.config import YOLO_MODEL, YOLO_IMGSZ, YOLO_CONF

# ─── Singleton model ─────────────────────────────────────────────────────────

_model: YOLO | None = None


def get_model() -> YOLO:
    """Return the shared YOLO model, loading it on first call."""
    global _model
    if _model is None:
        _model = YOLO(YOLO_MODEL)
    return _model


# ─── Constants ───────────────────────────────────────────────────────────────

NUM_KEYPOINTS = 17
RAW_DIM       = NUM_KEYPOINTS * 2   # 34


# ─── Internal helper ─────────────────────────────────────────────────────────

def _run_yolo(frame: np.ndarray) -> np.ndarray | None:
    """
    Run YOLOv8 on *frame* and return the first-person keypoints
    as a (34,) float32 array, or None if detection fails.
    """
    model   = get_model()
    results = model(frame, verbose=False, imgsz=YOLO_IMGSZ, conf=YOLO_CONF)

    if not results:
        return None

    result = results[0]

    if result.keypoints is None:
        return None

    try:
        kpts = result.keypoints.xy     # (num_persons, 17, 2)

        if kpts is None or len(kpts) == 0:
            return None

        kp = kpts[0].cpu().numpy()     # first person → (17, 2)

        if kp.shape != (NUM_KEYPOINTS, 2):
            return None

        flat = kp.flatten()            # (34,)

        if flat.shape[0] != RAW_DIM:
            return None

        return flat.astype(np.float32)

    except Exception:
        return None


# ─── Public API ──────────────────────────────────────────────────────────────

def extract_keypoints(frame: np.ndarray) -> np.ndarray | None:
    """
    Extract a (34,) flat keypoint vector from a BGR frame.

    Parameters
    ----------
    frame : np.ndarray  (H, W, 3)  BGR

    Returns
    -------
    np.ndarray (34,) float32  or  None on detection failure
    """
    return _run_yolo(frame)


def extract_keypoints_xy(frame: np.ndarray) -> np.ndarray | None:
    """
    Same as :func:`extract_keypoints` but documented as (17, 2) logically.
    Returns (34,) float32 for compatibility with reshape(17,2).
    """
    return _run_yolo(frame)