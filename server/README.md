Somi TTS Server

Deployment files for the Qwen3-TTS server that runs on the LLM box, not on the desktop. The desktop's somi.tts.remote backend POSTs text here and receives WAV audio back.

Files

- tts_server.py - FastAPI app. Loads Qwen3-TTS 0.6B on CUDA, serves POST /v1/audio/speech. Returns WAV bytes.
- somi-tts.service - systemd unit that runs the server as a background daemon, auto-restarts on crash, survives reboots.

Why this exists

Somi's TTS runs on the LLM box (CUDA) instead of the desktop CPU because:

- CPU synthesis was ~3x real-time (11s for a 3.8s reply) - too slow
- The 0.6B model is ~1.2GB in bfloat16, fits alongside the 27B LLM
- The desktop's 9060XT is AMD/RDNA4; Qwen3-TTS is CUDA only

Deployment (on the LLM box)

```bash
# 1. Create the venv (once)
python3 -m venv ~/tts-venv
~/tts-venv/bin/python -m pip install torch qwen-tts fastapi uvicorn soundfile
# NOTE: do NOT install triton - see tts_server.py header for why

# 2. Copy these files
cp tts_server.py ~/tts_server.py
sudo cp somi-tts.service /etc/systemd/system/somi-tts.service

# 3. Start it
sudo systemctl daemon-reload
sudo systemctl enable --now somi-tts

# 4. Verify
curl -s -X POST http://10.0.0.215:8081/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello.","voice":"Serena","language":"English"}' \
  --output /tmp/test.wav
```


Gotchas (read before debugging)

- dtype must be bfloat16, not float16 - float16 overflows for Qwen3-TTS on any GPU (its activations exceed fp16's ~65504 max, producing NaN). bfloat16 keeps float32's exponent range at half the memory. This is a universal model requirement, not specific to this box.
- Why not float32? float32 also works (no overflow) but needs ~5.2GB - that OOMs next to the 27B LLM (18+GB) on a 24GB card. On a 48GB card float32 would be fine.
- Turing caveat - the RTX Titan (sm_75) has no bfloat16 hardware acceleration, so bf16 runs emulated here (still far faster than CPU). Ampere+ cards (RTX 30xx/40xx/50xx, A100/H100) run bf16 at full speed.
- Triton is uninstalled - its JIT needs CUDA dev headers (cuda.h) that require apt install nvidia-cuda-toolkit. torch falls back to native CUDA cleanly without Triton; only reinstall it alongside the toolkit.
- Ports - this server listens on 8081; llama-server uses 8080.

