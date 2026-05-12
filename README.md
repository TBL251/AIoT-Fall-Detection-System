# AIoT Fall Detection & ICU Monitoring System

An intelligent AIoT-based ICU patient monitoring and fall detection system using Artificial Intelligence, Computer Vision, IoT, Firebase, Telegram, and ESP32.

---

# System Features

## AI Fall Detection

* Human pose detection
* Real-time fall detection
* ICU monitoring logic
* Risk score analysis
* Severity classification

### Severity Levels

| Level | Description        |
| ----- | ------------------ |
| 1     | Minor Fall         |
| 2     | Dangerous Fall     |
| 3     | Critical Emergency |

---

# ICU Monitoring Engine

The system continuously monitors patient posture and movement.

### ICU State Machine

```text
NORMAL
   ↓
UNBALANCED
   ↓
FALLING
   ↓
LYING_MONITORING
   ↓
CRITICAL ALERT
```

### Risk Score System

* Dynamic risk scoring
* Continuous monitoring
* Automatic recovery detection
* Cooldown protection

---

# Realtime Dashboard

Modern production-style dashboard with:

* Realtime monitoring
* Live statistics
* Live risk analysis
* Realtime charts
* Event replay
* User management

---

# Dashboard Pages

## Dashboard

Main overview page including:

* Weekly fall chart
* Live status cards
* Risk indicators
* Quick navigation

---

## Live Monitoring

Realtime ICU monitoring interface:

* Live camera feed
* Patient state
* Risk score
* Fall prediction
* Emergency level

---

## Replay Center

Automatically loads videos from:

```bash
recorded_videos/
```

Replay features:

* Severity filtering
* Video playback
* Event history
* Timestamp tracking

---

## Charts

Realtime analytics page:

* Weekly statistics
* Severity comparison
* Historical data
* Dynamic charts

---

## Profile

Displays user information:

* Full name
* Email
* Date of birth
* Account information

---

# Authentication System

## Register

Features:

* OTP email verification
* Password confirmation
* Secure account creation
* User folder creation

### Registration Fields

* Full name
* Date of birth
* Email
* Password
* Confirm password
* OTP verification

---

## Login

Features:

* Password hashing
* Session authentication
* Show/hide password
* Auto redirect

---

## Logout

Features:

* Session cleanup
* Automatic redirect
* User state reset

---

# Realtime Communication

Built using:

* Flask-SocketIO
* Event streaming
* Live updates
* Instant synchronization

---

# Telegram Alert System

Automatically sends:

* Emergency alerts
* Fall notifications
* Event videos
* Critical warnings

---

# ESP32 Alarm System

ESP32 buzzer supports multiple emergency levels.

| Level | Alarm Type       |
| ----- | ---------------- |
| 0     | OFF              |
| 1     | Slow Beep        |
| 2     | Fast Beep        |
| 3     | Continuous Alarm |

---

# Firebase Integration

Stores:

* Fall events
* Severity level
* Video paths
* Timestamps
* Realtime logs

---

# Project Structure

```bash
AIoT-Fall-Detection-System/
│
├── ai_detection/
│   ├── pipeline.py
│   ├── pose_detector.py
│   ├── fall_detector.py
│   └── severity_estimator.py
│
├── dashboard/
│   ├── app.py
│   ├── auth.py
│   ├── mail.py
│   ├── otp_store.py
│   ├── security.py
│   ├── users.json
│   │
│   ├── .env
│   │
│   └── templates/
│       ├── layout.html
│       ├── login.html
│       ├── register.html
│       ├── dashboard.html
│       ├── charts.html
│       ├── replay.html
│       ├── live.html
│       └── profile.html
│
├── services/
│   ├── .env
│   ├── shared_state.py
│   ├── local_storage.py
│   ├── firebase_service.py
│   ├── telegram_service.py
│   ├── esp32_service.py
│   └── event_manager.py
│
├── recorded_videos/
│
├── main.py
├── requirements.txt
└── README.md
```

---

# Environment Files

The system uses 2 separate `.env` files.

---

## dashboard/.env

Used for:

* OTP email system
* Flask secret keys
* Dashboard security

Example:

```env
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
SECRET_KEY=your_secret_key
```

---

## services/.env

Used for:

* Telegram bot
* Firebase
* ESP32 services

Example:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_CHAT_ID

FIREBASE_KEY=firebase_key.json
DATABASE_URL=https://your-project.firebaseio.com/
```

---

# Installation

## 1. Clone Project

```bash
git clone <your-repository>
cd AIoT-Fall-Detection-System
```

---

# 2. Create Virtual Environment

## Windows

```bash
python -m venv venv
venv\Scripts\activate
```

## Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

# 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

# 4. Configure Environment Variables

Create:

```bash
dashboard/.env
services/.env
```

---

# 5. Run Dashboard

```bash
python dashboard/app.py
```

Open browser:

```text
http://127.0.0.1:5000
```

---

# 6. Run AI Monitoring System

Open another terminal:

```bash
python main.py
```

---

# Recorded Videos

Videos are automatically stored by:

* user
* severity
* timestamp

Example:

```bash
recorded_videos/
└── user_gmail_com/
    ├── Minor/
    ├── Dangerous/
    └── Critical Emergency/
```

---

# Technologies Used

* Python
* Flask
* Flask-SocketIO
* OpenCV
* MediaPipe
* Firebase
* Telegram Bot API
* ESP32
* HTML
* CSS
* JavaScript

---

# Security Features

* Password hashing
* OTP verification
* Email encryption
* Secure session login
* Protected routes

---

# Future Improvements

* YOLO-based detection
* Cloud deployment
* Multi-camera support
* Mobile application
* AI prediction system
* Medical analytics
* Doctor notification system
* Edge AI optimization

---

# System Workflow

```text
Camera
   ↓
AI Detection
   ↓
Risk Analysis
   ↓
ICU Decision Engine
   ↓
Alert System
   ├── Dashboard
   ├── Firebase
   ├── Telegram
   └── ESP32 Alarm
```

---

# Author

AIoT ICU Monitoring & Fall Detection System

Built using AI + IoT + Computer Vision + Realtime Monitoring.
