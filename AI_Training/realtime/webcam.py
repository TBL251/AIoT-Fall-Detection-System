"""
realtime/webcam.py
───────────────────
Optimized real-time fall detection.

Key-bindings
────────────
  Q / ESC — quit
  R       — toggle video recording
  S       — save snapshot
  SPACE   — reset pipeline state
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from realtime.pipeline import FallDetectionPipeline
from configs.config import VIDEO_DIR, SKIP_FRAMES, VOTE_WINDOW
from utils.fps import FPSCounter
from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger("webcam")

WINDOW_NAME  = "Fall Detection — Q to quit"
RECORD_CODEC = "mp4v"
RECORD_EXT   = ".mp4"

# Overlay colours (BGR)
COLOR_NORMAL  = (0,  200, 0)
COLOR_FALL    = (0,  0,   255)
COLOR_WAITING = (180, 180, 0)


# ─── Argument Parser ─────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Real-time fall detection")
    p.add_argument("--source",     default="0",
                   help="Camera index or video path (default: 0)")
    p.add_argument("--width",      type=int, default=640)
    p.add_argument("--height",     type=int, default=480)
    p.add_argument("--smoothing",  type=int, default=VOTE_WINDOW,
                   help="Predictor vote window length")
    p.add_argument("--no-display", action="store_true",
                   help="Disable GUI (headless mode)")
    return p.parse_args()


# ─── Camera helper ───────────────────────────────────────────────────────────

def open_capture(source: str, width: int, height: int) -> cv2.VideoCapture:
    src = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(src)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)      # minimise latency

    return cap


# ─── Recorder ────────────────────────────────────────────────────────────────

class Recorder:
    """Optional video recorder toggled by pressing 'R'."""

    def __init__(self, w: int, h: int, fps: float = 25.0) -> None:
        self.writer : cv2.VideoWriter | None = None
        self.w      : int   = w
        self.h      : int   = h
        self.fps    : float = fps
        self.active : bool  = False

    def toggle(self) -> str:
        if self.active:
            self.stop()
            return "stopped"
        self.start()
        return "started"

    def start(self) -> None:
        ensure_dir(os.path.join(VIDEO_DIR, "videos"))
        ts   = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(VIDEO_DIR, "videos", f"fall_{ts}{RECORD_EXT}")
        fourcc = cv2.VideoWriter_fourcc(*RECORD_CODEC)
        self.writer = cv2.VideoWriter(path, fourcc, self.fps, (self.w, self.h))
        self.active = True
        logger.info(f"Recording → {path}")

    def stop(self) -> None:
        if self.writer:
            self.writer.release()
        self.writer = None
        self.active = False
        logger.info("Recording stopped")

    def write(self, frame: np.ndarray) -> None:
        if self.active and self.writer is not None:
            self.writer.write(frame)


# ─── Overlay drawing ─────────────────────────────────────────────────────────

def draw_overlay(
    frame: np.ndarray,
    label: str,
    conf: float,
    fps: float,
    recording: bool,
) -> None:
    """Draw status overlay on frame in-place."""
    h, w = frame.shape[:2]

    color = {
        "FALL":    COLOR_FALL,
        "NORMAL":  COLOR_NORMAL,
        "WAITING": COLOR_WAITING,
    }.get(label, COLOR_WAITING)

    # Status banner
    cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 0), -1)
    cv2.putText(frame, f"{label}  {conf*100:.1f}%",
                (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 2, cv2.LINE_AA)

    # FPS (bottom-right)
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (w - 140, h - 16), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (200, 200, 200), 1, cv2.LINE_AA)

    # Recording indicator
    if recording:
        cv2.circle(frame, (w - 20, 20), 8, COLOR_FALL, -1)


# ─── Main loop ───────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:
    cap      = open_capture(args.source, args.width, args.height)
    pipeline = FallDetectionPipeline(smoothing_window=args.smoothing)
    fps_ctr  = FPSCounter()

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    recorder    = Recorder(w, h)
    last_result : tuple[str, float, np.ndarray | None] = ("WAITING", 0.0, None)
    frame_id    = 0

    logger.info(f"Stream: {args.source}  Resolution: {w}×{h}")

    if not args.no_display:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Stream ended or frame drop — stopping.")
                break

            fps_ctr.tick()
            frame_id += 1

            # ── YOLO every SKIP_FRAMES, reuse result otherwise ──────────
            if frame_id % SKIP_FRAMES == 0:
                label, conf, annotated = pipeline.process(frame)
                last_result = (label, conf, annotated if annotated is not None else frame)
            else:
                label, conf, annotated = last_result
                if annotated is None:
                    annotated = frame

            draw_overlay(annotated, label, conf, fps_ctr.fps, recorder.active)

            if recorder.active:
                recorder.write(annotated)

            if not args.no_display:
                cv2.imshow(WINDOW_NAME, annotated)

            key = cv2.waitKey(1) & 0xFF

            if key in (27, ord("q")):
                break
            elif key == ord("r"):
                logger.info(f"Recorder {recorder.toggle()}")
            elif key == ord("s"):
                ensure_dir(PRED_DIR := os.path.join(VIDEO_DIR, "predictions"))
                ts   = time.strftime("%Y%m%d_%H%M%S")
                path = os.path.join(PRED_DIR, f"snap_{ts}.png")
                cv2.imwrite(path, annotated)
                logger.info(f"Snapshot saved → {path}")
            elif key == 32:          # SPACE
                pipeline.reset()
                logger.info("Pipeline reset")

    finally:
        recorder.stop()
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Stream closed.")


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run(parse_args())