import time
import json
import threading
from typing import Dict, Any, List, Optional

import cv2
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
import pyttsx3


# =========================
#  CONFIG
# =========================

# ⚠️ MODEL CHOICE:
# This is the *larger, more capable* SmolVLM. It will give better vision-language
# performance but is heavier to download and slower on CPU.
#
# If your machine or internet can't handle it, change this line to:
# MODEL_NAME = "HuggingFaceTB/SmolVLM-256M-Instruct"
MODEL_NAME = "HuggingFaceTB/SmolVLM-Instruct"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_SIDE = 384          # image resized so that max(h, w) = MAX_SIDE
FRAME_INTERVAL = 6.0    # seconds between model inferences
MIN_WARNING_INTERVAL = 8.0  # seconds between *similar* spoken warnings

print(f"[INFO] Using device: {DEVICE}")
print(f"[INFO] Loading model: {MODEL_NAME} (may take a while first time)")

processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForVision2Seq.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
).to(DEVICE)


# =========================
#  TTS SETUP
# =========================

print("[INFO] Initializing TTS engine ...")
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 170)
tts_engine.setProperty("volume", 1.0)


def speak(text: str) -> None:
    """Speak a warning out loud."""
    print(f"[VOICE] {text}")
    tts_engine.say(text)
    tts_engine.runAndWait()


# =========================
#  PROMPT
# =========================

HAZARD_PROMPT = (
    "You are a safety assistant for a blind person. "
    "You see one image from their chest-mounted camera. "
    "Describe nearby physical dangers that could hurt them within about 5 meters. "
    "Examples: cars, bikes, people about to collide, stairs, holes, edges, open manholes, "
    "slippery floor, fire, sharp tools, broken glass, obstacles on the ground, fast-moving objects.\n\n"
    "Return ONLY valid JSON, nothing else. Use exactly this schema:\n\n"
    "{\n"
    '  "dangers": [\n'
    "    {\n"
    '      "label": "short name of the danger, like car, fire, stairs",\n'
    '      "direction": "left" or "right" or "front" or "behind" or "unknown",\n'
    '      "distance_m": 2.5,\n'
    '      "severity": "low" or "medium" or "high"\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    '- distance_m MUST be a number (integer or decimal), not text.\n'
    "- Fill in the fields with REAL values from the image, NEVER with placeholders.\n"
    "- If there is more than one danger, you can include several objects in the list.\n"
    '- If there is no meaningful danger, answer exactly: { "dangers": [] }\n'
    "- Do NOT add comments, explanations, markdown, or any text outside the JSON.\n"
)


# =========================
#  JSON EXTRACTION
# =========================

def extract_json_block(text: str) -> Optional[str]:
    """
    Try to extract the first JSON object from the model output.
    We *only* trust actual JSON, we ignore extra 'Rules:' text etc.
    """
    # Optional: cut off trailing "Rules:" section if present
    lower = text.lower()
    rules_idx = lower.find("rules:")
    if rules_idx != -1:
        text = text[:rules_idx]

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start:end + 1]
    return candidate


# =========================
#  MODEL CALL
# =========================

def call_model_for_hazards(frame_bgr) -> Dict[str, Any]:
    """Send a smaller frame to the VLM and get a dict with a 'dangers' list."""
    h, w, _ = frame_bgr.shape
    scale = MAX_SIDE / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    small = cv2.resize(frame_bgr, (new_w, new_h))

    image = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": HAZARD_PROMPT},
            ],
        }
    ]

    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)

    inputs = processor(
        text=prompt,
        images=[image],
        return_tensors="pt",
    ).to(DEVICE)

    print("[INFO] Running hazard detection...")
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=128,
        )

    generated_text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True,
    )[0].strip()

    print("[DEBUG] Raw model output (first 300 chars):")
    print(generated_text[:300].replace("\n\n", "\n"))

    # Try to isolate JSON
    json_block = extract_json_block(generated_text)
    if not json_block:
        print("[WARN] No JSON block found in model output.")
        return {"dangers": []}

    try:
        data = json.loads(json_block)
        if not isinstance(data, dict):
            print("[WARN] JSON root is not an object.")
            return {"dangers": []}
        if "dangers" not in data or not isinstance(data["dangers"], list):
            print("[WARN] JSON object has no 'dangers' list.")
            return {"dangers": []}
        return data
    except json.JSONDecodeError as e:
        print("[WARN] JSON decode failed:", e)
        print("[WARN] Candidate JSON was:")
        print(json_block)
        return {"dangers": []}


# =========================
#  DANGER SELECTION / FORMAT
# =========================

def choose_primary_danger(dangers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pick the most urgent danger based on severity and distance."""
    if not dangers:
        return None

    severity_order = {"low": 1, "medium": 2, "high": 3}

    def score(d: Dict[str, Any]) -> float:
        sev = str(d.get("severity", "low")).lower()
        sev_score = severity_order.get(sev, 1)
        dist = d.get("distance_m", 3.0)
        try:
            dist = float(dist)
        except Exception:
            dist = 3.0
        # Higher = more urgent: closer & more severe
        return sev_score * 10.0 - dist

    return sorted(dangers, key=score, reverse=True)[0]


def dangers_similar(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Check if two dangers are 'basically the same' to avoid repeating them."""
    if not a or not b:
        return False

    same_label = str(a.get("label", "")).lower() == str(b.get("label", "")).lower()
    same_dir = str(a.get("direction", "")).lower() == str(b.get("direction", "")).lower()

    try:
        da = float(a.get("distance_m", 0))
        db = float(b.get("distance_m", 0))
        similar_dist = abs(da - db) < 0.7
    except Exception:
        similar_dist = True

    return same_label and same_dir and similar_dist


def format_warning(danger: Dict[str, Any]) -> str:
    """Turn a danger dict into a speech sentence."""
    label = str(danger.get("label", "danger"))
    direction = str(danger.get("direction", "front")).lower()
    dist = danger.get("distance_m", None)

    if direction not in {"left", "right", "front", "behind"}:
        direction = "front"

    try:
        dist_val = float(dist) if dist is not None else None
    except Exception:
        dist_val = None

    if dist_val is None or dist_val <= 0:
        if direction == "front":
            return f"Watch out, {label} ahead."
        return f"Watch out, {label} to your {direction}."

    dist_rounded = round(dist_val, 1)
    dir_phrase = "ahead" if direction == "front" else f"to your {direction}"
    return f"Watch out, {label} around {dist_rounded} meters {dir_phrase}!"


# =========================
#  CAMERA OPEN (LIKE YOUR TEST)
# =========================

def try_open_camera():
    combos = [
        (0, cv2.CAP_MSMF),   # 1400 on Windows
        (0, cv2.CAP_DSHOW),
        (0, cv2.CAP_ANY),
        (1, cv2.CAP_ANY),
    ]
    for idx, backend in combos:
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            return cap, idx, backend
        cap.release()
    return None, None, None


# =========================
#  HAZARD WORKER THREAD
# =========================

last_frame: Dict[str, Any] = {"frame": None}
stop_event = threading.Event()


def hazard_worker():
    """Background thread that periodically runs the VLM on the latest frame."""
    last_infer_time = 0.0
    last_warning_time = 0.0
    last_warning_danger: Optional[Dict[str, Any]] = None

    print("[INFO] Hazard worker started.")
    while not stop_event.is_set():
        time.sleep(0.05)

        frame = last_frame["frame"]
        if frame is None:
            continue

        now = time.time()
        if now - last_infer_time < FRAME_INTERVAL:
            continue
        last_infer_time = now

        data = call_model_for_hazards(frame)
        dangers = data.get("dangers", [])

        if not dangers:
            print("[INFO] No dangers in last analyzed frame.")
            continue

        print(f"[INFO] Hazards found: {dangers}")
        primary = choose_primary_danger(dangers)
        if not primary:
            continue

        # Anti-spam: don't repeat same/very similar danger too often
        if (
            last_warning_danger is not None
            and dangers_similar(primary, last_warning_danger)
            and (now - last_warning_time) < MIN_WARNING_INTERVAL
        ):
            print("[INFO] Skipping speech (similar danger recently warned).")
            continue

        warning_text = format_warning(primary)
        speak(warning_text)
        last_warning_danger = primary
        last_warning_time = now


# =========================
#  MAIN LOOP
# =========================

def main():
    cap, idx, backend = try_open_camera()
    if cap is None:
        print("❌ Could not open camera.")
        return

    cv2.namedWindow("Danger Watch", cv2.WINDOW_AUTOSIZE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print(f"[INFO] Camera opened (index={idx}, backend={backend}).")
    print("[INFO] Press 'q' or Esc or close the window to quit.")

    # Start hazard worker
    worker = threading.Thread(target=hazard_worker, daemon=True)
    worker.start()

    t0, frames = time.time(), 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[ERROR] Failed to read from camera.")
                break

            # Real-time: update shared frame for worker
            last_frame["frame"] = frame

            # FPS counter like your working camera script
            frames += 1
            if time.time() - t0 >= 1.0:
                cv2.setWindowTitle("Danger Watch", f"Danger Watch - ~{frames} FPS")
                t0, frames = time.time(), 0

            cv2.imshow("Danger Watch", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if cv2.getWindowProperty("Danger Watch", cv2.WND_PROP_VISIBLE) < 1:
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
    finally:
        stop_event.set()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
