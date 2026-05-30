"""
scripts/extract_ur.py
──────────────────────
Extract YOLOv8 keypoints from the UR Fall Detection Dataset.

Dataset structure expected:
  dataset/raw/ur/
    fall/
      seq_001/   ← folder of sequential JPG/PNG frames
        frame_001.jpg
        ...
    normal/
      seq_001/
        ...

Outputs:
  dataset/pose/ur/fall/<seq_name>.npy     shape (N, 34)
  dataset/pose/ur/normal/<seq_name>.npy   shape (N, 34)
"""

from __future__ import annotations

import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from yolo.pose_extractor import extract_keypoints
from configs.config import UR_RAW_PATH, POSE_DIR, LABELS
from utils.helpers import ensure_dir, is_image
from utils.logger import get_logger

logger = get_logger("extract_ur")

# Minimum frames with valid keypoints to keep a sequence
MIN_VALID_FRAMES = 10


# ─── Per-folder extraction ────────────────────────────────────────────────────

def process_folder(folder_path: str) -> np.ndarray | None:
    """
    Extract keypoints from all image frames in *folder_path*.

    Returns
    -------
    np.ndarray (N, 34)  or  None if fewer than MIN_VALID_FRAMES valid frames.
    """
    frames = sorted(f for f in os.listdir(folder_path) if is_image(f))

    if not frames:
        return None

    buffer: list[np.ndarray] = []

    for fname in frames:
        path = os.path.join(folder_path, fname)

        try:
            img = cv2.imread(path)
            if img is None:
                continue

            kp = extract_keypoints(img)   # (34,) or None
            if kp is None:
                continue

            kp = np.asarray(kp, dtype=np.float32)

            try:
                kp_2d = kp.reshape(17, 2)
            except ValueError:
                continue

            if np.isnan(kp_2d).any():
                continue

            valid_joints = int(np.sum(np.linalg.norm(kp_2d, axis=1) > 0))
            if valid_joints < 8:
                continue

            buffer.append(kp_2d.flatten())   # (34,)

        except Exception:
            continue

    if len(buffer) < MIN_VALID_FRAMES:
        return None

    return np.array(buffer, dtype=np.float32)   # (N, 34)


# ─── Main ─────────────────────────────────────────────────────────────────────

def run() -> None:
    logger.info("Starting UR dataset extraction …")

    for class_name in LABELS:
        class_path = os.path.join(UR_RAW_PATH, class_name)

        if not os.path.isdir(class_path):
            logger.warning(f"Class folder not found: {class_path}")
            continue

        out_dir = os.path.join(POSE_DIR, "ur", class_name)
        ensure_dir(out_dir)

        folders = sorted(
            f for f in os.listdir(class_path)
            if os.path.isdir(os.path.join(class_path, f))
        )

        logger.info(f"  [{class_name}] {len(folders)} sequence folders")

        for folder in folders:
            save_path = os.path.join(out_dir, f"{folder}.npy")

            if os.path.exists(save_path):
                continue

            kps = process_folder(os.path.join(class_path, folder))

            if kps is None:
                logger.debug(f"  Skip (too few valid frames): {folder}")
                continue

            np.save(save_path, kps)
            logger.info(f"  Saved {class_name}/{folder}.npy  shape={kps.shape}")

    logger.info("UR extraction complete.")


if __name__ == "__main__":
    run()