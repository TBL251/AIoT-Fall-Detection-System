# AIoT Fall Detection System

AI-powered IoT Fall Detection & Emergency Monitoring System using:

* Python
* OpenCV
* MediaPipe
* Flask Dashboard
* Telegram Bot
* Firebase
* ESP32 Alarm Controller

The system detects human falls in realtime, records emergency videos, stores them automatically, and sends alerts through Telegram and ESP32 devices.

---

# Features

## AI Fall Detection

* Realtime pose estimation using MediaPipe
* Fall state analysis
* Risk score calculation
* Severity classification:

  * Minor
  * Dangerous
  * Critical Emergency

---

## Smart Emergency Recording

The system records automatically when a fall is detected.

Recording logic:

```text
FALL DETECTED
    ↓
Start Recording
    ↓
Danger ?
 ├── YES → Continue Recording
 └── NO
        ↓
   Wait Recovery Time
        ↓
Normal stable ?
 ├── YES → Stop Recording
 └── NO → Continue Recording
```

---

## Telegram Integration

* Instant emergency alerts
* Inline video playback in Telegram
* Recovery video delivery
* Emergency notifications

---

## ESP32 Integration

* LED / buzzer emergency alarm
* Serial communication
* Emergency level synchronization

---

## Flask Dashboard

Web dashboard with:

* Login/Register
* Live camera monitoring
* Realtime AI status
* Replay recorded videos
* Charts & statistics
* User profile system

---

## Firebase Support

* Event storage
* Cloud synchronization
* Emergency history logging

---

# Project Structure

```text
AIoT-Fall-Detection-System/
│
├── ai_detection/
│   ├── pipeline.py
│   ├── pose_detector.py
│   ├── fall_detector.py
│   └── utils.py
│
├── dashboard/
│   ├── templates/
│   ├── static/
│   ├── app.py
│   ├── auth.py
│   ├── mail.py
│   └── security.py
│
├── services/
│   ├── event_manager.py
│   ├── local_storage.py
│   ├── telegram_service.py
│   ├── firebase_service.py
│   ├── esp32_service.py
│   └── shared_state.py
│
├── recorded_videos/
│
├── main.py
├── requirements.txt
└── README.md
```

---

# Installation

## 1. Clone Project

```bash
git clone https://github.com/TBL251/AIoT-Fall-Detection-System.git
cd AIoT-Fall-Detection-System
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

# FFmpeg Installation

FFmpeg is required for:

* H264 encoding
* Telegram inline playback
* Fast MP4 optimization

## Download

Official site:
https://ffmpeg.org/download.html

Windows build:
https://www.gyan.dev/ffmpeg/builds/

---

## Verify Installation

```bash
ffmpeg -version
```

---

# Environment Variables

Create `.env` file:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_CHAT_ID

MAIL_USERNAME=YOUR_EMAIL
MAIL_PASSWORD=YOUR_PASSWORD

FIREBASE_CREDENTIALS=YOUR_FIREBASE_JSON
```

---

# Running The System

## Start Dashboard

```bash
python dashboard/app.py
```

Dashboard:

```text
http://127.0.0.1:5000
```

---

## Start AI Engine

```bash
python main.py
```

---

# Telegram Bot Setup

## Create Bot

Open:
https://t.me/BotFather

Command:

```text
/newbot
```

Copy the bot token.

---

## Get Chat ID

Open:
https://t.me/getmyid_bot

---

# Video Storage Structure

```text
recorded_videos/
│
└── user_email/
    ├── Minor/
    ├── Dangerous/
    └── Critical Emergency/
```

Example:

```text
recorded_videos/tbl1240_gmail_com/Critical Emergency/event_20260519_120000.mp4
```

---

# AI Pipeline

Current version uses:

* MediaPipe pose estimation
* Angle calculation
* State machine logic

Future upgrade:

* Deep Learning model
* YOLO / LSTM / CNN
* Custom AI training dataset

---

# Current Detection Logic

The system currently detects:

* Body angle
* Sudden vertical collapse
* Long lying duration
* Movement recovery

---

# Future AI Training Plan

Planned upgrade:

* Collect dataset
* Train custom fall detection model
* Replace mathematical heuristics
* Deploy optimized AI inference

Suggested models:

* YOLOv8 Pose
* LSTM Action Recognition
* MoveNet
* TensorFlow Lite

---

# Performance Optimization

Optimizations included:

* FPS limiter
* Realtime frame buffering
* FFmpeg pipe encoding
* Telegram streaming support
* Async recording
* Reduced camera lag

---

# Technologies Used

* Python
* OpenCV
* MediaPipe
* Flask
* SocketIO
* Firebase
* Telegram Bot API
* FFmpeg
* ESP32
* TensorFlow Lite

---

# Security Features

* Password hashing
* Encrypted emails
* Session management
* OTP verification
* Secure Telegram token storage

---

# License

MIT License

---

# Author

Developed by:
TBL251

GitHub:
https://github.com/TBL251/AIoT-Fall-Detection-System
