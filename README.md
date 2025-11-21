# 👁️ GuidedVision – VLM-Powered Safety Assistant

GuidedVision is an assistive system for visually impaired users that uses a **Vision-Language Model (VLM)** to:

- Watch the scene through a camera (laptop webcam or Raspberry Pi camera).
- Describe **in one short sentence** what it sees.
- Classify whether the scene contains **danger**.
- If there is danger, it speaks a loud alert:

  > "DANGER to your DIRECTION"

- If the scene is safe, it **prints the description** only (no speech).

---

## ✨ Features

- 🔍 **Scene Description**
  - One concise sentence describing everything in the frame.
  - Includes relative position: `front`, `left`, `right`.

- 🚨 **Danger Detection**
  Detects:
  - Knives, blades, sharp edges  
  - Fire, flames, smoke  
  - Exposed cables/wires  
  - Holes, pits, stairs, obstacles  

- 🔊 **Audio Alerts**
  - On danger:  
    `DANGER to your DIRECTION`
  - On safe scenes: **no speech**, only printed text.

- 🧠 **VLM Backend**
  - Uses `HuggingFaceTB/SmolVLM-256M-Instruct`
  - Works on CPU (GPU if available)

- 🔌 **Modular Client–Server Architecture**
  - `server/` = FastAPI + VLM inference  
  - `client_pi/` = camera capture + communication + TTS  

---

## 🗂️ Project Structure

```text
Guided_Vision/
├─ server/
│  ├─ main.py
│  ├─ vlm_service.py
│
├─ client_pi/
│  ├─ pi_client.py
│  ├─ config.yaml
│  ├─ tts.py
│
├─ frontend/
│  └─ index.html
│  └─ Dockerfile
│
├─ requirements_pi.txt
├─ requirements_server.txt
├─ docker-compose.yml
└─ Dockerfile
```

---

## ⚙️ Requirements

### **Option 1 – Native (Python)**

#### Python
Recommended: **Python 3.10+**

#### Server Dependencies

Defined in `server/requirements_server.txt`:

- fastapi  
- uvicorn  
- pillow  
- torch  
- transformers  
- accelerate  
- safetensors  
- numpy  
- python-multipart  

#### Client Dependencies

Defined in `client_pi/requirements_pi.txt`:

- opencv-python  
- requests  
- PyYAML  

#### TTS Requirements

- **Windows:** PowerShell `System.Speech`  
- **Linux / Raspberry Pi:** `espeak`

---

### **Option 2 – Docker (Backend + Frontend)**

- **Docker** (or Docker Desktop on Windows/macOS)  
- **Docker Compose** (included in recent Docker Desktop versions)

With Docker you don’t need to install Python dependencies locally; everything runs inside containers.

---

## 🚀 Quickstart (Laptop – Native Python)

### 1. Clone the repository
```bash
git clone https://github.com/Joud158/Guided_Vision.git
cd Guided_Vision
```

### 2. Create a virtual environment
```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r server/requirements_server.txt
pip install -r client_pi/requirements_pi.txt
```

---

## 🚢 Quickstart (Docker – Backend + Frontend)

> This spins up **both** the FastAPI backend and the web dashboard using Docker.

From the project root:

### 1. Build images (local)

```bash
# Backend (FastAPI + VLM)
docker build -t guided_vision-server:latest .

# Frontend (Nginx serving index.html)
docker build -t guided_vision-frontend:latest ./frontend
```

### 2. Start both services with Docker Compose

```bash
docker compose up
```

This will:

- Run the **backend** on port **8000**
- Run the **frontend dashboard** on port **4173**

### 3. Open in your browser

- Frontend dashboard: <http://127.0.0.1:4173>  
- Backend health check: <http://127.0.0.1:8000/> → should return `{"status": "ok"}`  
- Backend docs (optional): <http://127.0.0.1:8000/docs>

To stop everything:

```bash
docker compose down
```
---

## 🧩 Client Configuration (`client_pi/config.yaml`)

```yaml
server_url: "http://127.0.0.1:8000"  # for laptop version; change to Raspberry Pi IP if using the hardware
camera_index: 0
send_width: 480
jpeg_quality: 50
request_timeout_sec: 15.0
frame_interval_sec: 3.0
min_alert_interval_sec: 5.0
show_preview: false
vlm_model_id: "HuggingFaceTB/SmolVLM-256M-Instruct"
vlm_device: "auto"
vlm_max_new_tokens: 64
```

---

## 🧠 How the Server Works

`POST /analyze_frame`  
Receives image → captions → checks danger → returns:

```json
{
  "is_danger": true,
  "message": "Fire in front of you",
  "raw_caption": "Fire in front of you",
  "warning": "Fire to your front",
  "latency_ms": 1280
}
```

---

## 🎛️ How the Client Works

1. Reads config  
2. Captures frame  
3. Sends to server  
4. Prints caption  
5. Speaks alert if danger  

---

## 🧱 Danger Logic Summary

**Always dangerous** if caption mentions:  
`knife`, `blade`, `scissors`, `fire`, `flames`, `smoke`, `exposed cable`, `wire`, `hole`, `pit`, `stairs`, `obstacle`, etc.

---

# 🌐 Front-End Dashboard

We added a fully interactive web dashboard for GuidedVision, built using **HTML, CSS, and JavaScript**.

The dashboard runs locally in any browser and communicates with the FastAPI server at:

```text
http://127.0.0.1:8000
```

---

## 🔥 Dashboard Features

- Shows **live webcam preview**  
- Switch between:
  - **Laptop Mode:** Browser captures frames → sends to `/analyze_frame`
  - **Raspberry Pi Mode:** Refer to hardware implementation
- Displays:
  - Latest caption
  - Hazard level
  - Latency
  - Server status
- Browser speaks danger alerts using Web Speech API:

  `DANGER to your DIRECTION`

- Safe scenes: No audio, only text.

You can either:

- Open `frontend/index.html` directly in the browser (native mode), **or**
- Use the Dockerized dashboard via <http://127.0.0.1:4173> when running `docker compose up`.

---

## 🖥️ Start the Dashboard (Native Python Mode)

### 1. Start the VLM server
```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Open dashboard
```text
Guided_Vision/frontend/index.html
```

### 3. Choose mode  
Laptop Camera → Start Capture  
or  
Raspberry Pi Mode (refer to hardware implementation)

---

## 🙏 Acknowledgements

This project was developed for **EECE490: Introduction to Machine Learning** at  
**American University of Beirut** under the supervision of **Prof. Ammar Mohanna**.

Team Members:
- Aya El Hajj  
- Batoul Hachem  
- Joud Senan
