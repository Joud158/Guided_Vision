# new_vlm/server/vlm_service.py

import io
import re
import warnings

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
from transformers.utils import logging as hf_logging

# Silence transformers logs / warnings
hf_logging.set_verbosity_error()
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

# --- Model config ---
MODEL_NAME = "HuggingFaceTB/SmolVLM-256M-Instruct"
MAX_NEW_TOKENS = 32  # shorter = faster

# Auto device selection: GPU if available, otherwise CPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Load model once at startup (NO PRINTS) ---
processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForVision2Seq.from_pretrained(MODEL_NAME)
model.to(DEVICE)
model.eval()

# Prompt: include <image> so the model knows there's an image
PROMPT = (
    "User:\n"
    "<image>\n"
    "You are a vision assistant for a visually impaired person. "
    "Describe in ONE short, direct sentence what you see in the image. "
    "Always mention the main objects, people, and any vehicles. "
    "Always say where each important object is relative to the camera using words like "
    "front, left, right, or behind. If the distance is clear, mention the approximate "
    "distance in meters. "
    "For vehicles, explicitly say whether they are parked, moving away, passing by, or "
    "coming towards you. If a vehicle is coming towards you, include the exact phrase "
    "'coming towards you' in the sentence. "
    "Do not talk about being an AI or an assistant. Do not repeat the prompt. "
    "Just answer with the description sentence.\n"
    "Assistant:"
)


@torch.no_grad()
def generate_caption(image_bytes: bytes) -> str:
    """Run the VLM and return a single short sentence description."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    inputs = processor(text=PROMPT, images=image, return_tensors="pt").to(DEVICE)

    output_ids = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,
    )
    raw_text = processor.batch_decode(output_ids, skip_special_tokens=True)[0]
    return clean_caption(raw_text)


def clean_caption(text: str) -> str:
    """Extract a single clean sentence description from chat-style output."""
    t = text.strip()
    if not t:
        return "Unknown scene."

    lower = t.lower()

    # If the output includes conversation, keep what comes after "assistant:"
    idx = lower.rfind("assistant:")
    if idx != -1:
        t = t[idx + len("assistant:"):].strip()
        lower = t.lower()

    # Strip common prefixes
    for prefix in ["user:", "assistant:", "image description:", "description:"]:
        if lower.startswith(prefix):
            t = t[len(prefix):].lstrip(" :-").lstrip()
            lower = t.lower()
            break

    # If it's still just echoing the prompt, treat as unknown
    if lower.startswith("you are ") or "vision assistant for a visually impaired person" in lower:
        return "Unknown scene."

    # Keep only the first sentence or line
    for sep in ["\n", "."]:
        if sep in t:
            first = t.split(sep)[0].strip()
            if first:
                t = first
                break

    if not t:
        return "Unknown scene."

    return t

# --- Danger classification (regex with word boundaries) ---

# Non-vehicle dangers
NON_VEHICLE_DANGER_PATTERNS = [
    r"\bknife(s)?\b",
    r"\bknives\b",
    r"\bscissor(s)?\b",
    r"\bblade(s)?\b",
    r"\bsharp edge(s)?\b",
    r"\bsharp\b",
    r"\bfire\b",
    r"\bflame(s)?\b",
    r"\bsmoke\b",
    r"\bcable(s)?\b",
    r"\bwire(s)?\b",
    r"\bexposed cable(s)?\b",
    r"\bstair(s)?\b",
    r"\bstep(s)?\b",
    r"\bhole(s)?\b",
    r"\bpit\b",
    r"\bobstacle(s)?\b",
]

# Vehicle detection is handled separately so we only trigger on vehicles
# that are coming towards the user.
VEHICLE_WORDS = [
    "car",
    "cars",
    "vehicle",
    "vehicles",
    "bus",
    "buses",
    "truck",
    "trucks",
    "motorcycle",
    "motorcycles",
    "bike",
    "bikes",
]

VEHICLE_APPROACH_PATTERNS = [
    r"coming toward you",
    r"coming towards you",
    r"coming toward the camera",
    r"coming towards the camera",
    r"approaching you",
    r"approaching the camera",
    r"moving toward you",
    r"moving towards you",
    r"moving toward the camera",
    r"moving towards the camera",
    r"driving toward you",
    r"driving towards you",
    r"driving toward the camera",
    r"driving towards the camera",
    r"heading toward you",
    r"heading towards you",
    r"coming at you",
    r"moving closer to you",
]



def is_dangerous(description: str) -> bool:
    """Return True if description contains any danger keyword.

    - Non-vehicle hazards (knife, fire, cables, stairs, etc.) trigger danger directly.
    - Vehicles only trigger danger if they are coming towards the user/camera.
    """
    low = description.lower()

    # 1) Non-vehicle dangers
    for pat in NON_VEHICLE_DANGER_PATTERNS:
        if re.search(pat, low):
            return True

    # 2) Vehicle dangers: require a vehicle word AND an "approaching" phrase
    has_vehicle = any(word in low for word in VEHICLE_WORDS)
    if has_vehicle:
        for pat in VEHICLE_APPROACH_PATTERNS:
            if re.search(pat, low):
                return True

    return False


