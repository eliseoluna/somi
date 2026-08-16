"""Somi orchestrator - wake word -> listen -> think -> speak loop."""

from somi.capture import record_until_silence
from somi.llm import chat
from somi.stt import load_model as load_stt, transcribe
from somi.tts import get_tts_backend
from somi.play import play
from somi.wake import listen_for_wake_word
import re

def sanitize_for_speech(text: str) -> str:
    text = re.sub(r"[^\w\s.,!?;:'\"\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main() -> None:
    print("Loading models...")
    load_stt()
    tts = get_tts_backend()
    print("Ready. Say the wake word.")

    while True:
        # SLEEP - wait for wake word
        listen_for_wake_word()          # defaults to "hey_jarvis", no key needed

        # LISTEN
        audio = record_until_silence()

        # THINK
        text = transcribe(audio)
        print(f"heard: {text}")
        response = sanitize_for_speech(chat(text))
        print(f"response: {response}")

        # SPEAK
        wav_bytes, sample_rate = tts.synthesize(response)
        play(wav_bytes, sample_rate)


if __name__ == "__main__":
    main()