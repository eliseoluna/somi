"""TTS package - local CPU or remote Titan backend."""

import os


def get_tts_backend():
    backend = os.getenv("SOMI_TTS_BACKEND", "remote")

    if backend == "local":
        from somi.tts import local
        return local

    from somi.tts import remote
    return remote