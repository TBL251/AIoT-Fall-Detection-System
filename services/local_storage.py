import cv2
import os
import time
import subprocess

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

FFMPEG_PATH = r"E:\ffmpeg-8.1.1-essentials_build\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"

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

        raw_path = os.path.join(
            user_dir,
            f"raw_{timestamp}.avi"
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
        # SAVE RAW VIDEO
        # =========================

        fourcc = cv2.VideoWriter_fourcc(
            *"XVID"
        )

        writer = cv2.VideoWriter(
            raw_path,
            fourcc,
            fps,
            (width, height)
        )

        for frame in frames:

            writer.write(frame)

        writer.release()

        print("[VIDEO] Raw AVI saved")

        # =========================
        # CHECK FFMPEG
        # =========================

        if not os.path.exists(
            FFMPEG_PATH
        ):

            print(
                "[FFMPEG] ffmpeg.exe not found"
            )

            return raw_path

        # =========================
        # CONVERT TO MP4
        # =========================

        command = [

            FFMPEG_PATH,

            "-y",

            "-i", raw_path,

            # H264 codec
            "-c:v", "libx264",

            # Fast encode
            "-preset", "ultrafast",

            # Telegram compatible
            "-pix_fmt", "yuv420p",

            # Stream immediately
            "-movflags", "+faststart",

            # FPS
            "-r", "30",

            # Optimize size
            "-crf", "23",

            # no audio
            "-an",

            final_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # =========================
        # CHECK RESULT
        # =========================

        if result.returncode != 0:

            print("[FFMPEG ERROR]")

            print(
                result.stderr.decode(
                    errors="ignore"
                )
            )

            return raw_path

        # =========================
        # DELETE RAW AVI
        # =========================

        if os.path.exists(raw_path):

            os.remove(raw_path)

        print("[VIDEO] MP4 optimized")

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