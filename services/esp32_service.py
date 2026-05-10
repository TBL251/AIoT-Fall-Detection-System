import serial


class ESP32Controller:

    def __init__(self, port="COM3", baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate)
        except:
            self.ser = None
            print("[ESP32] Not connected")

    def send_alert(self, severity):

        if self.ser is None:
            return

        if severity >= 3:
            self.ser.write(b"1")  # bật buzzer
        else:
            self.ser.write(b"0")  # tắt buzzer
def send_alert(self, severity):

    if self.ser is None:
        return

    if severity == 0:
        self.ser.write(b"0")

    elif severity == 1:
        self.ser.write(b"1")

    elif severity == 2:
        self.ser.write(b"2")

    elif severity == 3:
        self.ser.write(b"3")