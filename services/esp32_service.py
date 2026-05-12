import serial
import time


class ESP32Controller:

    def __init__(
        self,
        port="COM3",
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

            print(
                "[ESP32] Serial unavailable"
            )

            return

        try:

            # ======================
            # LEVEL MAPPING
            # ======================

            if severity == 0:

                signal = b"0"

                print(
                    "[ESP32] NORMAL"
                )

            elif severity == 1:

                signal = b"1"

                print(
                    "[ESP32] MINOR FALL"
                )

            elif severity == 2:

                signal = b"2"

                print(
                    "[ESP32] DANGEROUS FALL"
                )

            else:

                signal = b"3"

                print(
                    "[ESP32] CRITICAL EMERGENCY"
                )

            # ======================
            # SEND SERIAL
            # ======================

            self.ser.write(signal)

            self.ser.flush()

        except Exception as e:

            print(
                "[ESP32 ERROR]",
                e
            )

            self.ser = None