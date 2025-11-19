import threading
import subprocess
import queue

# Single global queue for messages
_tts_queue: "queue.Queue[str]" = queue.Queue()


def _tts_worker() -> None:
    """
    Background worker that speaks messages from the queue
    sequentially (no overlapping speech).
    """
    while True:
        text = _tts_queue.get()
        if text is None:
            # Optional clean shutdown
            _tts_queue.task_done()
            break

        if not text:
            _tts_queue.task_done()
            continue

        # Avoid breaking the PowerShell command with quotes
        safe = text.replace("'", " ").replace('"', " ")

        ps_command = (
            "Add-Type -AssemblyName System.Speech; "
            "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speak.Speak('{safe}');"
        )

        try:
            subprocess.run(
                ["powershell", "-Command", ps_command],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[TTS] Error while speaking: {e}")

        _tts_queue.task_done()


# Start the worker as soon as this module is imported
_worker_thread = threading.Thread(target=_tts_worker, daemon=True)
_worker_thread.start()


def speak(text: str) -> None:
    """
    Queue text for speech. The background worker will
    speak one message at a time.
    """
    if not text:
        return
    _tts_queue.put(text)
