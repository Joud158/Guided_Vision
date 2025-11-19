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
    """
    Wrapper around the queued TTS engine in tts.py
    (sequential, no overlapping).
    """
    import tts  # type: ignore

    if not text:
        return
    tts.speak(text)


def main() -> None:
    print("[GuidedVision] pi_client.main() starting...")

    # --- Load config.yaml ---
    try:
        cfg = load_config()
    except Exception as e:
        print(f"[GuidedVision] Failed to load config.yaml: {e}")
        return

    print(f"[GuidedVision] Config loaded: {cfg}")

    server_url = str(cfg.get("server_url", "http://localhost:8000")).rstrip("/")
    endpoint = server_url + "/analyze_frame"

    camera_index = int(cfg.get("camera_index", 0))

    send_width = int(cfg.get("send_width", 480))
    jpeg_quality = int(cfg.get("jpeg_quality", 50))
    request_timeout = float(cfg.get("request_timeout_sec", 3.0))
    frame_interval = float(cfg.get("frame_interval_sec", 0.10))
    repeat_interval = float(cfg.get("min_alert_interval_sec", 5.0))
    show_preview = bool(cfg.get("show_preview", False))

    print(f"[GuidedVision] Using camera_index={camera_index}, send_width={send_width}")
    print(
        f"[GuidedVision] request_timeout={request_timeout}, "
        f"frame_interval={frame_interval}, repeat_interval={repeat_interval}"
    )

    # --- Open camera ---
    print("[GuidedVision] Opening camera...")
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print(f"[GuidedVision] Could not open camera index {camera_index}")
        return

    print("[GuidedVision] Camera opened successfully.")
    print("[GuidedVision] Streaming. Press 'q' in the preview window (if enabled) to quit.")

    # --- danger / speech state ---
    danger_active = False
    last_warning_text = None
    last_speak_time = 0.0
    consecutive_errors = 0
    last_frame_time = 0.0

    # We'll use this to print response structure once
    printed_response_keys = False

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[GuidedVision] Failed to read frame from camera.")
                break

            now = time.time()

            # FPS limiter
            if (now - last_frame_time) < frame_interval:
                continue
            last_frame_time = now

            # Resize for speed
            h, w = frame.shape[:2]
            if w > send_width:
                scale = send_width / float(w)
                frame_to_send = cv2.resize(frame, (send_width, int(h * scale)))
            else:
                frame_to_send = frame

            # Encode JPEG
            ok, jpeg = cv2.imencode(
                ".jpg",
                frame_to_send,
                [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
            )
            if not ok:
                print("[GuidedVision] JPEG encode failed, skipping frame.")
                continue

            files = {"file": ("frame.jpg", jpeg.tobytes(), "image/jpeg")}

            # --- Call server ---
            try:
                resp = requests.post(endpoint, files=files, timeout=request_timeout)
                data = resp.json()
                if not printed_response_keys:
                    print(f"[GuidedVision] First response from server, keys={list(data.keys())}")
                    printed_response_keys = True
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3 or consecutive_errors % 10 == 0:
                    print(f"[GuidedVision] Server error (#{consecutive_errors}): {e}")
                # No data this frame
                continue

            warning = data.get("warning")
            dangers = data.get("dangers") or []
            has_danger = bool(dangers) and bool(warning)

            # --- Danger & speech logic ---
            if has_danger:
                print(f"[GuidedVision] Detected {len(dangers)} dangers; warning='{warning}'")

                if not danger_active:
                    # New danger episode → speak immediately
                    should_speak = True
                else:
                    # Same episode → speak if text changed OR repeat interval passed
                    changed_warning = warning != last_warning_text
                    time_elapsed = (now - last_speak_time) >= repeat_interval
                    should_speak = changed_warning or time_elapsed

                if should_speak:
                    print(f"[GuidedVision] SPEAK: {warning}")
                    speak(warning)
                    danger_active = True
                    last_warning_text = warning
                    last_speak_time = now
                else:
                    danger_active = True
            else:
                danger_active = False

            # --- Optional preview ---
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
