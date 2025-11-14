# Guided Vision (vLLM Edition)

Assistive system for blind/low-vision users. A Raspberry Pi 5 streams camera frames
to a server that runs:

- YOLO object detection (danger classes: cars, tools, cables, etc.)
- Simple distance & direction estimation
- A vLLM-powered language model that turns detections into short alerts, e.g.  
  `WATCH OUT! A CAR IS 2 METERS TO YOUR RIGHT.`

The Pi receives the text and speaks it out loud in real time.

---

## 1. Project layout

```text
guided_vision_vllm/
├── README.md
├── requirements_server.txt
├── requirements_pi.txt
├── models/
│   └── README_MODELS.txt
├── server/
│   ├── main.py
│   ├── detector.py
│   ├── distance_direction.py
│   └── reasoner_vllm.py
└── client_pi/
    ├── pi_client.py
    ├── tts.py
    └── config.yaml
```

- **server/** runs on a GPU laptop / desktop / cloud VM with vLLM installed.
- **client_pi/** runs on Raspberry Pi 5 (or your laptop for testing).
- **models/** holds your YOLO `.pt` weights.

---

## 2. Server setup (GPU machine with vLLM)

1. Create a virtual env and install dependencies:

   ```bash
   cd server
   python -m venv .venv
   source .venv/bin/activate   # on Windows: .venv\Scripts\activate
   pip install -r ../requirements_server.txt
   ```

2. Place your YOLO model in `../models/`, for example:

   ```bash
   cp /path/to/your_yolo.pt ../models/guided_vision_yolo.pt
   ```

   Or set an environment variable to point to a different path:

   ```bash
   export GUIDED_VISION_YOLO_PATH="/full/path/to/your_yolo.pt"
   ```

3. (Optional) Choose an LLM for vLLM, for example TinyLlama:

   ```bash
   export GUIDED_VISION_LLM_MODEL="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
   ```

   Make sure vLLM is correctly installed and your GPU drivers are configured.

4. Run the FastAPI server:

   ```bash
   cd server
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   The main endpoint is:

   - `POST /analyze_frame` with form-data file `file` (JPEG) → JSON containing:
     - `warning`: short text alert
     - `dangers`: list with label, distance (m), direction

---

## 3. Raspberry Pi 5 / laptop client setup

1. On the Pi (or your laptop for testing), install dependencies:

   ```bash
   cd client_pi
   python -m venv .venv
   source .venv/bin/activate   # on Windows: .venv\Scripts\activate
   pip install -r ../requirements_pi.txt
   ```

2. Edit `config.yaml` if needed:

   ```yaml
   server_url: "http://SERVER_IP:8000"  # change SERVER_IP to the GPU machine
   camera_index: 0
   send_width: 640
   jpeg_quality: 70
   request_timeout_sec: 2.0
   min_alert_interval_sec: 1.5
   show_preview: false
   ```

   - For laptop-only testing, set `server_url: "http://localhost:8000"`.
   - Set `show_preview: true` if you want a video window and to quit with `q`.

3. Run the client:

   ```bash
   cd client_pi
   python pi_client.py
   ```

   You should start hearing alerts like:

   ```text
   WATCH OUT! A CAR IS 2 METERS TO YOUR RIGHT.
   ```

---

## 4. How distance & direction work

- **Direction** is estimated from the bounding box center:
  - left third of the frame → LEFT
  - right third → RIGHT
  - center → FRONT

- **Distance** is approximated from how tall the object appears in the frame
  (relative bounding box height). You can tweak the thresholds in
  `server/distance_direction.py` to match your camera and typical scenes.

This is intentionally simple so it works in real time; you can replace it with a
proper depth model (e.g. MiDaS) later if you want better precision.

---

## 5. vLLM integration

- `server/reasoner_vllm.py` uses **vLLM** to turn structured detections into a short,
  high-urgency sentence.
- If vLLM is not installed or fails to load, it automatically falls back to a
  rule-based sentence in the same format, so the system still works.
- To guarantee you are using vLLM, make sure:
  - `pip install vllm` succeeds on the server.
  - `GUIDED_VISION_LLM_MODEL` points to a model compatible with vLLM.

---

## 6. Testing flow (before Raspberry Pi deployment)

1. Run the server on your **laptop** with webcam.
2. Run the client also on the same laptop with `server_url: "http://localhost:8000"`
   and `show_preview: true` in `client_pi/config.yaml`.
3. Confirm you see bounding boxes (via YOLO logs) and hear warnings.
4. When everything is OK, move only `client_pi/` to the Raspberry Pi and keep the
   server on your laptop or cloud GPU.

---

## 7. Notes

- Real-time performance depends on:
  - The YOLO model size (try `yolov8n` or a small custom model).
  - Network latency between Pi and server.
  - GPU performance for vLLM and YOLO.
- You can add/modify danger classes by training your own YOLO model and placing the
  `.pt` file in `models/`.

This project is meant as a clean starting point that already integrates camera,
detection, distance/direction, vLLM reasoning, and TTS into a single pipeline.
