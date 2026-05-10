import cv2
import os
import time

BASE_DIR = "recorded_videos"


def save_video(frames, folder="emergency"):

    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    save_dir = os.path.join(BASE_DIR, folder)
    os.makedirs(save_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(save_dir, f"event_{timestamp}.mp4")

    if len(frames) == 0:
        return None

    h, w, _ = frames[0].shape
    fps = 20

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (w, h))

    for f in frames:
        out.write(f)

    out.release()

    return path