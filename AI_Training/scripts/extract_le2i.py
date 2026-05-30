"""
scripts/extract_le2i.py
────────────────────────
Extract YOLOv8 keypoints from the LE2I Fall Detection Dataset.

Expected dataset structure:
  dataset/raw/le2i/
    <SceneName>/
      Videos/
        video1.avi  (or .mp4 / .mov)
      Annotation_files/   (or Annotations_files/)
        video1.txt         ← two lines: start_frame  end_frame (1-indexed)

Outputs:
  dataset/pose/le2i/fall/<scene>_<video>.npy    (N_fall, 34)
  dataset/pose/le2i/normal/<scene>_<video>.npy  (N_normal, 34)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from yolo.pose_extractor import extract_keypoints
from configs.config import LE2I_RAW_PATH, POSE_DIR
from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger("extract_le2i")

VIDEOS_DIR_NAME  = "Videos"
ANN_DIR_VARIANTS = ["Annotation_files", "Annotations_files"]
MIN_FRAMES       = 5     # discard arrays shorter than this


# ─── Utilities ───────────────────────────────────────────────────────────────

def _safe_name(s: str) -> str:
    return s.replace(" ", "_").replace("(", "").replace(")", "")


def _find_ann_dir(scene_path: str) -> str | None:
    for name in ANN_DIR_VARIANTS:
        candidate = os.path.join(scene_path, name)
        if os.path.isdir(candidate):
            return candidate
    return None


def _resolve_ann_path(ann_dir: str | None, stem: str) -> str | None:
    if not ann_dir:
        return None
    path = os.path.join(ann_dir, f"{stem}.txt")
    return path if os.path.exists(path) else None


def _ensure_output_dirs() -> None:
    ensure_dir(os.path.join(POSE_DIR, "le2i", "fall"))
    ensure_dir(os.path.join(POSE_DIR, "le2i", "normal"))


# ─── Audio strip ─────────────────────────────────────────────────────────────

def _strip_audio(video_path: str) -> str:
    """
    Return a copy of *video_path* with audio removed (via ffmpeg).
    Falls back to original path if ffmpeg is unavailable.
    """
    if shutil.which("ffmpeg") is None:
        return video_path

    tmp = os.path.join(tempfile.gettempdir(), f"noaudio_{os.path.basename(video_path)}")

    if os.path.exists(tmp):
        return tmp

    cmd = [
        "ffmpeg", "-y", "-loglevel", "quiet",
        "-i", video_path, "-an", "-c:v", "copy", tmp,
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=True)
        return tmp
    except Exception:
        return video_path


# ─── Annotation parsing ──────────────────────────────────────────────────────

def _parse_annotation(txt_path: str | None) -> set[int]:
    """
    Parse a LE2I annotation file into a set of 1-indexed fall frame numbers.

    File format (two non-empty lines):
        <start_frame>
        <end_frame>
    """
    if not txt_path or not os.path.exists(txt_path):
        return set()

    try:
        with open(txt_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]

        if len(lines) < 2:
            return set()

        start, end = int(lines[0]), int(lines[1])
        return set(range(start, end + 1))

    except Exception:
        return set()


# ─── Video processing ────────────────────────────────────────────────────────

def _process_video(
    video_path: str,
    fall_frames: set[int],
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """
    Iterate frames in *video_path*, extract keypoints, and split by label.

    Returns
    -------
    (fall_kps, normal_kps)  each (N, 34) float32 or None if < MIN_FRAMES
    """
    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        logger.warning(f"Cannot open video: {video_path}")
        return None, None

    fall_buf:   list[np.ndarray] = []
    normal_buf: list[np.ndarray] = []
    frame_idx = 1            # LE2I annotations are 1-indexed

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        kp = extract_keypoints(frame)

        if kp is not None:
            kp = np.asarray(kp, dtype=np.float32)

            try:
                kp_2d = kp.reshape(17, 2)
            except ValueError:
                frame_idx += 1
                continue

            if not np.isnan(kp_2d).any():
                valid_joints = int(np.sum(np.linalg.norm(kp_2d, axis=1) > 0))
                if valid_joints >= 8:
                    flat = kp_2d.flatten()
                    if frame_idx in fall_frames:
                        fall_buf.append(flat)
                    else:
                        normal_buf.append(flat)

        frame_idx += 1

    cap.release()

    def _to_arr(buf: list[np.ndarray]) -> np.ndarray | None:
        return np.array(buf, dtype=np.float32) if len(buf) >= MIN_FRAMES else None

    return _to_arr(fall_buf), _to_arr(normal_buf)


# ─── Main ─────────────────────────────────────────────────────────────────────

def run() -> None:
    _ensure_output_dirs()

    if not os.path.isdir(LE2I_RAW_PATH):
        logger.error(f"LE2I dataset not found: {LE2I_RAW_PATH}")
        return

    scenes = sorted(os.listdir(LE2I_RAW_PATH))
    logger.info(f"Found {len(scenes)} scene(s) in {LE2I_RAW_PATH}")

    for scene in scenes:
        scene_path  = os.path.join(LE2I_RAW_PATH, scene)
        videos_path = os.path.join(scene_path, VIDEOS_DIR_NAME)
        ann_dir     = _find_ann_dir(scene_path)

        if not os.path.isdir(videos_path):
            continue

        video_files = sorted(
            f for f in os.listdir(videos_path)
            if f.lower().endswith((".mp4", ".avi", ".mov"))
        )

        for vfile in video_files:
            stem      = os.path.splitext(vfile)[0]
            save_stem = f"{_safe_name(scene)}_{_safe_name(stem)}"

            fall_out   = os.path.join(POSE_DIR, "le2i", "fall",   f"{save_stem}.npy")
            normal_out = os.path.join(POSE_DIR, "le2i", "normal", f"{save_stem}.npy")

            if os.path.exists(fall_out) and os.path.exists(normal_out):
                continue

            vpath       = _strip_audio(os.path.join(videos_path, vfile))
            ann_path    = _resolve_ann_path(ann_dir, stem)
            fall_frames = _parse_annotation(ann_path)

            fall_kps, normal_kps = _process_video(vpath, fall_frames)

            if fall_kps is not None:
                np.save(fall_out, fall_kps)
            if normal_kps is not None:
                np.save(normal_out, normal_kps)

            logger.info(
                f"  {save_stem}: "
                f"fall={fall_kps.shape if fall_kps is not None else 'None'}  "
                f"normal={normal_kps.shape if normal_kps is not None else 'None'}"
            )

    logger.info("LE2I extraction complete.")


if __name__ == "__main__":
    run()