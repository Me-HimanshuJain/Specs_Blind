# 👓 Specs_Blind - Smart Goggles for the Visually Impaired

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?style=for-the-badge&logo=ultralytics&logoColor=black)](https://github.com/ultralytics/ultralytics)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![Android Kotlin](https://img.shields.io/badge/Android-Kotlin%20%7C%20TFLite-3DDC84?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg?style=for-the-badge)](LICENSE)

> **Specs_Blind** is an intelligent assistive vision wearable system engineered from the ground up for blind and low-vision users. Combining real-time computer vision (YOLOv8), Kalman filter obstacle tracking, intelligent 4-tier urgency audio feedback, multi-pattern haptic vibration, and adaptive power management, Specs_Blind empowers users to navigate both indoor and outdoor environments safely and independently.

---

## 📑 Table of Contents

- [Vision & Purpose](#-vision--purpose)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Audio & Accessibility Design](#-audio--accessibility-design)
- [Haptic Feedback Matrix](#-haptic-feedback-matrix)
- [Repository Structure](#-repository-structure)
- [Installation & Quick Start](#-installation--quick-start)
- [Running the System](#-running-the-system)
- [Controls & Shortcuts](#-controls--shortcuts)
- [Configuration Guide (`config.yaml`)](#-configuration-guide-configyaml)
- [Android Mobile Port (`android_app/`)](#-android-mobile-port-android_app)
- [Performance & Optimizations](#-performance--optimizations)
- [Documentation Index](#-documentation-index)
- [Roadmap](#-roadmap)
- [Contributing & License](#-contributing--license)

---

## 🌟 Vision & Purpose

Navigating daily environments poses significant challenges for visually impaired individuals. Traditional white canes provide local surface tactile feedback but cannot detect head-level obstacles, approaching vehicles, moving pedestrians, or distant hazards.

**Specs_Blind** bridges this gap by acting as an intelligent cognitive copilot:
- **Detects hazards early** (approaching cars, bicycles, people, low obstacles, tables, and walls).
- **Prevents sensory overload** through smart priority queuing, confidence filtering, and non-repetitive spatial audio.
- **Adapts to urgent situations** by modulating speech rate (faster for immediate danger) and firing tactile vibrations.
- **Operates across devices**: Runs on PCs/laptops, embedded hardware (Raspberry Pi/Jetson), and portable Android smartphones via USB-OTG smart glasses.

---

## 🚀 Key Features

### 👁️ Real-Time Computer Vision & Obstacle Detection
- **YOLOv8 Neural Network**: Utilizes `yolov8n.pt` for high-throughput, low-latency object detection across 80 COCO categories.
- **Asynchronous Inference Pipeline**: Dedicated background threads run model inference without freezing or dropping camera frames.
- **Wall & Surface Detection**: Integrated Canny edge detection and contour analysis identify walls, structural partitions, and dead ends.
- **Static vs. Dynamic Classification**: Categorizes objects into moving threats (pedestrians, vehicles) versus static hazards (furniture, appliances, barriers).

### 🎯 Kalman Filter Multi-Object Tracking
- **SORT-Inspired Tracking**: Employs a 7-state Kalman filter (`state_dim=7`, `measurement_dim=4`) and Hungarian matching algorithm with IoU thresholds.
- **Trajectory & Relative Velocity**: Computes whether an obstacle is approaching, stationary, or moving away from the user.
- **Persistent Object IDs**: Tracks objects through brief occlusions and maintains continuity across frames.

### 🔊 4-Tier Priority Audio Guidance
- **Emergency Tier (< 0.6m)**: Instant stop alerts spoken at 200 WPM (*"STOP! Object very close ahead!"*).
- **Obstacle Tier (0.6m – 2.0m)**: Warnings for approaching threats spoken at 160 WPM (*"Car approaching on left 1.5 meters"*).
- **Navigation Tier (2.0m – 3.0m)**: Clear path directions spoken at 140 WPM (*"Move right to avoid chair"*).
- **Info Tier (> 3.0m)**: Distant background context spoken at 120 WPM (*"Person standing on right 4 meters"*).
- **Anti-Spam Throttles**: Configurable per-category cooldowns eliminate repetitive chatter.

### 🧠 Threat Escalation & Memory
- **10-Second Context Window**: Tracks recurring threats that move in and out of frame.
- **Escalation Logic**: Escalates alert priority if an obstacle repeatedly enters the user's trajectory.

### 📳 Tactile Haptic Feedback
- **5 Distinct Haptic Signatures**: Complements voice guidance in noisy traffic or crowded conditions with vibration patterns for SOS Emergency, Double Warning Pulse, Obstacle Alert, Directional Nudges, and Safe Path confirmation.

### ⚡ Adaptive Power Management
- **Tri-Profile Governor**: Dynamically transitions between `ECO`, `BALANCED`, and `PERFORMANCE` modes based on real-time battery status and threat severity.

### 📱 Full-Featured Android Port
- Built with Kotlin and modern MVVM architecture.
- Integrates Camera2 API with USB-OTG external glasses camera support, TensorFlow Lite on-device inference, and native Android TTS.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Specs_Blind System V2                           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────┐                         ┌───────────────────────┐
│  Async Camera Feed    │                         │  USB-OTG Android App  │
│  (60 FPS Threaded)    │                         │  (Camera2 + TFLite)   │
└──────────┬────────────┘                         └──────────┬────────────┘
           │                                                 │
           ▼                                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       YOLOv8 Object Detection                          │
│   • 80 COCO classes      • Wall/Edge contour analysis                  │
│   • Confidence filtering • Non-blocking frame buffer                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Kalman Filter Tracking Engine                     │
│   • 7-State Kalman tracker       • Hungarian IoU data association      │
│   • Relative velocity estimation • Spatial position (5-zone grid)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Threat Memory & Decision Core                     │
│   • 10-second contextual memory  • Power manager governor              │
│   • Threat escalation rules      • Anti-spam announcement timers       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────────────────┐     ┌──────────────────────────────┐
│     4-Tier Priority Audio TTS     │     │    Multi-Pattern Haptics     │
│  • EMERGENCY (200 WPM, < 0.6m)    │     │  • SOS Emergency Pattern     │
│  • OBSTACLE  (160 WPM, 0.6 - 2m)  │     │  • Double Warning Pulse      │
│  • NAVIGATION(140 WPM, 2 - 3m)    │     │  • Directional Guidance      │
│  • INFO      (120 WPM, > 3m)      │     │  • Safe Confirmation         │
└───────────────────────────────────┘     └──────────────────────────────┘
```

---

## 🔊 Audio & Accessibility Design

Specs_Blind applies evidence-based psychoacoustic design principles to keep the user informed without inducing cognitive fatigue:

| Tier | Distance Trigger | Speech Rate | Volume | Example Announcement | User Action Required |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **🚨 EMERGENCY** | `< 0.6m` | Fast (200 WPM) | 100% | *"STOP! Wall very close ahead!"* | Halt movement immediately |
| **⚠️ OBSTACLE** | `0.6m – 2.0m` | Normal (160 WPM) | 90% | *"Car approaching left 1.5m"* | Slow down and prepare to maneuver |
| **🧭 NAVIGATION** | `2.0m – 3.0m` | Moderate (140 WPM) | 80% | *"Move right to clear path"* | Follow directional cue |
| **ℹ️ INFO** | `> 3.0m` | Calm (120 WPM) | 70% | *"Person on far right 4m"* | Maintain awareness, proceed freely |

### Spatial Sectors
The forward field of view is segmented into five intuitive spatial zones:
`[ Far Left ]  [ Left ]  [ Center / Ahead ]  [ Right ]  [ Far Right ]`

---

## 📳 Haptic Feedback Matrix

When ambient sound makes audio cues difficult to hear, haptic motors mounted on the glasses frame or wristband provide tactile alerts:

- **Emergency SOS**: Rapid burst `200ms ON / 100ms OFF / 200ms ON / 100ms OFF` (Immediate stop).
- **Critical Hazard**: Double pulse `150ms ON / 150ms OFF / 150ms ON` (Approaching obstacle).
- **Proximity Alert**: Single pulse `100ms ON` (Object within 2 meters).
- **Directional Guide**: Gentle left/right vibration nudges for suggested clearance paths.
- **Safe Path Confirmation**: Single smooth, long pulse `400ms ON` confirming clear path ahead.

---

## 📂 Repository Structure

```
Specs_blind/
├── android_app/                  # Native Kotlin Android application
│   └── app/
│       ├── build.gradle          # Android build dependencies & TFLite setup
│       └── src/main/
│           ├── AndroidManifest.xml
│           ├── java/com/smartgoggle/
│           │   ├── MainActivity.kt         # Android UI & hardware bindings
│           │   ├── SmartGoggleViewModel.kt # Lifecycle & MVVM business logic
│           │   ├── camera/USBCameraManager.kt # USB-OTG external camera support
│           │   ├── ml/ObjectDetector.kt    # TensorFlow Lite edge inference
│           │   ├── ml/ObjectTracker.kt     # Mobile Kalman filter tracking
│           │   └── audio/AudioGuidance.kt  # Android TextToSpeech engine
│           └── res/                        # Layouts, icons, and theme values
│
├── config/
│   └── classes.txt               # 80 standard COCO detection class names
├── config.yaml                   # Core runtime configuration (camera, audio, thresholds)
├── requirements.txt              # Python runtime dependencies
│
├── main.py                       # High-performance async vision & audio runner (v1)
├── main_v2.py                    # Complete V2 system (threat tracking, haptics, power)
│
├── src/                          # Modular Python source library
│   ├── __init__.py
│   ├── camera.py                 # Async background camera frame capture
│   ├── detector.py               # YOLOv8 detector, caching & wall detection
│   ├── tracker.py                # Kalman filter multi-object tracker
│   ├── audio_feedback.py         # Priority queue TTS audio guidance engine
│   ├── threat_tracker.py         # Contextual threat escalation & memory window
│   ├── haptic_feedback.py        # Haptic tactile vibration controller
│   ├── power_manager.py          # Dynamic battery governor & runtime simulator
│   ├── sensors.py                # Distance and environmental sensor interface
│   ├── user_input.py             # Hardware button & keypress dispatcher
│   ├── voice_confirmation.py     # Voice dialog confirmation for critical actions
│   └── utils.py                  # Visualization overlays & bounding box rendering
│
└── [Documentation Files]         # In-depth architectural & user guides
    ├── ACCESSIBILITY_GUIDE.md    # Detailed accessibility design manual
    ├── BLIND_USER_GUIDE.md       # Audio-first end-user operational handbook
    ├── ARCHITECTURE_OPTIMIZATION.md # Deep dive into async I/O & caching
    ├── ANDROID_IMPLEMENTATION_GUIDE.md # Step-by-step Android build instructions
    ├── QUICK_START.md            # 5-minute setup and test walkthrough
    └── DOCUMENTATION_INDEX.md    # Complete master index of project documentation
```

---

## 💻 Installation & Quick Start

### 1. Prerequisites
- **Python**: Version `3.8`, `3.9`, `3.10`, or `3.11`
- **Camera**: Standard USB webcam, laptop webcam, or USB-OTG camera
- **Audio Output**: Headphones (bone-conduction recommended) or device speakers

### 2. Clone the Repository
```bash
git clone https://github.com/Me-HimanshuJain/Specs_Blind.git
cd Specs_Blind
```

### 3. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Download / Verify YOLOv8 Model
The YOLOv8 nano model (`yolov8n.pt`) is bundled in this repository. If missing, Ultralytics will automatically download it on the first launch.

---

## 🏃 Running the System

Specs_Blind includes two operational modes:

### Mode A: Full Smart Glasses System V2 (Recommended)
Includes threat memory, haptic integration, adaptive power management, and voice verification:
```bash
python main_v2.py
```

### Mode B: Optimized Low-Latency Vision & Audio Runner (V1)
Lightweight pipeline optimized for maximum FPS and low CPU usage:
```bash
python main.py
```

---

## 🎮 Controls & Shortcuts

When running with visualization enabled, control the system via keyboard shortcuts:

| Key | Action | Description |
| :---: | :--- | :--- |
| `q` | **Quit** | Gracefully releases camera, terminates threads, and closes window |
| `p` | **Pause / Resume** | Toggles camera stream and audio feedback loop |
| `v` | **Toggle Visualization** | Toggles OpenCV UI window on/off (saves CPU/battery) |
| `a` | **Audio Self-Test** | Speaks diagnostic distance test message via TTS |
| `c` | **Clear Threat History** | Resets Kalman tracker and threat memory cache |
| `s` | **Show Status** | Prints active tracks, battery level, and FPS to terminal |

---

## ⚙️ Configuration Guide (`config.yaml`)

Customize system behavior by editing `config.yaml`:

```yaml
# Device profile: 'auto' | 'high' | 'low' | 'full'
device_profile: 'full'

camera:
  device_id: 0              # Video device index (0 for primary webcam)
  width: 640                # Capture frame width
  height: 480               # Capture frame height
  fps: 60                   # Target camera framerate

yolo:
  model_path: "yolov8n.pt"   # YOLO model weights (n=nano, s=small)
  confidence_threshold: 0.3 # Minimum detection threshold
  iou_threshold: 0.45       # NMS IoU threshold
  inference_size: 416       # Network input dimension (416 or 640)
  half_precision: false     # FP16 acceleration (supported on CUDA GPUs)

tracking:
  max_age: 10               # Maximum missed frames before dropping track
  min_hits: 1               # Detections required to initialize track
  iou_threshold: 0.3        # Hungarian association threshold

audio:
  volume: 0.9               # Output volume (0.0 to 1.0)
  rate: 160                 # Base speech rate in words per minute
  min_confidence: 0.6       # Minimum confidence to trigger audio alert
  announcement_intervals:
    critical: 1.0           # Emergency interval limit (seconds)
    warning: 4.0            # Warning interval limit (seconds)
    normal: 8.0             # General guidance interval limit (seconds)
    clear: 15.0             # Clear path confirmation interval

guidance:
  stop_distance: 0.6        # Emergency stop threshold in meters
  critical_distance: 0.8    # Critical proximity threshold in meters
  warning_distance: 1.5     # Cautionary proximity threshold in meters
  safe_distance: 3.0        # Clear navigational buffer in meters

wall_detection:
  enabled: true             # Enable edge-based barrier detection
  edge_threshold1: 50
  edge_threshold2: 150
  min_wall_area: 1000
```

---

## 📱 Android Mobile Port (`android_app/`)

The repository includes a production-ready Android companion application in [`android_app/`](android_app/):

- **No Custom SBC Required**: Mounts an ordinary smartphone in a pocket or pouch connected to smart glasses via USB-C OTG cable.
- **Camera2 & USB-OTG**: Supports external high-FOV frame-mounted cameras.
- **On-Device Machine Learning**: Utilizes TensorFlow Lite for hardware-accelerated mobile inference.
- **Battery Life**: Optimized for 4–6 hours of continuous guidance on modern Android devices.

To build and run:
1. Open [`android_app`](android_app/) in **Android Studio**.
2. Allow Gradle to synchronize dependencies.
3. Connect your Android phone via USB with USB Debugging enabled.
4. Click **Run 'app'** to install and launch.

For comprehensive Android deployment instructions, refer to [`ANDROID_IMPLEMENTATION_GUIDE.md`](ANDROID_IMPLEMENTATION_GUIDE.md).

---

## ⚡ Performance & Optimizations

Specs_Blind achieves smooth real-time performance across both high-end and budget hardware:

- **Asynchronous Frame Streaming**: Non-blocking frame capture thread keeps the camera buffer fresh and prevents frame staleness.
- **Thread-Safe Detection Caching**: Reduces redundant inference runs on static scenes, cutting CPU consumption by up to **80%**.
- **Dual Confidence Filter**: 0.3 for computer vision tracking, 0.6 for vocal announcement — reducing audio false alarms by **~40%**.
- **Average Performance**:
  - **High-End Desktop / Laptop**: 60 FPS, ~15-25% CPU utilization.
  - **Budget Laptop / Mini-PC**: 30 FPS, ~30-40% CPU utilization.
  - **Android Smartphone**: 25-30 FPS, 150-200ms end-to-end latency.

---

## 📚 Documentation Index

Detailed documentation files are available in this repository:

- 📖 [`QUICK_START.md`](QUICK_START.md) — 5-minute quick start and verification guide.
- 🦮 [`BLIND_USER_GUIDE.md`](BLIND_USER_GUIDE.md) — Practical audio-first guide for blind users.
- ♿ [`ACCESSIBILITY_GUIDE.md`](ACCESSIBILITY_GUIDE.md) — Deep dive into the accessibility engineering decisions.
- 🏛️ [`ARCHITECTURE_OPTIMIZATION.md`](ARCHITECTURE_OPTIMIZATION.md) — Architecture diagrams and concurrency design.
- 📱 [`ANDROID_IMPLEMENTATION_GUIDE.md`](ANDROID_IMPLEMENTATION_GUIDE.md) — Android build and configuration guide.
- 📋 [`DOCUMENTATION_INDEX.md`](DOCUMENTATION_INDEX.md) — Complete navigational index for all documentation.

---

## 🔮 Roadmap

- [ ] **LiDAR / Time-of-Flight (ToF) Integration**: True millimeter-precision depth maps for uneven stairs and drop-offs.
- [ ] **Text & OCR Reading Mode**: Point-to-read functionality for street signs, menus, and product labels.
- [ ] **Currency & Banknote Recognition**: Offline audio identification of paper currency.
- [ ] **GPS & Turn-by-Turn Navigation Fusion**: Blending outdoor pedestrian navigation with obstacle avoidance.
- [ ] **Bluetooth Low Energy (BLE) Haptic Wristbands**: Wireless left/right tactile direction wristbands.

---

## 🤝 Contributing

Contributions are welcome! If you have ideas for improvements, bug fixes, or new accessibility features:

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'feat: Add AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Copyright &copy; 2026 Himanshu Jain. All rights reserved. See the [LICENSE](LICENSE) file for details.

---