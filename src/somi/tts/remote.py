"""Remote TTS backend - HTTP call to the LLM box's somi-tts server."""

import os
import httpx


def synthesize(text: str) -> tuple[bytes, int]:
    url = os.getenv("SOMI_TTS_URL", "http://10.0.0.215:8081/v1/audio/speech")
    resp = httpx.post(
        url,
        json={"input": text, "voice": "Serena", "language": "English"},
        timeout=60.0
    )
    resp.raise_for_status()
    return resp.content, 24000  # sample rate is fixed at 24kHz