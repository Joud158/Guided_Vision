from typing import Tuple


def estimate_distance_m(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    frame_height: int,
    label: str,
) -> float:
    """Very rough distance estimate from bounding box height.

    For bigger boxes (taller on screen), return a smaller distance.
    Tuned for typical person/car-sized objects with a chest-level camera.

    You can adjust these thresholds to better fit your setup.
    """
    box_h = max(y2 - y1, 1.0)
    rel_h = box_h / float(frame_height)

    if rel_h >= 0.6:
        return 0.5
    elif rel_h >= 0.45:
        return 1.0
    elif rel_h >= 0.3:
        return 1.5
    elif rel_h >= 0.2:
        return 2.0
    elif rel_h >= 0.15:
        return 3.0
    elif rel_h >= 0.1:
        return 4.0
    else:
        return 5.0


def estimate_direction(x1: float, x2: float, frame_width: int) -> str:
    """Estimate LEFT / RIGHT / FRONT based on the box center."""
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
) -> Tuple[float, str]:
    """Helper that returns (distance_m, direction)."""
    distance = estimate_distance_m(x1, y1, x2, y2, frame_height, label)
    direction = estimate_direction(x1, x2, frame_width)
    return float(distance), direction
