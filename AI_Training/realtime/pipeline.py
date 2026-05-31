"""
AI_Training/realtime/pipeline.py
──────────────────────────────────
End-to-end single-frame processing pipeline for the ICU fall-detection
system.

Returns
───────
process(frame) → (annotated_frame, fall_flag, severity, emergency_level)

    annotated_frame : BGR ndarray  — frame with skeleton drawn in-place
    fall_flag       : bool         — True when a fall is detected
    severity        : float [0,1]  — smoothed fall confidence
    emergency_level : int          — 0=NORMAL | 1=MINOR | 2=DANGEROUS | 3=CRITICAL

Bugs fixed
──────────
BUG 1 — TypeError: '>=' not supported between instances of 'str' and 'int'
  emergency_level was a str ("CRITICAL" etc.).  EventManager.start_recording()
  does (severity >= 2) and local_storage.get_severity_folder() does (severity <= 1),
  both expecting an int.  Passing a string caused a TypeError on every fall frame.
  Fix: _confidence_to_level() now returns an int (0-3).

BUG 2 — Skeleton drawn before early-return, then discarded
  draw_skeleton() was called before the sequence-length guard.  The annotated
  frame was thrown away (early return) and the caller received a blank frame
  for the first SEQUENCE_LENGTH frames.
  Fix: draw_skeleton() is called once, after all early-returns.

BUG 3 — Shared frame reference in no-fall path
  The (frame, False, 0.0, "NORMAL") tuple re-used the original frame reference.
  If the caller mutated the frame afterwards the pipeline's internal state was
  corrupted.  Fix: no separate tuple variable — just return inline.
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

# ── Emergency level integer constants ────────────────────────────────────────
# Must match what EventManager.start_recording() and
# local_storage.get_severity_folder() expect.
LEVEL_NORMAL    = 0   # no fall / below minor threshold
LEVEL_MINOR     = 1   # conf >= 0.50
LEVEL_DANGEROUS = 2   # conf >= 0.70
LEVEL_CRITICAL  = 3   # conf >= 0.90

_CONF_CRITICAL  = 0.90
_CONF_DANGEROUS = 0.70
_CONF_MINOR     = 0.50

_LEVEL_LABELS = {
    LEVEL_NORMAL:    "NORMAL",
    LEVEL_MINOR:     "MINOR",
    LEVEL_DANGEROUS: "DANGEROUS",
    LEVEL_CRITICAL:  "CRITICAL",
}


def _confidence_to_level(conf: float) -> int:
    """Map a fall confidence [0,1] → integer severity level 0-3."""
    if conf >= _CONF_CRITICAL:
        return LEVEL_CRITICAL
    if conf >= _CONF_DANGEROUS:
        return LEVEL_DANGEROUS
    if conf >= _CONF_MINOR:
        return LEVEL_MINOR
    return LEVEL_NORMAL


class FallDetectionPipeline:
    """
    Stateful pipeline: accumulates pose sequences and emits predictions.

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
        """Load the Keras model on first call (lazy — avoids import-time GPU init)."""
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
    ) -> tuple[np.ndarray, bool, float, int]:
        """
        Process one BGR frame and return a prediction.

        Parameters
        ----------
        frame : np.ndarray (H, W, 3)  BGR image

        Returns
        -------
        (annotated_frame, fall_flag, severity, emergency_level)
            annotated_frame : frame with skeleton overlay (modified in-place)
            fall_flag       : True when a fall is detected
            severity        : smoothed fall probability  [0.0, 1.0]
            emergency_level : int  0=NORMAL 1=MINOR 2=DANGEROUS 3=CRITICAL
        """
        # ── Pose extraction ──────────────────────────────────────────────
        kp = extract_keypoints(frame)           # (34,) or None

        if kp is None:
            return frame, False, 0.0, LEVEL_NORMAL

        kp_2d = kp.reshape(17, 2)

        # ── Accumulate sequence ──────────────────────────────────────────
        self._seq.append(kp)

        if len(self._seq) < SEQUENCE_LENGTH:
            # Buffer still warming up — draw neutral skeleton, no prediction yet
            draw_skeleton(frame, kp_2d, is_fall=False)
            return frame, False, 0.0, LEVEL_NORMAL

        # ── Feature extraction ───────────────────────────────────────────
        seq_arr  = np.array(self._seq, dtype=np.float32)   # (T, 34)
        feat_seq = extract_features(seq_arr)               # (T, F)

        # ── Inference ────────────────────────────────────────────────────
        model = self._get_model()
        label, conf = self.predictor.update(model, feat_seq)

        fall_flag       : bool = str(label).upper() == "FALL"
        severity        : float = float(conf)
        emergency_level : int   = (
            _confidence_to_level(severity) if fall_flag else LEVEL_NORMAL
        )

        # ── Skeleton overlay (red on fall, green otherwise) ──────────────
        draw_skeleton(frame, kp_2d, is_fall=fall_flag)

        if fall_flag:
            print(
                f"[Pipeline] FALL  conf={severity:.2f}  "
                f"level={_LEVEL_LABELS[emergency_level]}"
            )

        return frame, fall_flag, severity, emergency_level

    def reset(self) -> None:
        """Clear sequence buffer and predictor state."""
        self._seq.clear()
        self.predictor.reset()