import serial
import time


class ESP32Controller:

    def __init__(self, port="COM5", baudrate=115200):
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

            time.sleep(3)  # FIX: 2s→3s, some ESP32 boards boot slower

            print(f"[ESP32] Connected {self.port}")

        except Exception as e:
            self.ser = None
            print("[ESP32] Not connected:", e)

    # ======================
    # RECONNECT SAFE
    # ======================
    def ensure_connection(self):
        if self.ser is None:
            self.connect()

        if self.ser and not self.ser.is_open:
            self.connect()

    # ======================
    # SEND ALERT
    # ======================
    def send_alert(self, severity):

        self.ensure_connection()

        if self.ser is None:
            print("[ESP32] Serial unavailable")
            return

        try:
            # ======================
            # LEVEL MAPPING
            # ======================
            if severity == 0:
                signal = "0"
                print("[ESP32] NORMAL")

            elif severity == 1:
                signal = "1"
                print("[ESP32] MINOR FALL")

            elif severity == 2:
                signal = "2"
                print("[ESP32] DANGEROUS FALL")

            else:
                signal = "3"
                print("[ESP32] CRITICAL EMERGENCY")

            # ======================
            # SEND (IMPORTANT FIX)
            # ======================
            message = signal + "\n"   # 🔥 FIX: ESP32 cần newline

            self.ser.write(message.encode())
            self.ser.flush()

            # FIX: track keepalive for severity 2 & 3.
            # ESP32 safety timeout is 30s — call keepalive() every ~25s
            # from your main loop to prevent the buzzer being silenced.
            # Call send_alert(0) explicitly to stop the alarm.
            self._keepalive_signal = signal if severity in (2, 3) else None

        except Exception as e:
            print("[ESP32 ERROR]", e)
            self.ser = None

    # ======================
    # FIX: KEEPALIVE
    # Resend the last command for severity 2/3 so the 30s
    # safety timeout on the ESP32 never fires while alarm is active.
    # Usage: call esp32.keepalive() every 25 s in your main loop.
    # ======================
    def keepalive(self):
        if getattr(self, "_keepalive_signal", None) is None:
            return
        self.ensure_connection()
        if self.ser is None:
            return
        try:
            self.ser.write((self._keepalive_signal + "\n").encode())
            self.ser.flush()
            print(f"[ESP32] KEEPALIVE → {self._keepalive_signal}")
        except Exception as e:
            print("[ESP32 KEEPALIVE ERROR]", e)
            self.ser = None

    # ======================
    # CLOSE CONNECTION
    # ======================
    def close(self):
        if self.ser:
            self.ser.close()
            self.ser = None
            print("[ESP32] Connection closed")