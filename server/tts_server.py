"""TTS server for Somi - Qwen3-TTS on CUDA, exposed over HTTP.

Runs on the LLM box (RTX Titan 24GB) as a systemd service, alongside llama-server. The desktop's
somi.tts.remote backend POSTs text here and receives WAV bytes back.

Deployment notes (hard-won - read before changing anything):

1. dtype MUST be bfloat16 on RTX Titan (Turing / sm_75):
    - float16 overflow -> "CUDA error: device-side assert triggered"
    - float32 works but ~5.2 GiB -> OOM next to the 27B LLM (18+GiB)
    - bfloat16 = float32's exponent range (no overflow) + half the memory
2. Triton was UNINSTALLED from the tts-venv. Its JIT needs CUDA dev headers
   (cuda.h) which this box doesn't have, and gcc compilation fails. torch falls
   back to native CUDA cleanly without it. Do NOT reinstall triton unless you also apt
   install nvidia-cuda-toolkit.
3. The model downloads ~2.5GB of weights on first startup (one-time).
4. Always restart the service after editing this file (systemd won't hot-reload).

See systemd unit: server/somi-tts.service
"""

import io
from contextlib import asynccontextmanager

import soundfile as sf
import torch
from fastapi import FastAPI, Response
from pydantic import BaseModel
from qwen_tts import Qwen3TTSModel

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
DEFAULT_VOICE = "Serena"
DEFAULT_LANGUAGE = "English"

model: Qwen3TTSModel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    model = Qwen3TTSModel.from_pretrained(
        MODEL_ID,
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    yield

app = FastAPI(lifespan=lifespan)

class SpeechRequest(BaseModel):
    input: str
    voice: str = DEFAULT_VOICE
    language: str = DEFAULT_LANGUAGE

@app.post("/v1/audio/speech")
async def synthesize(req: SpeechRequest):
    wavs, sr = model.generate_custom_voice(
        text=req.input,
        language=req.language,
        speaker=req.voice,
    )
    buf = io.BytesIO()
    sf.write(buf, wavs[0], sr, format="WAV")
    return Response(content=buf.getvalue(), media_type="audio/wav")