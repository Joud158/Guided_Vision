# Guided_Vision/client_pi/tts.py

import threading
import subprocess
import queue
import sys

_tts_queue: "queue.Queue[str]" = queue.Queue()


def _speak_linux(text: str) -> None:
    safe = text.replace('"', " ").replace("'", " ")
    try:
        subprocess.run(
            ["espeak", safe],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[TTS] Linux TTS error: {e}")


def _speak_windows(text: str) -> None:
    safe = text.replace("'", " ").replace('"', " ")
    ps_command = (
        "Add-Type -AssemblyName System.Speech; "
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$synth.Speak('{safe}');"
    )
    try:
        subprocess.run(
            ["powershell", "-Command", ps_command],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[TTS] Windows TTS error: {e}")


def _tts_worker() -> None:
    while True:
        text = _tts_queue.get()
        if text is None:
            _tts_queue.task_done()
            break

        if not text:
            _tts_queue.task_done()
            continue

        if sys.platform.startswith("win"):
            _speak_windows(text)
        else:
            _speak_linux(text)

        _tts_queue.task_done()


_worker_thread = threading.Thread(target=_tts_worker, daemon=True)
_worker_thread.start()


def speak(text: str) -> None:
    if not text:
        return
    _tts_queue.put(text)
