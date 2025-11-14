Put your YOLO object detection weights here.

Example:
- guided_vision_yolo.pt  (custom model trained on danger classes: cars, tools, cables, fire, etc.)

By default, the server looks for:
- ../models/guided_vision_yolo.pt

You can override this with the environment variable:
- GUIDED_VISION_YOLO_PATH=/full/path/to/your_model.pt
