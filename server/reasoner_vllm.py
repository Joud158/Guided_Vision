from typing import Any, Dict, List

try:
    from vllm import LLM, SamplingParams  # type: ignore
except Exception:  # ImportError or runtime error
    LLM = None
    SamplingParams = None


class DangerReasoner:
    """Turn detections into short spoken warnings using vLLM.

    If vLLM is not available, falls back to a simple rule-based template
    with the same sentence format.
    """

    def __init__(self, model_name: str, max_dangers: int = 3) -> None:
        self.model_name = model_name
        self.max_dangers = max_dangers

        if LLM is None or SamplingParams is None:
            print(
                "[GuidedVision] vLLM is not available. "
                "Falling back to rule-based warnings."
            )
            self.llm = None
            self.sampling_params = None
        else:
            self.sampling_params = SamplingParams(
                temperature=0.2,
                max_tokens=64,
                top_p=0.95,
            )
            self.llm = LLM(model=self.model_name)

    def build_structured_summary(self, dangers: List[Dict[str, Any]]) -> str:
        """Convert danger dicts into a compact textual summary."""
        if not dangers:
            return ""

        parts = []
        for idx, d in enumerate(dangers[: self.max_dangers], start=1):
            label = d["label"]
            distance_m = d["distance_m"]
            direction = d["direction"]
            parts.append(
                f"{idx}) {label} at approximately {distance_m:.1f} meters to the {direction}"
            )

        return " ; ".join(parts)

    def _rule_based_warning(self, dangers: List[Dict[str, Any]]) -> str:
        """Fallback if vLLM cannot be used: pick closest danger and format."""
        closest = dangers[0]
        label = closest["label"].upper()
        distance_m = closest["distance_m"]
        direction = closest["direction"].upper()
        distance_str = f"{distance_m:.1f}".rstrip("0").rstrip(".")
        return f"WATCH OUT! A {label} IS {distance_str} METERS TO YOUR {direction}."

    def generate_warning(self, summary: str, dangers: List[Dict[str, Any]]) -> str:
        """Generate a warning sentence, using vLLM when available."""
        if not dangers:
            return ""

        # Fall back to deterministic rule-based sentence if vLLM is not ready
        if self.llm is None or self.sampling_params is None:
            return self._rule_based_warning(dangers)

        prompt = (
            "You are an assistive safety system for a blind or low-vision user.\n"
            "You receive structured detections about nearby dangers and you must respond\n"
            "with a VERY SHORT, LOUD-style warning sentence in English.\n\n"
            f"Detections: {summary}\n\n"
            "Rules:\n"
            "- Always speak in the second person.\n"
            "- Always start the sentence with: \"WATCH OUT!\" (all caps).\n"
            "- Mention only the single closest danger.\n"
            "- Include: object type, approximate distance in meters, and direction (LEFT, RIGHT, or FRONT).\n"
            "- Use the format: WATCH OUT! A <OBJECT> IS <DISTANCE> METERS TO YOUR <DIRECTION>.\n"
            "- Do not add any extra explanation or words.\n\n"
            "Return exactly ONE sentence following this format."
        )

        outputs = self.llm.generate([prompt], self.sampling_params)
        text = outputs[0].outputs[0].text.strip().replace("\n", " ")

        # Safety net: if the LLM doesn't follow the style, fall back
        if not text.upper().startswith("WATCH OUT") or "METERS" not in text.upper():
            return self._rule_based_warning(dangers)

        return text
