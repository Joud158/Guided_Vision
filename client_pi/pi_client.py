import time
from pathlib import Path

import cv2
import requests
import yaml


def load_config() -> dict:
    here = Path(__file__).resolve().parent
    cfg_path = here / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def speak(text: str) -> None:
    # Local import keeps startup fast on machines without audio configured yet
    import tts  # type: ignore

    tts.speak(text)


def main() -> None:
    cfg = load_config()
    server_url = cfg.get("server_url", "http://localhost:8000").rstrip("/")
    endpoint = server_url + "/analyze_frame"

    camera_index = int(cfg.get("camera_index", 0))
    send_width = int(cfg.get("send_width", 640))
    jpeg_quality = int(cfg.get("jpeg_quality", 70))
    request_timeout = float(cfg.get("request_timeout_sec", 2.0))
    min_alert_interval = float(cfg.get("min_alert_interval_sec", 1.5))
    show_preview = bool(cfg.get("show_preview", False))

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[GuidedVision] Could not open camera index {camera_index}")
        return

    print("[GuidedVision] Streaming frames. Press 'q' to quit (if preview enabled).")
    last_spoken = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[GuidedVision] Failed to read frame from camera.")
                break

            h, w = frame.shape[:2]
            if w > send_width:
                scale = send_width / float(w)
                frame = cv2.resize(frame, (send_width, int(h * scale)))

            ok, jpeg = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
            )
            if not ok:
                continue

            files = {"file": ("frame.jpg", jpeg.tobytes(), "image/jpeg")}

            try:
                resp = requests.post(endpoint, files=files, timeout=request_timeout)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[GuidedVision] Error contacting server: {e}")
                data = {}

            warning = data.get("warning")
            if warning and (time.time() - last_spoken) >= min_alert_interval:
                print(f"[GuidedVision] {warning}")
                speak(warning)
                last_spoken = time.time()

            if show_preview:
                cv2.imshow("Guided Vision Preview", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        if show_preview:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
