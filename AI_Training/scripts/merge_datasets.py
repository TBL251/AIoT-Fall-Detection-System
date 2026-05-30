"""
scripts/merge_datasets.py
─────────────────────────
Merge pose .npy files from one or more sources into a unified dataset.

Usage:
    python scripts/merge_datasets.py                   # merge ALL sources
    python scripts/merge_datasets.py --sources ur le2i # selective merge
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lstm.dataset_builder import build
from configs.config import SAVE_X, SAVE_Y
from utils.logger import get_logger

logger = get_logger("merge_datasets")


def merge(sources: list[str] | None = None) -> tuple:
    logger.info(f"Merging sources: {sources or 'ALL'}")

    X, y = build(sources=sources)

    counts = Counter(y.tolist())
    logger.info(f"Total sequences : {len(X)}")
    logger.info(f"Class counts    : {dict(counts)}")
    logger.info(f"Saved → {SAVE_X},  {SAVE_Y}")

    return X, y


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge pose .npy sources into a unified dataset."
    )
    parser.add_argument(
        "--sources", nargs="*", default=None,
        help="Sub-folder names under dataset/pose/ to include (e.g. ur le2i). "
             "Omit for all.",
    )
    args = parser.parse_args()
    merge(args.sources)