import os

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from detector import DangerDetector
from reasoner_vllm import DangerReasoner


YOLO_MODEL_PATH = os.getenv("GUIDED_VISION_YOLO_PATH", "../models/bestFinalMulti.pt")
LLM_MODEL_NAME = os.getenv("GUIDED_VISION_LLM_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

app = FastAPI(title="Guided Vision vLLM Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = DangerDetector(YOLO_MODEL_PATH)
reasoner = DangerReasoner(model_name=LLM_MODEL_NAME)


@app.post("/analyze_frame")
async def analyze_frame(file: UploadFile = File(...)):
    """Receive a JPEG frame, run detection + vLLM, and return a warning."""
    image_bytes = await file.read()
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    dangers = detector.detect_dangers(frame)

    if not dangers:
        return {"warning": None, "dangers": []}

    summary = reasoner.build_structured_summary(dangers)
    warning = reasoner.generate_warning(summary, dangers)

    return {"warning": warning, "dangers": dangers}
