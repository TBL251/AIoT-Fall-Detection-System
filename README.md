# AIoT Fall Detection System

An AI-powered IoT Fall Detection and Emergency Monitoring System for elderly care, patient monitoring, and smart healthcare environments.

The system combines Computer Vision, Deep Learning, IoT devices, Cloud Services, and Real-Time Notifications to detect falls, classify emergency severity, record incidents, and notify caregivers instantly.

---

# Features

## Real-Time Fall Detection

The system uses:

* YOLO Pose for human pose estimation
* Temporal Convolutional Network (TCN) for action classification
* Real-time video processing
* Automatic fall confidence scoring
* Emergency severity assessment

Severity Levels:

* Minor
* Dangerous
* Critical Emergency

---

## Smart Emergency Recording

The system automatically records video when a fall is detected.

Workflow:

```text
Fall Detected
      ↓
Start Recording
      ↓
Evaluate Severity
      ↓
Monitor Recovery
      ↓
Recovery Stable?
      ↓
Save Video
```

Features:

* Pre-event frame buffering
* Post-event recording
* MP4 video generation
* FFmpeg H264 encoding
* Automatic storage organization

---

## Telegram Emergency Alert

When a fall occurs:

* Telegram notification is sent instantly
* Emergency severity is included
* Event video is uploaded automatically
* Recovery notification can be sent

---

## ESP32 Emergency Alarm

ESP32 integration supports:

* Buzzer alarm
* LED warning system
* Serial communication
* Emergency level synchronization

---

## Flask Dashboard

Web-based monitoring dashboard:

* User Login / Registration
* OTP Verification
* Live Camera Monitoring
* Real-Time AI Status
* Replay Recorded Videos
* Statistics Dashboard
* User Profile Management

---

## Firebase Integration

Firebase is used for:

* Event Logging
* Cloud Synchronization
* Historical Data Storage
* Monitoring Analytics

---

# System Architecture

```text
USB Camera
     │
     ▼
YOLO Pose
     │
     ▼
Feature Extraction
     │
     ▼
TCN Model
     │
     ▼
Fall Classification
     │
 ┌───┼─────────────┐
 │   │             │
 ▼   ▼             ▼
ESP32 Telegram   Dashboard
Alarm Alert      Stream
 │
 ▼
Video Recording
```

---

# Dataset

The model is trained using two public fall detection datasets.

## UR Fall Detection Dataset

Contains:

* RGB videos
* Fall activities
* Activities of Daily Living (ADL)
* Multiple subjects
* Multiple viewpoints

Official Website:

https://fenix.ur.edu.pl/~mkepski/ds/uf.html

---

## Le2i Fall Detection Dataset

Contains:

* Indoor fall scenarios
* Daily activities
* Multiple fall types
* Various camera placements

Official Website:

https://le2i.cnrs.fr/Fall-detection-Dataset

---

# Dataset Pipeline

```text
UR Dataset
      │
      ▼
Frame Extraction

Le2i Dataset
      │
      ▼
Frame Extraction

      ▼
YOLO Pose Extraction

      ▼
Feature Engineering

      ▼
Merged Dataset

      ▼
TCN Training
```

---

# AI Model

## Pose Estimation

```text
YOLO Pose
```

## Temporal Classification

```text
Temporal Convolutional Network (TCN)
```

Input:

```text
Human Pose Keypoint Sequences
```

Output:

```text
Normal Activity
or
Fall Event
```

---

# Project Structure

```text
AIoT-Fall-Detection-System/
│
├── AI_Training/
│   ├── configs/
│   ├── datasets/
│   ├── features/
│   ├── lstm/
│   ├── realtime/
│   ├── scripts/
│   └── yolo/
│
├── dashboard/
│   ├── static/
│   ├── templates/
│   ├── app.py
│   ├── auth.py
│   ├── mail.py
│   └── security.py
│
├── services/
│   ├── camera_thread.py
│   ├── event_manager.py
│   ├── local_storage.py
│   ├── telegram_service.py
│   ├── firebase_service.py
│   └── esp32_service.py
│
├── recorded_videos/
│
├── shared_camera.py
├── main.py
├── mainAI.py
├── requirements.txt
└── README.md
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/TBL251/AIoT-Fall-Detection-System.git

cd AIoT-Fall-Detection-System
```

---

## Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# FFmpeg Installation

FFmpeg is required for:

* MP4 generation
* H264 encoding
* Telegram-compatible playback

Download:

https://ffmpeg.org/download.html

Verify installation:

```bash
ffmpeg -version
```

---

# Environment Variables

Create a `.env` file:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_CHAT_ID

MAIL_USERNAME=YOUR_EMAIL
MAIL_PASSWORD=YOUR_EMAIL_PASSWORD

FIREBASE_CREDENTIALS=YOUR_FIREBASE_JSON
```

---

# Dataset Preparation

Run:

```bash
python mainAI.py
```

Choose:

```text
1. Extract & Build Dataset
```

Pipeline:

```text
Extract UR Dataset
        ↓
Extract Le2i Dataset
        ↓
Build Dataset
        ↓
Merge Dataset
```

---

# Model Training

Run:

```bash
python mainAI.py
```

Choose:

```text
2. Train Model
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

Example camera configuration:

```python
CAMERA_INDEX = 0
```

Use the index corresponding to your USB camera.

---

# Video Storage Structure

```text
recorded_videos/

└── user_email/
    ├── Minor/
    ├── Dangerous/
    └── Critical Emergency/
```

Example:

```text
recorded_videos/

└── tbl251_gmail_com/
    └── Dangerous/
        └── event_20260531_200412.mp4
```

---

# Technologies Used

* Python
* OpenCV
* YOLO Pose
* TensorFlow
* TCN
* Flask
* Flask-SocketIO
* Firebase
* Telegram Bot API
* FFmpeg
* ESP32

---

# Security Features

* Password Hashing
* Email Encryption
* OTP Verification
* Session Management
* Protected Dashboard Access

---

# Future Improvements

* Multi-person fall detection
* TensorRT optimization
* Edge AI deployment
* Mobile application
* Healthcare analytics dashboard
* Cloud AI inference

---

# License

MIT License

---

# Author

TBL251

GitHub:

https://github.com/TBL251/AIoT-Fall-Detection-System
