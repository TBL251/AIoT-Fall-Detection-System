import cv2
import os
import time
import subprocess
import numpy as np

# =========================
# BASE PATH
# =========================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

VIDEOS_DIR = os.path.join(
    BASE_DIR,
    "..",
    "recorded_videos"
)

os.makedirs(
    VIDEOS_DIR,
    exist_ok=True
)

# =========================
# FFMPEG PATH
# =========================

FFMPEG_PATH = (
    r"E:\ffmpeg-8.1.1-essentials_build"
    r"\ffmpeg-8.1.1-essentials_build"
    r"\bin\ffmpeg.exe"
)

# =========================
# GET SEVERITY FOLDER
# =========================

def get_severity_folder(severity):

    if severity <= 1:
        return "Minor"

    elif severity == 2:
        return "Dangerous"

    else:
        return "Critical Emergency"

# =========================
# SAVE VIDEO
# =========================

def save_video(
    frames,
    email,
    severity
):

    try:

        if not frames:

            print("[VIDEO] No frames")

            return None

        # =========================
        # USER FOLDER
        # =========================

        safe_email = (
            email
            .replace("@", "_")
            .replace(".", "_")
        )

        severity_folder = get_severity_folder(
            severity
        )

        user_dir = os.path.join(
            VIDEOS_DIR,
            safe_email,
            severity_folder
        )

        os.makedirs(
            user_dir,
            exist_ok=True
        )

        # =========================
        # FILE NAME
        # =========================

        timestamp = time.strftime(
            "%Y%m%d_%H%M%S"
        )

        final_path = os.path.join(
            user_dir,
            f"event_{timestamp}.mp4"
        )

        # =========================
        # VIDEO INFO
        # =========================

        height, width = frames[0].shape[:2]

        fps = 30

        # =========================
        # CHECK FFMPEG
        # =========================

        if not os.path.exists(
            FFMPEG_PATH
        ):

            print(
                "[FFMPEG] Not found"
            )

            return None

        # =========================
        # FFMPEG COMMAND
        # =========================

        command = [

            FFMPEG_PATH,

            "-y",

            # input from pipe
            "-f", "rawvideo",

            "-vcodec", "rawvideo",

            "-pix_fmt", "bgr24",

            "-s", f"{width}x{height}",

            "-r", str(fps),

            "-i", "-",

            # encoder
            "-an",

            "-c:v", "libx264",

            # ULTRA FAST
            "-preset", "ultrafast",

            # Telegram compatible
            "-pix_fmt", "yuv420p",

            # stream immediately
            "-movflags", "+faststart",

            # quality
            "-crf", "23",

            final_path
        ]

        # =========================
        # START FFMPEG
        # =========================

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # =========================
        # WRITE FRAMES
        # =========================

        for frame in frames:

            process.stdin.write(
                frame.tobytes()
            )

        process.stdin.close()

        process.wait()

        # =========================
        # CHECK OUTPUT
        # =========================

        if not os.path.exists(
            final_path
        ):

            print(
                "[VIDEO ERROR] MP4 not created"
            )

            return None

        print("[VIDEO] MP4 SAVED")

        print(
            f"[VIDEO PATH] {final_path}"
        )

        return final_path

    except Exception as e:

        print(
            "[SAVE VIDEO ERROR]",
            e
        )

        return None