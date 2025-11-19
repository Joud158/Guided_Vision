from typing import Any, Dict, List

import cv2  # noqa
from ultralytics import YOLO

from distance_direction import compute_distance_and_direction


class DangerDetector:
    """Wrapper around a YOLO model to detect dangerous objects."""

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.model = YOLO(model_path)
        self.class_names = self.model.names

    def detect_dangers(self, frame) -> List[Dict[str, Any]]:
        """
        Run YOLO on a frame and return a list of detected dangers.

        Each item:
        - label: class name
        - confidence: float
        - distance: VERY CLOSE / CLOSE / NEAR / FAR
        - direction: LEFT / RIGHT / FRONT
        """

        results = self.model.predict(
            frame,
            imgsz=640,    # back to original for reliability
            conf=0.5,    # slightly LOWER threshold to pick more detections
            verbose=False,
            max_det=10,   # optional: cap max detections
        )[0]



        h, w = frame.shape[:2]
        dangers: List[Dict[str, Any]] = []

        for box in results.boxes:
            cls_id = int(box.cls.item())
            label = self.class_names.get(cls_id, f"class_{cls_id}")
            conf = float(box.conf.item())

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # NEW: distance category + direction
            distance_cat, direction = compute_distance_and_direction(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                frame_width=w,
                frame_height=h,
                label=label,
            )

            dangers.append(
                {
                    "label": label,
                    "confidence": conf,
                    "distance": distance_cat,     # <-- UPDATED
                    "direction": direction,
                }
            )

        # Sort by closeness: VERY CLOSE → CLOSE → NEAR → FAR
        priority = {"VERY CLOSE": 0, "CLOSE": 1, "NEAR": 2, "FAR": 3}
        dangers.sort(key=lambda d: priority[d["distance"]])

        return dangers
