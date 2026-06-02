"""
AI_Training/realtime/pipeline.py
──────────────────────────────────
End-to-end single-frame processing pipeline for the ICU fall-detection
system.

Returns
───────
process(frame) → (annotated_frame, fall_flag, severity, emergency_level)

    annotated_frame : BGR ndarray — frame with skeleton drawn in-place
    fall_flag       : bool        — True when a fall is detected
    severity        : float [0,1] — smoothed fall confidence
    emergency_level : str         — "NORMAL" | "MINOR" | "DANGEROUS" | "CRITICAL"

Changes vs. original
─────────────────────
- Skeleton is now redrawn with is_fall=True when a fall is confirmed,
  giving the red overlay that makes the alarm visually obvious.
- Emergency level thresholds are now named constants (easy to tune).
- `reset()` properly delegates to `predictor.reset()` (was missing).
- Lazy model loading is guarded; a descriptive error is raised if the
  model file is absent.
- Type annotations added throughout.
- `process()` no longer silently swallows exceptions; callers should
  wrap it in try/except so errors surface rather than being hidden.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np

from AI_Training.yolo.pose_extractor import extract_keypoints
from AI_Training.yolo.draw_skeleton import draw_skeleton
from AI_Training.lstm.predict import Predictor
from AI_Training.features.feature_engineering import extract_features
from AI_Training.configs.config import (
    SEQUENCE_LENGTH,
    VOTE_WINDOW,
    TCN_MODEL,
)

# ── Emergency level thresholds (confidence ≥ threshold → level) ─────────────
_LEVEL_CRITICAL   = 0.90
_LEVEL_DANGEROUS  = 0.70
_LEVEL_MINOR      = 0.50


def _confidence_to_level(conf: float) -> str:
    if conf >= _LEVEL_CRITICAL:
        return "CRITICAL"
    if conf >= _LEVEL_DANGEROUS:
        return "DANGEROUS"
    if conf >= _LEVEL_MINOR:
        return "MINOR"
    return "NORMAL"


class FallDetectionPipeline:
    """
    Stateful pipeline that accumulates pose sequences and emits
    fall/normal predictions.

    Parameters
    ----------
    smoothing_window : int
        History buffer length passed to :class:`Predictor`.
    """

    def __init__(self, smoothing_window: int = VOTE_WINDOW) -> None:
        self._seq      : deque[np.ndarray] = deque(maxlen=SEQUENCE_LENGTH)
        self.predictor : Predictor         = Predictor(window=smoothing_window)
        self._model                        = None

    # ── Internal helpers ─────────────────────────────────────────────────

    def _get_model(self):
        """Load the Keras model on first call (lazy, avoids import-time GPU init)."""
        if self._model is None:
            import tensorflow as tf

            model_path = Path(TCN_MODEL)
            if not model_path.exists():
                raise FileNotFoundError(
                    f"[Pipeline] TCN model not found at '{TCN_MODEL}'. "
                    "Run the training script first or check TCN_MODEL in config.py."
                )

            self._model = tf.keras.models.load_model(
                str(model_path), compile=False
            )
            print(f"[Pipeline] Model loaded from '{TCN_MODEL}'")

        return self._model

    # ── Public API ───────────────────────────────────────────────────────

    def process(
        self,
        frame: np.ndarray,
    ) -> tuple[np.ndarray, bool, float, str]:
        """
        Process one BGR frame and return a prediction.

        Parameters
        ----------
        frame : np.ndarray (H, W, 3)  BGR image

        Returns
        -------
        (annotated_frame, fall_flag, severity, emergency_level)
        """
        _NO_FALL = (frame, False, 0.0, "NORMAL")

        # ── Pose extraction ──────────────────────────────────────────────
        kp = extract_keypoints(frame)   # (34,) or None

        if kp is None:
            return _NO_FALL

        # ── Accumulate sequence ──────────────────────────────────────────
        self._seq.append(kp)

        if len(self._seq) < SEQUENCE_LENGTH:
            # Draw skeleton without fall colour while we warm up the buffer
            draw_skeleton(frame, kp.reshape(17, 2), is_fall=False)
            return _NO_FALL

        # ── Feature extraction ───────────────────────────────────────────
        seq_arr  = np.array(self._seq, dtype=np.float32)   # (T, 34)
        feat_seq = extract_features(seq_arr)               # (T, F)

        # ── Inference ────────────────────────────────────────────────────
        model = self._get_model()
        label, conf = self.predictor.update(model, feat_seq)

        fall_flag       = str(label).upper() == "FALL"
        severity        = float(conf)
        emergency_level = _confidence_to_level(severity) if fall_flag else "NORMAL"

        # ── Skeleton overlay (red when falling) ──────────────────────────
        draw_skeleton(frame, kp.reshape(17, 2), is_fall=fall_flag)

        return frame, fall_flag, severity, emergency_level

    def reset(self) -> None:
        """Clear all internal state (call on scene change or manual reset)."""
        self._seq.clear()
        self.predictor.reset()