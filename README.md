# 👁️ GuidedVision – VLM-Powered Safety Assistant

GuidedVision is an assistive system for visually impaired users that uses a **Vision-Language Model (VLM)** to:

- Watch the scene through a camera (laptop webcam or Raspberry Pi camera).
- Describe **in one short sentence** what it sees.
- Classify whether the scene contains **danger**.
- If there is danger, speak a loud alert:
  > WATCH OUT! DANGER <description>
- If there is no danger, it **only prints** the description in the terminal (no speech).

Special logic is used for **vehicles**: they are considered dangerous **only if they are coming towards the user**, not if they are parked or moving away.

---

## ✨ Features

- 🔍 **Scene Description**  
  One concise sentence describing main objects, people, and vehicles, with:
  - Relative position: `front`, `left`, `right`, `behind`.
  - Approximate distance in meters (when possible).

- 🚨 **Danger Detection**
  - Detects hazardous concepts such as:
    - Knives, blades, sharp edges
    - Fire, flames, smoke
    - Exposed cables/wires
    - Holes, pits, stairs, obstacles
  - **Vehicles** are treated specially:
    - 🚗 **Danger** only when the vehicle is *coming towards* the camera/user.
    - Parked or moving away → **no danger warning**.

- 🔊 **Audio Alerts (Client side)**
  - On danger: speaks  
    `WATCH OUT! DANGER <model description>`
  - On safe scenes: **no speech**, just prints text.

- 🧠 **VLM Backend**
  - Uses [HuggingFaceTB/SmolVLM-256M-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct).
  - Runs via **FastAPI** server.
  - Uses **CPU by default**, automatically uses **GPU** if available.

- 🔌 **Modular Client–Server Architecture**
  - `server/` hosts the VLM inference API.
  - `client_pi/` runs on laptop or Raspberry Pi, captures frames, sends them to server, and handles TTS.

---

## 🗂️ Project Structure

```text
Guided_Vision/
├─ server/
│  ├─ main.py          # FastAPI app, /analyze_frame endpoint
│  ├─ vlm_service.py   # VLM loading, caption generation, danger detection
│  └─ ... (other server files)
│
├─ client_pi/
│  ├─ pi_client.py     # Camera loop, HTTP client, TTS, terminal output
│  ├─ config.yaml      # Client configuration (camera, server URL, etc.)
│  ├─ tts.py
│  └─ ... (other client files)
|
├─ config.yaml
├─ requirements_pi.txt
├─ requirements_server.txt
│
└─ README.md           # This file
```

---

## ⚙️ Requirements

### Python

- Python **3.10+** is recommended.

### Server (VLM backend)

Python packages (defined in `server/requirements_server.txt`):

- `fastapi`
- `uvicorn[standard]`
- `pillow`
- `torch`
- `transformers`
- `accelerate`
- `safetensors`
- `numpy`

### Client (Laptop / Raspberry Pi)

Python packages (defined in `client_pi/requirements_pi.txt`):

- `opencv-python`
- `requests`
- `PyYAML`

### TTS (Operating System)

- **Windows**: uses PowerShell + `System.Speech.Synthesis.SpeechSynthesizer`.
- **Linux / Raspberry Pi**: uses `espeak` (must be installed via package manager, e.g. `sudo apt install espeak`).

---

## 🚀 Quickstart (Local Laptop Setup)

### 1. Clone the repository

```bash
git clone <your-repo-url>.git
cd Guided_Vision
```

### 2. Create & activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

From the project root (`Guided_Vision/`):

```bash
# Server deps
pip install -r server/requirements_server.txt

# Client deps
pip install -r client_pi/requirements_pi.txt
```

---

## 🧩 Configuration (`client_pi/config.yaml`)

`client_pi/config.yaml` controls how the client behaves:

```yaml
# Where the Raspberry Pi / laptop client sends frames
server_url: "http://127.0.0.1:8000"

# Camera device index on the client machine
camera_index: 0

# Width of the frame sent to the server (height is proportional)
send_width: 480

# JPEG quality for the frame upload (1–100)
jpeg_quality: 50

# HTTP timeout for each /analyze_frame request (seconds)
request_timeout_sec: 15.0

# Delay between frames sent from the client (seconds)
frame_interval_sec: 3.0

# Currently unused in the simplest client, but kept for future throttling
min_alert_interval_sec: 5.0

# Set to true if you want an OpenCV preview window on the client
show_preview: false

# (Informational) VLM settings – actual model config is read on the server
vlm_model_id: "HuggingFaceTB/SmolVLM-256M-Instruct"
vlm_device: "auto"
vlm_max_new_tokens: 64
```

For **local testing on the same machine**:

- Keep `server_url: "http://127.0.0.1:8000"`.

For **Raspberry Pi + separate server**:

- Set `server_url` to the server’s IP, e.g.:  
  `server_url: "http://192.168.1.10:8000"`

---

## 🧠 Server – How It Works

`server/main.py` exposes:

### `POST /analyze_frame`

- **Input**: an image file (`frame.jpg`) sent via `multipart/form-data`.
- **Process**:
  1. `vlm_service.generate_caption(image_bytes)`
     - Uses SmolVLM to produce **one-sentence** scene description.
     - Prompt encourages:
       - Main objects and people.
       - Left/right/front/behind.
       - Approximate distance in meters.
       - Clear phrases for vehicle behavior, e.g. “coming towards you”.
  2. `vlm_service.is_dangerous(description)`
     - Checks for:
       - Non-vehicle hazards (knife, fire, smoke, exposed cables, holes, stairs, obstacles, etc.).
       - Vehicles as danger **only when** they are *coming towards* the user.
- **Response JSON**:

```json
{
  "is_danger": true,
  "message": "A large fire in front of you about two meters away",
  "raw_caption": "A large fire in front of you about two meters away",
  "warning": "WATCH OUT! DANGER A large fire in front of you about two meters away",
  "latency_ms": 1234.56
}
```

- When `is_danger` is `false`, `warning` is `null`.

---

## 🎛️ Client – How It Works

`client_pi/pi_client.py`:

1. Reads `config.yaml`.
2. Opens the camera (`cv2.VideoCapture(camera_index)`).
3. Every `frame_interval_sec` seconds:
   - Captures a frame.
   - Resizes to `send_width`.
   - JPEG-encodes and sends to `POST /analyze_frame`.
4. Receives JSON from the server:
   - Prints the caption to the terminal:

     ```text
     [GuidedVision] Caption: 'A girl wearing a hijab and glasses in front of you about one meter away' (danger=False)
     ```

   - If `is_danger == True`:
     - Builds a spoken message:

       ```text
       WATCH OUT! DANGER <caption>
       ```

     - Calls OS-level TTS (PowerShell on Windows or `espeak` on Linux/Pi).
   - If `is_danger == False`:
     - Only prints the caption; **no speech**.

---

## 🧪 Running the System

### 1. Start the server

From `Guided_Vision/`:

```bash
# Activate venv first
# Windows:
# .\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

cd server
uvicorn main:app --host 0.0.0.0 --port 8000
```

You’ll see log lines like:

```text
[SERVER] Caption: 'A large fire in front of you about two meters away'  (danger=True)
```

### 2. Start the client

In a second terminal:

```bash
cd Guided_Vision
# Activate venv again in this terminal
cd client_pi
python pi_client.py
```

Example client output:

```text
[GuidedVision] Caption: 'A large fire in front of you about two meters away' (danger=True)
[GuidedVision] SPEAK: WATCH OUT! DANGER A large fire in front of you about two meters away
[GuidedVision][TTS] speak() called with: 'WATCH OUT! DANGER A large fire in front of you about two meters away'
```

- On a *safe* scene:

  ```text
  [GuidedVision] Caption: 'A girl wearing a hijab and glasses standing to the left about one meter away' (danger=False)
  ```

  → no speech.

---

## 🧱 Danger Logic Summary

- **Always dangerous** when description mentions:
  - Knife, knives, blade, sharp edge(s), scissors, sharp
  - Fire, flames, smoke
  - Cables, wires, exposed cables
  - Stairs, steps, holes, pits, obstacles

- **Vehicles** (`car`, `bus`, `truck`, `bike`, etc.) are dangerous **only if** the description also contains phrases such as:
  - "coming towards you", "coming toward you"
  - "approaching you", "heading towards you"
  - "coming towards the camera", "moving towards the camera", etc.

Everything is based on the **natural language caption**, which keeps the system flexible and model-agnostic.

---

## 🙏 Acknowledgements

- [HuggingFaceTB/SmolVLM-256M-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct) for the lightweight vision-language model.
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/index)
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenCV](https://opencv.org/)

---

## 📄 License

This project was done for EECE490: Introduction to Machine Learning at the American University of Beirut under the supervision of Prof. Ammar Mohanna.
Members of the Team: Aya El Hajj, Batoul Hachem, and Joud Senan
