import cv2
import os
import time

BASE_DIR = "recorded_videos"


def save_video(frames, email, severity):

    # ======================
    # EMPTY CHECK
    # ======================

    if len(frames) == 0:
        return None

    # ======================
    # SAFE EMAIL
    # ======================

    safe_email = (
        email
        .replace("@", "_")
        .replace(".", "_")
    )

    # ======================
    # SEVERITY FOLDER
    # ======================

    if severity == 1:

        level_folder = "Minor"

    elif severity == 2:

        level_folder = "Dangerous"

    else:

        level_folder = "Critical Emergency"

    # ======================
    # FINAL DIRECTORY
    # ======================

    save_dir = os.path.join(
        BASE_DIR,
        safe_email,
        level_folder
    )

    os.makedirs(
        save_dir,
        exist_ok=True
    )

    # ======================
    # FILE NAME
    # ======================

    timestamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )

    path = os.path.join(
        save_dir,
        f"event_{timestamp}.mp4"
    )

    # ======================
    # VIDEO INFO
    # ======================

    h, w, _ = frames[0].shape

    fps = 20

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    out = cv2.VideoWriter(
        path,
        fourcc,
        fps,
        (w, h)
    )

    # ======================
    # WRITE VIDEO
    # ======================

    for frame in frames:

        out.write(frame)

    out.release()

    print(f"[VIDEO SAVED] {path}")

    return path