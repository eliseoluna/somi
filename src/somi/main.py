"""Somi orchestrator - wake word -> listen -> think -> speak loop."""

import re

from somi.capture import record_until_silence
from somi.llm import chat
from somi.stt import transcribe
from somi.tts import get_tts_backend
from somi.play import play
from somi.wake import listen_for_wake_word

def sanitize_for_speech(text: str) -> str:
    text = re.sub(r"[^\w\s.,!?;:'\"\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main() -> None:
    # get_tts_backend() only imports the module - the model itself loads
    # lazily on first synthesize() call, so idle Somi uses near-zero resources.
    tts = get_tts_backend()
    print("Ready. Say the wake word.")

    while True:
        # SLEEP - wait for wake word; STT/TTS models unloaded until first use
        listen_for_wake_word()          # defaults to "hey_jarvis", no key needed

        # LISTEN
        audio = record_until_silence()

        # THINK
        text = transcribe(audio)            # loads whipser on first use
        print(f"heard: {text}")
        response = sanitize_for_speech(chat(text))
        print(f"response: {response}")

        # SPEAK
        wav_bytes, sample_rate = tts.synthesize(response)   # loads Kokoro on first use
        play(wav_bytes, sample_rate)


if __name__ == "__main__":
    main()