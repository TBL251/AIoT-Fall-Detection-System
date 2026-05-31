"""
services/local_storage.py
──────────────────────────
Saves fall-event frame buffers to disk as H.264 MP4 files via FFmpeg.

Bugs fixed
──────────
BUG 1 — FFMPEG_PATH is hard-coded to a machine-specific absolute path.
  If FFmpeg is on the system PATH (standard install), or if the project
  moves to another machine, the hard-coded path breaks.
  Fix: check the hard-coded path first; if absent, fall back to "ffmpeg"
  (system PATH).  If neither works, log a clear error.

BUG 2 — save_video() accepted `severity` as any type but
  get_severity_folder() did (severity <= 1) which raised TypeError when
  severity was a str.  Now fixed in pipeline.py (always int), and
  get_severity_folder() has a defensive int() cast with a fallback.

BUG 3 — frames list is checked with `if not frames` which is False for
  an empty deque too, but the type annotation said list.  Kept as-is
  since EventManager now converts deque → list before calling save_video.

BUG 4 — Hard-coded email fallback "unknown" folder.  If email is None
  save_video() would crash on .replace().  Added a None guard.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import traceback

import cv2

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "..", "recorded_videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Try the project-local FFmpeg first; fall back to system PATH.
_FFMPEG_LOCAL = (
    r"E:\ffmpeg-8.1.1-essentials_build"
    r"\ffmpeg-8.1.1-essentials_build"
    r"\bin\ffmpeg.exe"
)


def _get_ffmpeg() -> str | None:
    """Return a usable ffmpeg executable path, or None if not found."""
    if os.path.exists(_FFMPEG_LOCAL):
        return _FFMPEG_LOCAL
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    return None


# ── Severity folder mapping ───────────────────────────────────────────────────

def get_severity_folder(severity) -> str:
    """
    Map integer severity (0-3) to a sub-folder name.

    0 = NORMAL    → "Minor"          (treated as minor for storage purposes)
    1 = MINOR     → "Minor"
    2 = DANGEROUS → "Dangerous"
    3 = CRITICAL  → "Critical_Emergency"
    """
    try:
        severity = int(severity)
    except (TypeError, ValueError):
        severity = 0

    if severity <= 1:
        return "Minor"
    if severity == 2:
        return "Dangerous"
    return "Critical_Emergency"


# ── Video save ────────────────────────────────────────────────────────────────

def save_video(
    frames: list,
    email: str | None,
    severity,
) -> str | None:
    """
    Encode *frames* to an MP4 file and return its path, or None on failure.

    Parameters
    ----------
    frames   : list of BGR ndarrays, all the same resolution
    email    : recipient e-mail (used as folder name); None → "unknown"
    severity : int 0-3 (or any int-castable value)
    """
    try:
        if not frames:
            print("[VIDEO] No frames to save")
            return None

        # ── Resolve FFmpeg ────────────────────────────────────────────────
        ffmpeg = _get_ffmpeg()
        if ffmpeg is None:
            print(
                "[FFMPEG] Not found.  Install FFmpeg and ensure it is on "
                "the system PATH, or place it at:\n  " + _FFMPEG_LOCAL
            )
            return None

        # ── Build output path ─────────────────────────────────────────────
        safe_email = (
            (email or "unknown")
            .replace("@", "_")
            .replace(".", "_")
        )
        severity_folder = get_severity_folder(severity)
        user_dir        = os.path.join(VIDEOS_DIR, safe_email, severity_folder)
        os.makedirs(user_dir, exist_ok=True)

        timestamp  = time.strftime("%Y%m%d_%H%M%S")
        final_path = os.path.join(user_dir, f"event_{timestamp}.mp4")

        # ── Frame dimensions ──────────────────────────────────────────────
        height, width = frames[0].shape[:2]
        fps = 30

        # ── FFmpeg command ────────────────────────────────────────────────
        command = [
            ffmpeg, "-y",
            "-f",       "rawvideo",
            "-vcodec",  "rawvideo",
            "-pix_fmt", "bgr24",
            "-s",       f"{width}x{height}",
            "-r",       str(fps),
            "-i",       "-",
            "-an",
            "-c:v",     "libx264",
            "-preset",  "ultrafast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-crf",     "23",
            final_path,
        ]

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        for frame in frames:
            process.stdin.write(frame.tobytes())

        process.stdin.close()
        process.wait()

        # ── Validate output ───────────────────────────────────────────────
        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
            print("[VIDEO ERROR] MP4 not created or is empty")
            return None

        print(f"[VIDEO] MP4 saved → {final_path}")
        return final_path

    except Exception:
        traceback.print_exc()
        return None