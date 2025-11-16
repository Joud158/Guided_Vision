# new_vlm/server/main.py

import time

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from vlm_service import generate_caption, is_dangerous

app = FastAPI()

# Allow frontend / clients to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    #    Caption already has type + direction + distance.
    warning = None
    if danger:
        # This is what the client will *speak*
        warning = f"WATCH OUT! DANGER {caption}"

    latency_ms = (time.time() - start) * 1000.0

    # This JSON shape matches pi_client.py exactly:
    # - message: short text version (same as caption)
    # - raw_caption: same as caption
    # - warning: sentence that the client should speak (None when safe)
    return {
        "is_danger": danger,
        "message": caption,
        "raw_caption": caption,
        "warning": warning,
        "latency_ms": latency_ms,
    }
