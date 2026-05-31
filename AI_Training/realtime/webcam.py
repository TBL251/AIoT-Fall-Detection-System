"""
AI_Training/realtime/webcam.py
───────────────────────────────
Standalone real-time fall detection viewer (AI_Training sub-module).

This script is SEPARATE from main.py.  It opens its own camera and is
intended for standalone testing of the AI model only — NOT for the
production ICU system.  The production system uses main.py +
services/camera_thread.py.

Bug fixed — wrong camera source causing recording mismatch
──────────────────────────────────────────────────────────
The original defaulted --source to "0" (built-in webcam).  When the
production system uses Camera 1, any accidental invocation of this
script (or any code path that imported it) would open Camera 0 and
produce recordings from the wrong device.

Fix:
  • Default --source is now "1" to match CAMERA_INDEX in main.py.
  • A prominent warning is printed at startup reminding the operator
    that this is a standalone test tool, not the production entry point.
  • pipeline.process() now returns 4 values (frame, fall_flag, severity,
    emergency_level:int).  The unpacking here is updated accordingly.

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

COLOR_NORMAL  = (0,  200,   0)
COLOR_FALL    = (0,    0, 255)
COLOR_WAITING = (180, 180,  0)


# ─── Argument Parser ─────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Standalone fall detection viewer (test only — not production)"
    )
    # Default source is 1 to match CAMERA_INDEX in main.py.
    # Override with --source 0 for the built-in webcam.
    p.add_argument(
        "--source", default="1",
        help="Camera index or video path (default: 1, matching CAMERA_INDEX in main.py)",
    )
    p.add_argument("--width",     type=int, default=640)
    p.add_argument("--height",    type=int, default=480)
    p.add_argument(
        "--smoothing", type=int, default=VOTE_WINDOW,
        help="Predictor vote window length",
    )
    p.add_argument("--no-display", action="store_true",
                   help="Disable GUI (headless mode)")
    return p.parse_args()


# ─── Camera helper ───────────────────────────────────────────────────────────

def open_capture(source: str, width: int, height: int) -> cv2.VideoCapture:
    src = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(src)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source!r}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)
    return cap


# ─── Recorder ────────────────────────────────────────────────────────────────

class Recorder:

    def __init__(self, w: int, h: int, fps: float = 25.0) -> None:
        self.writer : cv2.VideoWriter | None = None
        self.w      = w
        self.h      = h
        self.fps    = fps
        self.active = False

    def toggle(self) -> str:
        if self.active:
            self.stop()
            return "stopped"
        self.start()
        return "started"

    def start(self) -> None:
        ensure_dir(os.path.join(VIDEO_DIR, "videos"))
        ts     = time.strftime("%Y%m%d_%H%M%S")
        path   = os.path.join(VIDEO_DIR, "videos", f"fall_{ts}{RECORD_EXT}")
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


# ─── Overlay ─────────────────────────────────────────────────────────────────

def draw_overlay(
    frame: np.ndarray,
    label: str,
    conf: float,
    fps: float,
    recording: bool,
) -> None:
    h, w = frame.shape[:2]
    color = {"FALL": COLOR_FALL, "NORMAL": COLOR_NORMAL}.get(label, COLOR_WAITING)

    cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 0), -1)
    cv2.putText(
        frame, f"{label}  {conf*100:.1f}%",
        (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, f"FPS: {fps:.1f}",
        (w - 140, h - 16), cv2.FONT_HERSHEY_SIMPLEX,
        0.6, (200, 200, 200), 1, cv2.LINE_AA,
    )
    if recording:
        cv2.circle(frame, (w - 20, 20), 8, COLOR_FALL, -1)


# ─── Main loop ───────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:
    print(
        "\n⚠️  webcam.py is a STANDALONE TEST TOOL.\n"
        "   For the production ICU system run main.py instead.\n"
    )

    cap      = open_capture(args.source, args.width, args.height)
    pipeline = FallDetectionPipeline(smoothing_window=args.smoothing)
    fps_ctr  = FPSCounter()

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    recorder   = Recorder(w, h)
    # last_result stores (label_str, conf, annotated_frame)
    # pipeline.process() returns (frame, fall_flag, severity, emergency_level:int)
    # We derive label_str from fall_flag for the overlay.
    last_label    : str              = "WAITING"
    last_conf     : float            = 0.0
    last_annotated: np.ndarray | None = None
    frame_id      = 0

    logger.info(f"Stream: {args.source}  {w}×{h}")

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

            if frame_id % SKIP_FRAMES == 0:
                # pipeline now returns 4 values; unpack all four
                annotated, fall_flag, conf, _level = pipeline.process(frame)
                last_label     = "FALL" if fall_flag else "NORMAL"
                last_conf      = conf
                last_annotated = annotated if annotated is not None else frame
            else:
                if last_annotated is None:
                    last_annotated = frame

            draw_overlay(
                last_annotated, last_label, last_conf,
                fps_ctr.fps, recorder.active,
            )

            if recorder.active:
                recorder.write(last_annotated)

            if not args.no_display:
                cv2.imshow(WINDOW_NAME, last_annotated)

            key = cv2.waitKey(1) & 0xFF

            if key in (27, ord("q")):
                break
            elif key == ord("r"):
                logger.info(f"Recorder {recorder.toggle()}")
            elif key == ord("s"):
                pred_dir = os.path.join(VIDEO_DIR, "predictions")
                ensure_dir(pred_dir)
                ts   = time.strftime("%Y%m%d_%H%M%S")
                path = os.path.join(pred_dir, f"snap_{ts}.png")
                cv2.imwrite(path, last_annotated)
                logger.info(f"Snapshot saved → {path}")
            elif key == 32:
                pipeline.reset()
                logger.info("Pipeline reset")

    finally:
        recorder.stop()
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Stream closed.")


if __name__ == "__main__":
    run(parse_args())