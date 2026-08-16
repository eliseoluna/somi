"""Local CPU TTS backend using Qwen3-TTS in-process."""

import io

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
VOICE = "Serena"
LANGUAGE = "English"

_model = None

def _load():
    global _model
    if _model is None:
        _model = Qwen3TTSModel.from_pretrained(
            MODEL_ID, device_map="cpu", dtype=torch.float32
        )
    return _model

def synthesize(text: str) -> tuple[bytes, int]:
    model = _load()
    wavs, sr = model.generate_custom_voice(
        text=text, language=LANGUAGE, speaker=VOICE
    )
    buf = io.BytesIO()
    sf.write(buf, wavs[0], sr, format="WAV")
    return buf.getvalue(), sr