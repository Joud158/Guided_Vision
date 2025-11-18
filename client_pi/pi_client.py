# Guided_Vision/client_pi/pi_client.py

import sys
import time
from pathlib import Path
import subprocess

import cv2
import requests
import yaml


# ---------- SUPER SIMPLE TTS (no queues, no pyttsx3) ----------
def speak(text: str) -> None:
    if not text:
        return

    # Debug so we SEE if TTS is being called every time
    print(f"[GuidedVision][TTS] speak() called with: {text!r}")

    try:
        if sys.platform.startswith("win"):
            # Windows: use System.Speech via PowerShell
            safe = text.replace("'", " ").replace('"', " ")
            ps_command = (
                "Add-Type -AssemblyName System.Speech; "
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.Speak('{safe}');"
            )
            # Use Popen so we don't block the loop
            subprocess.Popen(
                ["powershell", "-Command", ps_command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Linux / Pi: assumes espeak is installed
            safe = text.replace('"', " ").replace("'", " ")
            subprocess.Popen(
                ["espeak", safe],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception as e:
        print(f"[GuidedVision][TTS] ERROR: {e}")


# ---------- Config loading ----------
def load_config() -> dict:
    here = Path(__file__).resolve().parent
    cfg_path = here / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    print("[GuidedVision] pi_client.main() starting... (simple TTS version)")

    cfg = load_config()
    print(f"[GuidedVision] Config loaded: {cfg}")

    server_url = str(cfg.get("server_url", "http://localhost:8000")).rstrip("/")
    endpoint = server_url + "/analyze_frame"

    camera_index = int(cfg.get("camera_index", 0))
    send_width = int(cfg.get("send_width", 480))
    jpeg_quality = int(cfg.get("jpeg_quality", 50))
    request_timeout = float(cfg.get("request_timeout_sec", 3.0))
    frame_interval = float(cfg.get("frame_interval_sec", 3.0))  # 3s default
    show_preview = bool(cfg.get("show_preview", False))

    print(f"[GuidedVision] Using camera_index={camera_index}, send_width={send_width}")
    print(
        f"[GuidedVision] request_timeout={request_timeout}, "
        f"frame_interval={frame_interval}"
    )

    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print(f"[GuidedVision] Could not open camera index {camera_index}")
        return

    print("[GuidedVision] Camera opened successfully.")
    print("[GuidedVision] Streaming. Press 'q' in preview window (if enabled) to quit.")

    consecutive_errors = 0
    last_frame_time = 0.0
    printed_response_keys = False

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[GuidedVision] Failed to read frame from camera.")
                break

            now = time.time()

            # Respect frame_interval
            if (now - last_frame_time) < frame_interval:
                continue
            last_frame_time = now

            # Resize if needed
            h, w = frame.shape[:2]
            if w > send_width:
                scale = send_width / float(w)
                frame_to_send = cv2.resize(frame, (send_width, int(h * scale)))
            else:
                frame_to_send = frame

            # JPEG encode
            ok, jpeg = cv2.imencode(
                ".jpg",
                frame_to_send,
                [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
            )
            if not ok:
                print("[GuidedVision] JPEG encode failed, skipping frame.")
                continue

            files = {"file": ("frame.jpg", jpeg.tobytes(), "image/jpeg")}

            # Send to server
            try:
                resp = requests.post(endpoint, files=files, timeout=request_timeout)
                data = resp.json()
                if not printed_response_keys:
                    print(f"[GuidedVision] First response keys: {list(data.keys())}")
                    printed_response_keys = True
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3 or consecutive_errors % 10 == 0:
                    print(f"[GuidedVision] Server error (#{consecutive_errors}): {e}")
                continue

            # ---- Process server response ----
            is_danger = bool(data.get("is_danger", False))
            message = data.get("message")
            raw_caption = data.get("raw_caption") or message
            warning = data.get("warning")

            # Always show what the model thinks (one short sentence)
            if raw_caption:
                print(f"[GuidedVision] Caption: {raw_caption!r} (danger={is_danger})")

            # 🔊 If danger, speak ONLY the short warning from the server
            if is_danger:
                # warning is like: "sharp edge to your left"
                spoken_text = warning or "danger to your front"
                print(f"[GuidedVision] SPEAK: {spoken_text}")
                speak(spoken_text)

            if show_preview:
                cv2.imshow("Guided Vision Preview", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("[GuidedVision] 'q' pressed, exiting.")
                    break

    finally:
        cap.release()
        if show_preview:
            cv2.destroyAllWindows()
        print("[GuidedVision] Client shut down cleanly.")


if __name__ == "__main__":
    main()
