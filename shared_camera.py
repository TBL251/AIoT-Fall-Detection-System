"""
shared_camera.py
─────────────────
Module-level shared state for the latest annotated camera frame.

Any thread or module can write to `latest_frame` after acquiring
`frame_lock`, and any consumer (e.g. the Flask dashboard) can read
from it safely.

Usage
─────
    import shared_camera

    # writer (main loop)
    with shared_camera.frame_lock:
        shared_camera.latest_frame = frame.copy()

    # reader (Flask route)
    with shared_camera.frame_lock:
        frame = shared_camera.latest_frame
        if frame is not None:
            frame = frame.copy()
"""

import threading

# The most recent annotated BGR frame, or None before the first frame arrives.
latest_frame = None

# Lock that MUST be held when reading or writing `latest_frame`.
frame_lock = threading.Lock()