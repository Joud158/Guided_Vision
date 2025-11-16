Guided Vision VLM Project
===========================

Structure:
- server/: FastAPI server with a small Vision-Language Model (VLM).
- client_pi/: Raspberry Pi (or laptop) client for camera + TTS.
- requirements_server.txt: Python dependencies for the server.
- requirements_pi.txt: Python dependencies for the client.

Server setup (laptop):
1) cd guided_vision_vlm
2) python -m venv .venv
3) On Windows: .\.venv\Scripts\Activate.ps1
   On Linux:   source .venv/bin/activate
4) python -m pip install --upgrade pip
5) python -m pip install -r requirements_server.txt
6) cd server
7) uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Client setup (Raspberry Pi):
1) Copy this folder to the Pi.
2) sudo apt update
3) sudo apt install -y python3-opencv espeak
4) cd guided_vision_vlm
5) python3 -m venv .venv
6) source .venv/bin/activate
7) python -m pip install --upgrade pip
8) python -m pip install -r requirements_pi.txt
9) Edit client_pi/config.yaml and set server_url to your laptop IP (e.g. http://192.168.1.37:8000).
10) python client_pi/pi_client.py
