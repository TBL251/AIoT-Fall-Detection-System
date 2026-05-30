"""
services/camera_thread.py
──────────────────────────
Thread-safe camera wrapper that continuously grabs frames in a
background thread to avoid blocking the main processing loop.

Changes vs. original
─────────────────────
- cv2.CAP_DSHOW is used only on Windows; falls back to default backend
  on Linux/macOS so the same code works everywhere.
- Added `is_open` property for health-check callers.
- `release()` waits for the background thread to exit before releasing
  the VideoCapture, preventing use-after-free crashes.
- `read()` returns (False, None) immediately when the capture is not
  open instead of blocking.
- Removed bare `except Exception` swallowing errors silently; errors are
  logged and the thread backs off with a short sleep before retrying.
- Frame resolution and FPS are read back after setting to detect
  cameras that silently ignore the requested values.
"""

from __future__ import annotations

import platform
import sys
import threading
import time

import cv2


class CameraStream:
    """
    Background-threaded camera reader.

    Parameters
    ----------
    src : int | str
        Camera index (int) or video file / RTSP URL (str).
    width, height : int
        Requested capture resolution.
    fps : int
        Requested capture frame rate.
    """

    def __init__(
        self,
        src: int | str = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
    ) -> None:

        # ── Backend selection ────────────────────────────────────────────
        # cv2.CAP_DSHOW is Windows-only; using it on Linux/macOS raises a
        # warning and may silently fail.
        if platform.system() == "Windows":
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(src)

        # ── Camera settings ──────────────────────────────────────────────
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        # ── Validate ─────────────────────────────────────────────────────
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {src!r}")

        # Read-back actual values (some cameras ignore requests silently)
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        print(
            f"[CAMERA] Opened source={src}  "
            f"resolution={actual_w}×{actual_h}  fps={actual_fps:.1f}"
        )

        # Grab the first frame synchronously so `read()` never returns
        # None before the background thread has produced anything.
        self._ret, self._frame = self.cap.read()
        if not self._ret or self._frame is None:
            self.cap.release()
            raise RuntimeError(
                f"Camera opened but could not read the first frame "
                f"(source={src!r}). Check that the camera is not in use "
                "by another application."
            )

        self._lock    = threading.Lock()
        self._running = True
        self._thread  = threading.Thread(
            target=self._update, daemon=True, name="CameraStream"
        )
        self._thread.start()

    # ── Background thread ────────────────────────────────────────────────

    def _update(self) -> None:
        """Continuously grab frames; runs in a daemon thread."""
        consecutive_failures = 0

        while self._running:
            try:
                ret, frame = self.cap.read()

                if ret and frame is not None:
                    consecutive_failures = 0
                    with self._lock:
                        self._ret   = ret
                        self._frame = frame
                else:
                    consecutive_failures += 1
                    print(
                        f"[CAMERA] Frame read failed "
                        f"(consecutive={consecutive_failures})"
                    )
                    # Back off: avoid spinning the CPU on a dead source
                    time.sleep(min(1.0, 0.1 * consecutive_failures))

            except Exception as exc:
                print(f"[CAMERA ERROR] {exc}", file=sys.stderr)
                time.sleep(0.5)

            # Yield the GIL briefly even on success
            time.sleep(0.005)

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        """True while the background thread is running."""
        return self._running

    def read(self) -> tuple[bool, cv2.typing.MatLike | None]:
        """
        Return the most recent (ret, frame) pair.

        The frame is a *copy* so the caller may mutate it freely without
        corrupting the shared buffer.
        """
        if not self._running:
            return False, None

        with self._lock:
            if self._frame is None:
                return False, None
            return self._ret, self._frame.copy()

    def release(self) -> None:
        """
        Signal the background thread to stop, wait for it to exit,
        then release the underlying VideoCapture.
        """
        self._running = False
        self._thread.join(timeout=2.0)
        self.cap.release()
        print("[CAMERA] Released")