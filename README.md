# 🧠 AIoT Fall Detection & Emergency Severity System

Hệ thống AIoT giám sát con người theo thời gian thực, phát hiện té ngã và phân loại mức độ nguy hiểm (Normal → Critical Emergency).  
Hệ thống kết hợp AI (MediaPipe + OpenCV), IoT (ESP32), Firebase (metadata), Telegram Bot và Local Storage.

---

# 🚀 Features

## 🧠 AI Detection
- Real-time human pose estimation (MediaPipe)
- Fall detection based on:
  - Body angle
  - Movement speed
  - Posture change over time

## ⚠️ Severity Classification
- Level 0: Normal
- Level 1: Minor Fall (có thể tự đứng dậy)
- Level 2: Dangerous Fall (cần hỗ trợ)
- Level 3: Critical Emergency (nghi ngờ: co giật / đột quỵ / bất động lâu)

## 📹 Video System
- Tự động ghi video khi có sự kiện
- Lưu hoàn toàn LOCAL (edge device)
- Không upload video lên cloud → tối ưu tốc độ

## ☁️ Cloud (Firebase)
- Chỉ lưu metadata:
  - event type
  - severity level
  - timestamp
  - video path (local)

## 📲 Notification System
- Telegram Bot gửi cảnh báo realtime
- ESP32 buzzer kích hoạt khi Level 3

## 🌐 Dashboard
- Xem lịch sử sự kiện
- Xem video đã lưu
- Hiển thị mức độ nguy hiểm

---

# 🏗️ System Architecture

Camera (Webcam)  
↓  
OpenCV + MediaPipe (Pose Estimation)  
↓  
Fall Detection Engine  
↓  
Severity Classification (0–3)  
↓  
Event Manager  
↓  
- Local Storage (Video Recording)  
- Firebase (Event Metadata)  
- Telegram Bot (Alert System)  
- ESP32 (Buzzer Alarm)  
↓  
Web Dashboard

---

# 📁 Project Structure

```text
AIoT-Fall-Detection-System/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── ai_detection/
│   ├── pipeline.py
│   ├── pose_detection.py
│   ├── fall_detection.py
│   ├── emergency_detection.py
│   └── utils.py
│
├── services/
│   ├── local_storage.py
│   ├── firebase_service.py
│   ├── telegram_service.py
│   ├── esp32_service.py
│   └── event_manager.py
│
├── dashboard/
│   ├── app.py
│   ├── api.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── script.js
│
├── esp32/
│   └── main.ino
│
├── recorded_videos/
│   ├── emergency/
│   └── normal/
│
├── dataset/
│   ├── fall/
│   └── normal/
│
├── config/
│   └── settings.py
│
└── docs/
    └── system_diagram.png
```

---

# ⚙️ Installation

## 1. Clone project
```bash
git clone https://github.com/TBL251/AIoT-Fall-Detection-System.git
cd AIoT-Fall-Detection-System
```


2. Install dependencies
```
pip install -r requirements.txt
```


▶️ Run System
```
python main.py
```


🧠 System Workflow
```
Webcam capture realtime video
MediaPipe detect human pose
AI analyzes posture + movement
System classifies severity level
If event detected:
Save video locally
Save metadata to Firebase
Send Telegram alert
Trigger ESP32 buzzer
Dashboard displays results
```


📊 Severity Levels
```text
Level	Name	Description	Action
0	Normal	No issue	No action
1	Minor Fall	Slight imbalance	UI warning
2	Dangerous Fall	Needs assistance	Telegram alert
3	Critical Emergency	Possible stroke / seizure / unconscious	Full alert system
```

💾 Storage Design

📌 Local Storage (Main)
recorded_videos/emergency/
recorded_videos/normal/
📌 Firebase (Metadata only)
```
{
  "event": "FALL",
  "severity": 3,
  "timestamp": "2026-05-09 10:30:00",
  "video_path": "recorded_videos/emergency/fall_001.mp4"
}
```


📲 Telegram Alert Example
```
⚠️ CRITICAL EMERGENCY DETECTED
Severity: Level 3
Time: 10:30:00
```


🔔 ESP32 Module
- Receives signal from system
- Activates buzzer for Level 3 only


🌐 Dashboard Features
- Event history tracking
- Video playback (local)
- Severity visualization
- System monitoring


🛠️ Tech Stack
- Python
- OpenCV
- MediaPipe
- Flask
- Firebase
- Telegram Bot API
- ESP32 


🎯 Project Goal

- Build a real-time AIoT system that can:

  - Detect human falls
  - Classify emergency severity levels
  - Trigger multi-channel alerts
  - Operate efficiently using local-first video processing


👨‍💻 Notes
- System optimized for edge computing
- Video stored locally for performance
- Firebase used only for lightweight metadata
