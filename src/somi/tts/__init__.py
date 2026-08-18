"""TTS package - local CPU or remote Titan backend."""

import os


def get_tts_backend():
    backend = os.getenv("SOMI_TTS_BACKEND", "kokoro")

    if backend == "remote":
        from somi.tts import remote
        return remote

    from somi.tts import kokoro
    return kokoro