"""Kokoro-82M TTS backend - local CPU, fast, no server"""

import io

import soundfile as sf
from kokoro_onnx import Kokoro

from somi import settings

_model = None


def _load() -> Kokoro:
    global _model
    if _model is None:
        _model = Kokoro(
            settings.get("tts", "kokoro_model"),
            settings.get("tts", "kokoro_voice"),
        )
    return _model

def synthesize(text: str) -> tuple[bytes, int]:
    kokoro = _load()
    samples, sample_rate= kokoro.create(
        text,
        voice=settings.get("tts", "voice"),
        speed=1.0,
        lang=settings.get("tts", "lang"),
    )
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    return buf.getvalue(), sample_rate


if __name__ == "__main__":
    wav_bytes, sr = synthesize("Hello, I'm Somi. How can I help you today?")
    with open("/tmp/kokoro_test.wav", "wb") as f:
        f.write(wav_bytes)
    print(f"done, sample rate {sr}")