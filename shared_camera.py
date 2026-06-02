"""
shared_camera.py
─────────────────
Module-level shared state for the single webcam instance and the most
recent annotated frame.

Design
──────
The webcam is opened ONCE inside main.py (via CameraStream) and stored
here.  Both the AI pipeline loop (main.py) and the Flask streaming route
(app.py / gen_frames) read from this single object — no second
VideoCapture is ever opened.

                    ┌─────────────┐
                    │   main.py   │  writes annotated frames
                    │  (AI loop)  │──────────────────────────────┐
                    └──────┬──────┘                              │
          opens once       │                                     ▼
          ┌────────────┐   │                           ┌──────────────────┐
          │CameraStream│◄──┘  shared_camera.camera     │  latest_frame    │
          │  (thread)  │      shared_camera.frame_lock │  (annotated BGR) │
          └────────────┘                               └────────┬─────────┘
                                                               │  reads
                                                    ┌──────────▼──────────┐
                                                    │  app.py / gen_frames │
                                                    │  (Flask MJPEG route) │
                                                    └─────────────────────┘

Usage
─────
    # In main.py — after opening the camera:
    import shared_camera
    shared_camera.camera = camera          # store the CameraStream instance

    # Writer (AI loop in main.py):
    with shared_camera.frame_lock:
        shared_camera.latest_frame = annotated_frame.copy()

    # Reader (Flask route in app.py):
    with shared_camera.frame_lock:
        frame = shared_camera.latest_frame
        if frame is not None:
            frame = frame.copy()
"""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only imported for type hints; avoids a circular import at runtime.
    from services.camera_thread import CameraStream

# ── Shared camera instance ────────────────────────────────────────────────────
# Set by main.py immediately after CameraStream() succeeds.
# Read by any module that needs raw frames (currently none — the AI loop
# consumes them and publishes annotated copies via latest_frame).
camera: "CameraStream | None" = None

# ── Shared annotated frame ────────────────────────────────────────────────────
# The most recent BGR frame after pose-estimation / annotation overlays.
# None until the first frame has been processed.
latest_frame = None

# Lock that MUST be held when reading or writing latest_frame (or camera).
frame_lock = threading.Lock()

current_level = 0
current_severity = 0
current_state = ""
current_risk = 0
latest_frame = None