from typing import Any, Dict, List


class DangerReasoner:
    """
    Takes detected dangers (with distance category + direction) and
    outputs one short spoken warning.

    Example danger dict:
    {
        "label": "knife",
        "distance": "VERY CLOSE",
        "direction": "LEFT"
    }
    """

    def __init__(self, max_dangers: int = 3) -> None:
        self.max_dangers = max_dangers

    def build_structured_summary(self, dangers: List[Dict[str, Any]]) -> str:
        """Optional helper for logging or debugging."""
        if not dangers:
            return ""

        parts = []
        for idx, d in enumerate(dangers[: self.max_dangers], start=1):
            parts.append(
                f"{idx}) {d['label']} - {d['distance']} - {d['direction']}"
            )
        return " ; ".join(parts)

    def _rule_based_warning(self, dangers: List[Dict[str, Any]]) -> str:
        """Always pick the closest danger (first in sorted list)."""
        closest = dangers[0]

        label = closest["label"].upper()
        distance_cat = closest["distance"].upper()
        direction = closest["direction"].upper()

        # Final sentence format
        return f"WATCH OUT! A {label} IS {distance_cat} TO YOUR {direction}."

    def generate_warning(self, summary: str, dangers: List[Dict[str, Any]]) -> str:
        """Main function to generate warning sentence."""
        if not dangers:
            return ""

        # We ALWAYS use rule-based since vLLM is not used on laptop
        return self._rule_based_warning(dangers)
