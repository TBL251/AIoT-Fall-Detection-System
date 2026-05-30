"""
lstm/predict.py
───────────────
Stateful predictor with three-stage post-processing:

  1. Exponential Moving Average  (EMA)   — smooths per-frame noise
  2. Majority Voting             (Vote)  — consensus over a sliding window
  3. Hysteresis Thresholding             — prevents rapid state flicker
"""

from __future__ import annotations

import numpy as np
from collections import deque
from AI_Training.configs.config import (
    CONFIDENCE_THRESHOLD,
    EMA_ALPHA,
    VOTE_WINDOW, VOTE_THRESHOLD,
    HYSTERESIS_ON, HYSTERESIS_OFF,
    SEQUENCE_LENGTH,
)


# ─── Raw inference ──────────────────────────────────────────────────────────

def predict_proba(model, x: np.ndarray) -> float:
    """
    Run a single forward pass.

    Parameters
    ----------
    model : loaded keras model
    x     : (1, T, F) float32 array

    Returns
    -------
    float in [0, 1]  — probability of FALL
    """
    p = float(model.predict(x, verbose=0)[0][0])
    return float(np.clip(p, 0.0, 1.0))


# ─── Stateful predictor ─────────────────────────────────────────────────────

class Predictor:
    """
    Wraps the raw model with EMA smoothing, majority voting, and
    hysteresis to produce a stable FALL / NORMAL label.

    Parameters
    ----------
    window : int
        Length of the EMA / voting history buffer.
    """

    def __init__(self, window: int = VOTE_WINDOW) -> None:
        self._hist   : deque[float] = deque(maxlen=window)
        self._state  : str          = "NORMAL"
        self._ema    : float        = 0.0
        self._alpha  : float        = EMA_ALPHA

    # ── Public API ──────────────────────────────────────────────────────

    def update(self, model, seq) -> tuple[str, float]:
        """
        Process one new sequence window.

        Parameters
        ----------
        model : loaded keras model
        seq   : array-like (T, F) — current sliding-window sequence

        Returns
        -------
        (label, confidence)
            label      : "FALL" | "NORMAL" | "WAITING"
            confidence : smoothed probability [0, 1]
        """
        seq = np.asarray(seq, dtype=np.float32)

        if len(seq) < SEQUENCE_LENGTH:
            return "WAITING", 0.0

        x = seq[None, ...]                          # (1, T, F)
        p = predict_proba(model, x)

        # Stage 1 — EMA smoothing
        self._ema = self._alpha * p + (1.0 - self._alpha) * self._ema
        self._hist.append(self._ema)

        # Stage 2 — majority voting
        votes = sum(1 for v in self._hist if v >= CONFIDENCE_THRESHOLD)
        majority = votes >= VOTE_THRESHOLD

        # Stage 3 — hysteresis state machine
        smooth = float(np.mean(self._hist))

        if self._state == "NORMAL":
            if smooth > HYSTERESIS_ON and majority:
                self._state = "FALL"
        else:  # currently in FALL
            if smooth < HYSTERESIS_OFF:
                self._state = "NORMAL"

        return self._state, round(smooth, 4)

    def reset(self) -> None:
        """Clear all internal state (call on scene change / reset)."""
        self._hist.clear()
        self._state = "NORMAL"
        self._ema   = 0.0