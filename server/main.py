# Guided_Vision/server/main.py

import time

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from vlm_service import generate_caption, is_dangerous

app = FastAPI()

LAST_RESULT=None

# Allow frontend / clients to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_direction(text: str) -> str:
    """
    Try to guess the direction of the danger from the caption.
    We keep it simple and only look for basic words.
    """
    t = text.lower()

    if "left" in t:
        return "left"
    if "right" in t:
        return "right"
    if "behind" in t or "back" in t:
        return "behind you"
    if "front" in t or "ahead" in t or "in front" in t:
        return "front"

    # Default if no direction found
    return "front"


def extract_danger_keyword(text: str) -> str:
    """
    Extract a short danger keyword from the caption.
    This is just to build: '<keyword> to your <direction>'
    """
    t = text.lower()

    danger_keywords = [
        # sharp / cutting objects
        "knife", "knives", "blade",
        "sharp edge", "sharp edges",
        "sharp corner", "sharp corners",
        "corner of the table", "table corner",
        "edge of the table", "table edge",
        "broken glass",

        # fire / heat / smoke
        "fire", "flame", "flames",

        # cables / wires
        "exposed cable", "exposed wire",
        "loose cable", "loose wire",
        "cable", "wire",

        # holes / gaps / stairs / obstacles
        "hole", "open hole", "pit", "gap",
        "stairs", "staircase", "step", "steps",
        "obstacle", "barrier",
    ]

    for kw in danger_keywords:
        if kw in t:
            # Return a clean short keyword for the alert
            return kw

    # Fallback if we don't detect a specific keyword
    return "danger"


@app.post("/analyze_frame")
async def analyze_frame(file: UploadFile = File(...)):
    """
    Receive a single frame, run the VLM, classify danger, and return a compact JSON
    that matches what client_pi/pi_client.py expects.
    """
    start = time.time()

    image_bytes = await file.read()

    # 1) Caption from VLM
    caption = generate_caption(image_bytes)

    # 2) Classify dangerous / safe
    danger = is_dangerous(caption)

    # 3) Always show what the model thinks in the server terminal
    print(f"[SERVER] Caption: {caption!r}  (danger={danger})")

    # 4) If dangerous, build the spoken warning sentence for the client
    warning = None
    if danger:
        direction = extract_direction(caption)
        danger_kw = extract_danger_keyword(caption)

        # This is what the client will *speak*
        # Example: sharp edge to your left
        warning = f"{danger_kw} to your {direction}"

    latency_ms = (time.time() - start) * 1000.0

    # This JSON shape matches pi_client.py exactly:
    # - message: short text version (same as caption)
    # - raw_caption: same as caption
    # - warning: sentence that the client should speak (None when safe)
    result = {
                "is_danger": danger,
                "message": caption,
                "raw_caption": caption,
                "warning": warning,
                "latency_ms": latency_ms,
            }

            # Save for the dashboard / Pi mode to poll
    global LAST_RESULT
    LAST_RESULT = result

    return result
@app.get("/last_result")
async def last_result():
    """
    Return the last analyze_frame result (from Pi client or web client).
    Useful for the dashboard / Pi mode.
    """
    global LAST_RESULT
    if LAST_RESULT is None:
        return {
            "is_danger": False,
            "message": None,
            "raw_caption": None,
            "warning": None,
            "latency_ms": None,
        }
    return LAST_RESULT
