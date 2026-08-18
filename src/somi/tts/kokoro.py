"""Kokoro-82M TTS backend - local CPU, fast, no server"""

import io

import soundfile as sf
from kokoro_onnx import Kokoro

MODEL_PATH = "/home/eliseoluna/.config/somi/kokoro/kokoro-v1.0.onnx"
VOICE_PATH = "/home/eliseoluna/.config/somi/kokoro/voices-v1.0.bin"
VOICE = "af_heart"
LANG = "en-us"

_model = None


def _load() -> Kokoro:
    global _model
    if _model is None:
        _model = Kokoro(MODEL_PATH, VOICE_PATH)
    return _model


def synthesize(text: str) -> tuple[bytes, int]:
    kokoro = _load()
    samples, sample_rate = kokoro.create(text, voice=VOICE, speed=1.0, lang=LANG)
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    return buf.getvalue(), sample_rate


if __name__ == "__main__":
    wav_bytes, sr = synthesize("Hello, I'm Somi. How can I help you today?")
    with open("/tmp/kokoro_test.wav", "wb") as f:
        f.write(wav_bytes)
    print(f"done, sample rate {sr}")