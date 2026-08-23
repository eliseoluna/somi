"""TTS package - kokoro CPU or remote Titan backend."""

from somi import settings


def get_tts_backend():
    backend = settings.get("tts", "backend")

    if backend == "remote":
        from somi.tts import remote
        return remote

    from somi.tts import kokoro
    return kokoro
