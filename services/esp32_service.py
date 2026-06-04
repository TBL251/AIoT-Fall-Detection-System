import os
import serial
import time


# FIX: read port from environment so the device path can be changed
# without touching source code (e.g. /dev/ttyUSB0 on Linux).
_DEFAULT_PORT = os.environ.get("ESP32_PORT", "COM5")
_DEFAULT_BAUD = int(os.environ.get("ESP32_BAUD", "115200"))

# Minimum seconds to wait before retrying a failed connect.
_RECONNECT_BACKOFF = 5.0


class ESP32Controller:

    def __init__(self, port: str = _DEFAULT_PORT, baudrate: int = _DEFAULT_BAUD):
        self.port     = port
        self.baudrate = baudrate
        self.ser      = None
        
        self.connection_error_shown = False

        self.last_send_time    = 0
        self.min_interval      = 0.2   # anti-spam (200 ms)

        # Initialise to a value that ensures the first connect() call is
        # never skipped by the backoff window.
        self._last_connect_attempt = -_RECONNECT_BACKOFF

        self.connect()

    # ======================
    # CONNECT ESP32
    # ======================
    def connect(self):
        now = time.time()
        if now - self._last_connect_attempt < _RECONNECT_BACKOFF:
            return   # still in backoff window

        self._last_connect_attempt = now

        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1,
            )
            time.sleep(2)   # allow ESP32 to reset after DTR toggle
            print(f"[ESP32] Connected on {self.port}")
        except Exception as e:
            if not self.connection_error_shown:
                print(
                    f"[ESP32] Not connected ({self.port}): {e}"
                )
                self.connection_error_shown = True

    # ======================
    # SAFE WRITE
    # ======================
    def _safe_write(self, data: bytes) -> bool:
        if self.ser is None:
            self.connect()
            if self.ser is None:
                return False

        try:
            if not self.ser.is_open:
                self.connect()
                if self.ser is None:
                    return False

            self.ser.write(data)
            self.ser.flush()
            return True

        except Exception as e:
            print("[ESP32 ERROR]", e)
            self.ser = None
            return False

    # ======================
    # SEND ALERT
    # ======================
    def send_alert(self, severity):
        now = time.time()
        if now - self.last_send_time < self.min_interval:
            return

        self.last_send_time = now

        try:
            severity = int(severity) if severity is not None else 0
            severity = max(0, min(severity, 3))

            # FIX: use a single consistent numeric protocol ("0"–"3") for
            # both alerts and the normal/stop state so the firmware only
            # needs one parser.  send_stop() now sends "0\n" via this
            # same method instead of the inconsistent "S0\n" it used to.
            signal = str(severity).encode()
            label  = {0: "NORMAL", 1: "MINOR", 2: "DANGEROUS", 3: "CRITICAL"}.get(severity, "?")

            ok = self._safe_write(signal + b"\n")
            if ok:
                print(f"[ESP32 SENT] {signal.decode()} ({label})")

        except Exception as e:
            print("[ESP32 ERROR]", e)
            self.ser = None

    # ======================
    # STOP ALERT
    # ======================
    def send_stop(self):
        """
        Signal the ESP32 to return to the NORMAL / quiet state.

        FIX: was sending "S0\\n" while send_alert(0) sends "0\\n" — two
        different stop signals that firmware had to handle separately.
        Unified to send_alert(0) so the firmware only needs one code path.
        """
        self.send_alert(0)