# AIoT Fall Detection System

An AI-powered IoT Fall Detection and Emergency Monitoring System for elderly care, patient monitoring, and smart healthcare environments.

The system combines Computer Vision, Deep Learning, IoT devices, Cloud Services, and Real-Time Notifications to detect falls, classify emergency severity, record incidents, and notify caregivers instantly.

---

## Features

### Real-Time Fall Detection

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

### Smart Emergency Recording

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

### Telegram Emergency Alert

When a fall occurs:

* Telegram notification is sent instantly
* Emergency severity is included
* Event video is uploaded automatically
* Recovery notification is sent on patient stabilization

---

### ESP32 Emergency Alarm

ESP32 integration supports:

* Buzzer alarm with severity-based patterns
* Serial communication (configurable port via `ESP32_PORT` env var)
* Emergency level synchronization (0 = Normal, 1 = Minor, 2 = Dangerous, 3 = Critical)
* Hardware safety auto-stop timeout (10 s failsafe)

---

### Flask Dashboard

Web-based monitoring dashboard:

* User Login / Registration
* OTP Verification
* Live Camera Monitoring (authenticated access only)
* Real-Time AI Status
* Replay Recorded Videos
* Statistics Dashboard
* User Profile Management

---

### Firebase Integration

Firebase is used for:

* Event Logging
* Cloud Synchronization
* Historical Data Storage
* Monitoring Analytics

---

## System Architecture

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
 ┌───┼──────────────────┐
 │   │                  │
 ▼   ▼                  ▼
ESP32  Telegram     Dashboard
Alarm  Alert       Live Stream
                       │
              ┌────────┘
              ▼
        Video Recording
```

---

## Dataset

The model is trained using two public fall detection datasets.

### UR Fall Detection Dataset

Contains:

* RGB videos
* Fall activities
* Activities of Daily Living (ADL)
* Multiple subjects
* Multiple viewpoints

Official Website:

https://fenix.ur.edu.pl/~mkepski/ds/uf.html

---

### Le2i Fall Detection Dataset

Contains:

* Indoor fall scenarios
* Daily activities
* Multiple fall types
* Various camera placements

Official Website:

https://www.le2i.cnrs.fr/Fall-detection-Dataset

---

## Dataset Pipeline

```text
UR Dataset          Le2i Dataset
     │                   │
     ▼                   ▼
Frame Extraction   Frame Extraction
     │                   │
     └─────────┬─────────┘
               ▼
      YOLO Pose Extraction
               ↓
      Feature Engineering
               ↓
         Merged Dataset
               ↓
          TCN Training
```

---

## AI Model

### Pose Estimation

```text
YOLO Pose
```

### Temporal Classification

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

## Project Structure

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
│   ├── esp32_service.py
│   ├── firebase_service.py
│   ├── local_storage.py
│   └── telegram_service.py
│
├── esp32/
│   └── buzzer.ino
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

## Installation

### Clone Repository

```bash
git clone https://github.com/TBL251/AIoT-Fall-Detection-System.git
cd AIoT-Fall-Detection-System
```

---

### Create Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## FFmpeg Installation

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

## Environment Variables

Create a `.env` file in the project root:

```env
# Flask
SECRET_KEY=YOUR_SECRET_KEY

# Telegram
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_CHAT_ID

# Email (OTP)
MAIL_USERNAME=YOUR_EMAIL
MAIL_PASSWORD=YOUR_EMAIL_PASSWORD

# Firebase
FIREBASE_CREDENTIALS=YOUR_FIREBASE_JSON

# ESP32 (optional — defaults shown)
ESP32_PORT=COM5
ESP32_BAUD=115200
```

> **Note:** `ESP32_PORT` should be set to the correct serial port for your system (e.g. `/dev/ttyUSB0` on Linux, `/dev/cu.usbserial-*` on macOS).

---

## Dataset Preparation

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

## Model Training

Run:

```bash
python mainAI.py
```

Choose:

```text
2. Train Model
```

---

## Running the System

Start the full system (dashboard + AI engine) with a single command:

```bash
python main.py
```

The dashboard will be available at:

```text
http://127.0.0.1:5000
```

The browser opens automatically. The AI engine starts processing the camera feed once the dashboard is ready.

> **Note:** Do not run `dashboard/app.py` directly. It is started automatically by `main.py`.

Camera configuration (inside `main.py`):

```python
CAMERA_INDEX = 0   # change to match your USB camera index
```

---

## Video Storage Structure

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

## Technologies Used

* Python
* OpenCV
* YOLO Pose
* TensorFlow
* TCN
* Flask
* Flask-SocketIO
* Werkzeug
* PySerial
* Firebase Admin SDK
* Telegram Bot API
* FFmpeg
* ESP32 (Arduino)

---

## Security Features

* Password hashing (Werkzeug PBKDF2)
* Email encryption (stored encrypted at rest)
* OTP email verification on registration
* Flask session management with `HttpOnly` and `SameSite=Lax` cookies
* All dashboard routes and the live camera stream require authentication

---

## Future Improvements

* Multi-person fall detection
* TensorRT optimization
* Edge AI deployment
* Mobile application
* Healthcare analytics dashboard
* Cloud AI inference
* LED warning indicator on ESP32

---

## License

MIT License

---

## Author

TBL251

GitHub: https://github.com/TBL251/AIoT-Fall-Detection-System
