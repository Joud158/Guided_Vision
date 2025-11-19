from typing import Tuple
import math


def categorize_distance(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    frame_height: int,
    label: str,
) -> str:
    """
    Return categorical distance instead of numeric meters:
    VERY CLOSE, CLOSE, NEAR, FAR.
    Uses bounding box area + height (better for small objects).
    """

    box_h = max(y2 - y1, 1.0)
    box_w = max(x2 - x1, 1.0)
    area = box_h * box_w
    rel_h = box_h / float(frame_height)

    label = label.lower()

    # ---------------------------------------------------------
    # HAZARDOUS SMALL OBJECTS: knife, cable, tool
    # More sensitive because they are small but dangerous
    # ---------------------------------------------------------
    if label in ["knife", "cable", "tool", "scissors"]:
        if area > 50000:
            return "VERY CLOSE"
        elif area > 25000:
            return "CLOSE"
        elif area > 12000:
            return "NEAR"
        else:
            return "FAR"

    # ---------------------------------------------------------
    # FIRE — taller but can be small
    # ---------------------------------------------------------
    if label == "fire":
        if rel_h >= 0.5:
            return "VERY CLOSE"
        elif rel_h >= 0.35:
            return "CLOSE"
        elif rel_h >= 0.22:
            return "NEAR"
        else:
            return "FAR"

    # ---------------------------------------------------------
    # DEFAULT CATEGORY
    # ---------------------------------------------------------
    if rel_h >= 0.45:
        return "VERY CLOSE"
    elif rel_h >= 0.3:
        return "CLOSE"
    elif rel_h >= 0.18:
        return "NEAR"
    else:
        return "FAR"


def estimate_direction(x1: float, x2: float, frame_width: int) -> str:
    """Return LEFT / RIGHT / FRONT based on the center x-position."""
    center_x = (x1 + x2) / 2.0
    rel = center_x / float(frame_width)

    if rel < 0.33:
        return "LEFT"
    elif rel > 0.66:
        return "RIGHT"
    else:
        return "FRONT"


def compute_distance_and_direction(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    frame_width: int,
    frame_height: int,
    label: str,
) -> Tuple[str, str]:
    """
    Return (distance_category, direction)
    e.g. ("VERY CLOSE", "LEFT")
    """
    distance_category = categorize_distance(
        x1, y1, x2, y2, frame_height, label
    )
    direction = estimate_direction(x1, x2, frame_width)
    return distance_category, direction
