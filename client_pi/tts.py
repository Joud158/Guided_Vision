import pyttsx3

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        # Slightly slower than default so speech is clear
        _engine.setProperty("rate", 175)
    return _engine


def speak(text: str) -> None:
    """Speak text out loud using the default TTS engine."""
    engine = _get_engine()
    # Stop any previous speech to avoid queueing too many alerts
    engine.stop()
    engine.say(text)
    engine.runAndWait()
