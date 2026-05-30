"""
lstm/dataset_builder.py
────────────────────────
Builds the (X.npy, y.npy) training dataset from .npy pose files.

Pipeline
────────
  For each source (ur, le2i, …):
    For each class (normal, fall):
      Load .npy  →  sliding-window sequences  →  feature extraction
  Stack all sequences  →  save X, y, labels.json
"""

from __future__ import annotations

import json
import os

import numpy as np

from configs.config import (
    FEATURES,
    LABELS,
    POSE_DIR,
    PROCESSED_DIR,
    SAVE_LABELS,
    SAVE_X,
    SAVE_Y,
    SEQUENCE_LENGTH,
    STRIDE,
)
from features.feature_engineering import extract_features
from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger("dataset_builder")


# ─── Sliding-window helper ───────────────────────────────────────────────────

def make_sequences(data: np.ndarray) -> list[np.ndarray]:
    """
    Convert (N, 34) raw pose array to a list of (T, 34) windows.

    Parameters
    ----------
    data : (N, 34)  — N frames of 17-keypoint poses

    Returns
    -------
    list of (SEQUENCE_LENGTH, 34) arrays
    """
    n = len(data)
    if n < SEQUENCE_LENGTH:
        return []

    return [
        data[i : i + SEQUENCE_LENGTH]
        for i in range(0, n - SEQUENCE_LENGTH + 1, STRIDE)
    ]


# ─── Feature conversion ──────────────────────────────────────────────────────

def to_features(seq_34: np.ndarray) -> np.ndarray:
    """
    (T, 34)  →  (T, FEATURES)

    Delegates to feature_engineering.extract_features which raises
    ValueError on shape mismatch, so errors surface early.
    """
    feat = extract_features(seq_34)

    if feat.shape[-1] != FEATURES:
        raise ValueError(
            f"[Feature Mismatch] Expected {FEATURES}D, got {feat.shape[-1]}D. "
            f"Check FEATURES in config.py."
        )

    return feat


# ─── Main builder ────────────────────────────────────────────────────────────

def build(sources: list[str] | None = None) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the full training dataset.

    Parameters
    ----------
    sources : list of source folder names under POSE_DIR, or None for all.

    Returns
    -------
    X : (N, T, F)  float32
    y : (N,)       int32
    """
    X_list: list[np.ndarray] = []
    y_list: list[int]        = []

    # Auto-detect sources
    if sources is None:
        sources = sorted(
            d for d in os.listdir(POSE_DIR)
            if os.path.isdir(os.path.join(POSE_DIR, d))
        )

    logger.info(f"Sources: {sources}")

    total_files = 0
    total_seqs  = 0

    for source in sources:
        source_path = os.path.join(POSE_DIR, source)

        if not os.path.isdir(source_path):
            logger.warning(f"Missing source dir: {source_path}")
            continue

        for class_name, label_id in LABELS.items():
            class_path = os.path.join(source_path, class_name)

            if not os.path.isdir(class_path):
                logger.warning(f"Missing class dir: {class_path}")
                continue

            files = sorted(f for f in os.listdir(class_path) if f.endswith(".npy"))
            logger.info(f"  [{source}/{class_name}] {len(files)} files")

            for fname in files:
                path = os.path.join(class_path, fname)
                try:
                    data = np.load(path)           # expected (N, 34)

                    if data.ndim != 2 or data.shape[1] != 34:
                        logger.warning(f"  Skip (bad shape {data.shape}): {path}")
                        continue

                    for seq in make_sequences(data):
                        feat = to_features(seq)    # (T, F)
                        X_list.append(feat)
                        y_list.append(label_id)
                        total_seqs += 1

                    total_files += 1

                except Exception as exc:
                    logger.error(f"  Failed {path}: {exc}")

    # ── Assemble ─────────────────────────────────────────────────────────
    X = np.array(X_list, dtype=np.float32)   # (N, T, F)
    y = np.array(y_list,  dtype=np.int32)    # (N,)

    ensure_dir(PROCESSED_DIR)
    np.save(SAVE_X, X)
    np.save(SAVE_Y, y)

    with open(SAVE_LABELS, "w") as f:
        json.dump(LABELS, f, indent=2)

    logger.info("=" * 44)
    logger.info(f"Files processed   : {total_files}")
    logger.info(f"Sequences created : {total_seqs}")
    logger.info(f"Dataset shape     : X={X.shape}  y={y.shape}")
    logger.info(f"Feature dim       : {X.shape[-1] if len(X) else 0}")
    logger.info(f"Saved → {SAVE_X}  {SAVE_Y}")
    logger.info("=" * 44)

    return X, y


if __name__ == "__main__":
    build()