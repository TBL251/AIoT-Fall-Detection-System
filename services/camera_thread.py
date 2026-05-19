import cv2
import threading
import time


class CameraStream:

    def __init__(self, src=0):

        self.cap = cv2.VideoCapture(
            src,
            cv2.CAP_DSHOW
        )

        # =========================
        # CAMERA SETTINGS
        # =========================

        self.cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*'MJPG')
        )

        self.cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

        self.cap.set(
            cv2.CAP_PROP_FPS,
            30
        )

        # =========================
        # VALIDATE CAMERA
        # =========================

        if not self.cap.isOpened():

            raise RuntimeError(
                "Cannot open webcam"
            )

        self.lock = threading.Lock()

        self.ret, self.frame = (
            self.cap.read()
        )

        if not self.ret:

            raise RuntimeError(
                "Cannot read first frame"
            )

        self.running = True

        # =========================
        # START THREAD
        # =========================

        threading.Thread(
            target=self.update,
            daemon=True
        ).start()

    # =========================
    # CAMERA LOOP
    # =========================

    def update(self):

        while self.running:

            try:

                ret, frame = self.cap.read()

                if ret:

                    with self.lock:

                        self.ret = ret

                        self.frame = frame

                else:

                    print(
                        "[CAMERA] Failed frame"
                    )

                    time.sleep(1)

            except Exception as e:

                print(
                    "[CAMERA ERROR]",
                    e
                )

            time.sleep(0.01)

    # =========================
    # READ FRAME
    # =========================

    def read(self):

        with self.lock:

            if self.frame is None:

                return False, None

            return (
                self.ret,
                self.frame.copy()
            )

    # =========================
    # RELEASE
    # =========================

    def release(self):

        self.running = False

        time.sleep(0.2)

        self.cap.release()

        print(
            "[CAMERA] Released"
        )