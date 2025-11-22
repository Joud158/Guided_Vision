# Guided_Vision/client_pi/pi_client.py
#
# Raspberry Pi Camera Module 3 version
# Uses rpicam-jpeg to grab a single JPEG each time
# and sends it to the server for analysis.

import sys
import time
from pathlib import Path
import subprocess

import cv2
import numpy as np
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


# ---------- Capture from Camera Module 3 via rpicam-jpeg ----------
def capture_frame_from_rpicam(width: int = 640,
                              height: int = 480,
                              quality: int = 80) -> bytes:
    """
    Capture a single JPEG frame from Raspberry Pi Camera Module (libcamera / rpicam).
    Returns the JPEG bytes, or b"" on error.
    """
    cmd = [
        "rpicam-jpeg",
        "-o", "-",                 # output JPEG to stdout
        "--width", str(width),
        "--height", str(height),
        "--quality", str(quality),
        "--timeout", "200",
	"--nopreview",        # ms; short delay for exposure
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return result.stdout  # JPEG bytes
    except subprocess.CalledProcessError as e:
        print("[GuidedVision] rpicam-jpeg ERROR:")
        try:
            print(e.stderr.decode(errors="ignore"))
        except Exception:
            pass
        return b""
    except FileNotFoundError:
        print("[GuidedVision] ERROR: rpicam-jpeg not found. Install with:")
        print("  sudo apt update && sudo apt install -y rpicam-apps")
        return b""


def main() -> None:
    print("[GuidedVision] pi_client.main() starting... (Camera Module 3 version)")

    cfg = load_config()
    print(f"[GuidedVision] Config loaded: {cfg}")

    server_url = str(cfg.get("server_url", "http://localhost:8000")).rstrip("/")
    endpoint = server_url + "/analyze_frame"

    # We ignore camera_index for Camera Module 3; we always use rpicam-jpeg
    send_width = int(cfg.get("send_width", 480))
    jpeg_quality = int(cfg.get("jpeg_quality", 50))
    request_timeout = float(cfg.get("request_timeout_sec", 3.0))
    frame_interval = float(cfg.get("frame_interval_sec", 3.0))  # 3s default
    show_preview = bool(cfg.get("show_preview", False))

    # Derive a simple 4:3 height from width unless explicitly given
    send_height = int(cfg.get("send_height", int(send_width * 3 / 4)))

    print(
        f"[GuidedVision] Using rpicam-jpeg with width={send_width}, "
        f"height={send_height}, jpeg_quality={jpeg_quality}"
    )
    print(
        f"[GuidedVision] request_timeout={request_timeout}, "
        f"frame_interval={frame_interval}, show_preview={show_preview}"
    )

    consecutive_errors = 0
    last_frame_time = 0.0
    printed_response_keys = False

    print("[GuidedVision] Starting capture loop with Camera Module 3.")
    print("[GuidedVision] Press Ctrl+C in the terminal to stop.")

    try:
        while True:
            now = time.time()

            # Respect frame_interval
            if (now - last_frame_time) < frame_interval:
                # Small sleep to avoid busy-looping
                time.sleep(0.01)
                continue
            last_frame_time = now

            # --- Capture frame from Camera Module 3 ---
            print("[GuidedVision] Capturing frame from rpicam-jpeg...")
            jpeg_bytes = capture_frame_from_rpicam(
                width=send_width,
                height=send_height,
                quality=jpeg_quality,
            )

            if not jpeg_bytes:
                print("[GuidedVision] Capture failed (empty JPEG), skipping frame.")
                consecutive_errors += 1
                time.sleep(0.5)
                continue

            files = {"file": ("frame.jpg", jpeg_bytes, "image/jpeg")}

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

            # Optional preview window (only if you have a monitor / X11)
            if show_preview:
                try:
                    np_arr = np.frombuffer(jpeg_bytes, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv2.imshow("Guided Vision Preview", frame)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            print("[GuidedVision] 'q' pressed, exiting.")
                            break
                except Exception as e:
                    print(f"[GuidedVision] Preview error: {e}")

    except KeyboardInterrupt:
        print("[GuidedVision] KeyboardInterrupt received. Exiting...")

    finally:
        if show_preview:
            cv2.destroyAllWindows()
        print("[GuidedVision] Client shut down cleanly.")


if __name__ == "__main__":
    main()
