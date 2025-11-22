# Guided_Vision/server/vlm_service.py

import io
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
    "Focus on important objects, people, and any dangerous or potentially dangerous elements "
    "such as knives, blades, sharp edges or corners, broken glass, fire, smoke, exposed cables, "
    "holes, pits, gaps, stairs, or other obstacles. "
    "Always say where each important danger is relative to the camera using words like "
    "front, left, right, or behind. If the distance is clear, mention the approximate "
    "distance in meters. "
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


# --- Danger classification (no vehicles at all) ---

HAZARD_KEYWORDS = [
    # sharp / cutting objects
    "knife", "knives", "blade", "scissors",
    "sharp edge", "sharp edges",
    "sharp corner", "sharp corners",
    "corner of the table", "table corner",
    "edge of the table", "table edge",
    "broken glass",

    # general obstacles / furniture
    "table", "chair", "desk", "door", "wall", "edge",

    # fire / heat / smoke
    "fire", "flame", "flames", "smoke",

    # cables / wires
    "exposed cable", "exposed wire",
    "loose cable", "loose wire",
    "cable", "wire",

    # holes / gaps / stairs / obstacles
    "hole", "open hole", "pit", "gap",
    "stairs", "staircase", "step", "steps",
    "obstacle", "barrier",
]



def is_dangerous(description: str) -> bool:
    text = description.lower()

    # ✅ Only check for hazards (no vehicles, no special handling)
    for kw in HAZARD_KEYWORDS:
        if kw in text:
            return True

    return False
