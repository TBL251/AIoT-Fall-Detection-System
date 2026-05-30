import os
import cv2
import numpy as np


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def is_image(filename: str) -> bool:
    return filename.lower().endswith((".png", ".jpg", ".jpeg"))


def read_frame(path: str):
    """Read an image from disk. Returns None if unreadable."""
    frame = cv2.imread(path)
    return frame


def resize_frame(frame, width: int = 640):
    """Resize frame keeping aspect ratio."""
    h, w = frame.shape[:2]
    scale = width / w
    return cv2.resize(frame, (width, int(h * scale)))


def normalize_keypoints(keypoints: np.ndarray, frame_w: int, frame_h: int) -> np.ndarray:
    """Normalize keypoints to [0, 1] range."""
    kp = keypoints.copy().reshape(-1, 2).astype(np.float32)
    kp[:, 0] /= frame_w
    kp[:, 1] /= frame_h
    return kp.flatten()
