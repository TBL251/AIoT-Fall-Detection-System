from services.esp32_service import ESP32Controller
import time

esp = ESP32Controller(port="COM5")


esp.send_alert(3)
