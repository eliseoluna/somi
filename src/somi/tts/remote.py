"""Remote TTS backend - HTTP call to the LLM box's somi-tts server."""

import httpx

from somi import settings

def synthesize(text: str) -> tuple[bytes, int]:
    url = settings.get("tts", "url")
    resp = httpx.post(
        url,
        json={"input": text, "voice": "Serena", "language": "English"},
        timeout=60.0
    )
    resp.raise_for_status()
    return resp.content, 24000  # sample rate is fixed at 24kHz