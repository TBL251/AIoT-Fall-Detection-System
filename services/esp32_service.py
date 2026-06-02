import serial
import time


class ESP32Controller:

    def __init__(
        self,
        port="COM5",
        baudrate=115200
    ):

        self.port = port

        self.baudrate = baudrate

        self.ser = None

        self.connect()

    # ======================
    # CONNECT ESP32
    # ======================

    def connect(self):

        try:

            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1
            )

            time.sleep(2)

            print(
                f"[ESP32] Connected {self.port}"
            )

        except Exception as e:

            self.ser = None

            print(
                "[ESP32] Not connected:",
                e
            )

    # ======================
    # SEND ALERT
    # ======================

    def send_alert(self, severity):

        if self.ser is None:
            print("[ESP32] Serial unavailable")
            return

        try:
            # ======================
            # FIX INPUT TYPE
            # ======================
            severity = int(severity) if severity is not None else 0
            severity = max(0, min(severity, 3))

            # ======================
            # LEVEL MAPPING
            # ======================
            if severity == 0:
                signal = b"0"
                print("[ESP32] NORMAL")

            elif severity == 1:
                signal = b"1"
                print("[ESP32] MINOR")

            elif severity == 2:
                signal = b"2"
                print("[ESP32] DANGEROUS")

            else:
                signal = b"3"
                print("[ESP32] CRITICAL")

            # ======================
            # SEND SERIAL
            # ======================
            self.ser.write(signal + b"\n")
            self.ser.flush()

            print("[ESP32 SENT]", signal)

        except Exception as e:
            print("[ESP32 ERROR]", e)
            self.ser = None