import os

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from detector import DangerDetector
from reasoner import DangerReasoner   # updated filename


YOLO_MODEL_PATH = os.getenv(
    "GUIDED_VISION_YOLO_PATH",
    "../models/bestFinalMulti.pt"
)

app = FastAPI(title="Guided Vision Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------
# Load YOLO detector + rule-based reasoner
# -------------------------------------
detector = DangerDetector(YOLO_MODEL_PATH)
reasoner = DangerReasoner()   # no LLM needed


@app.post("/analyze_frame")
async def analyze_frame(file: UploadFile = File(...)):
    """Receive a JPEG frame, detect hazards, and produce a warning sentence."""
    
    # Decode incoming JPEG
    image_bytes = await file.read()
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Detect dangers
    dangers = detector.detect_dangers(frame)

    if not dangers:
        return {
            "warning": None,
            "dangers": []
        }

    # Optional: summary (not used by rule-based reasoner, just logging)
    summary = reasoner.build_structured_summary(dangers)

    # Generate warning sentence
    warning = reasoner.generate_warning(summary, dangers)

    return {
        "warning": warning,
        "dangers": dangers
    }
