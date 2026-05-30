"""
scripts/build_dataset.py
────────────────────────
Build the final (X.npy, y.npy) training arrays from all pose .npy files.
Delegates all logic to lstm/dataset_builder.py.

Usage:
    python scripts/build_dataset.py
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lstm.dataset_builder import build
from utils.logger import get_logger

logger = get_logger("build_dataset")


if __name__ == "__main__":
    logger.info("Building dataset from all pose sources …")

    X, y = build()

    counts = Counter(y.tolist())
    logger.info(f"Done — X={X.shape}  y={y.shape}")
    logger.info(f"Class distribution: {dict(counts)}")