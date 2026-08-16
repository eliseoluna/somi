Somi — Design
    
Voice-first AI companion. Runs fully local by default, with optional cloud-LLM
fallback. This document captures the architecture, flow, and the decisions that
would otherwise live only in my head.
    
Architecture Overview
    
A single orchestrator wires five stages together. Each stage is a swappable module
behind a small interface, so a component can be moved or replaced without touching
the rest of the pipeline.
    
    
                        ┌────────────── DESKTOP (9600X, 32GB) ──────────────┐
                        │                                                  │
    [Microphone] ──► wake word ──► record/VAD ──► STT ──► LLM client ──► play ──► [Speaker]
                        │  openWakeWord sounddevice  faster-   (HTTP)   sounddevice
                        │                          whisper
                        │                                    │                │
                        └────────────────────────────────────┼────────────────┘
                                                             │ LAN (OpenAI-compatible HTTP)
                                                             ▼
                                                  ┌────────────────────────┐
                                                  │  LLM BOX (RTX Titan)   │
                                                  │  llama-server          │
                                                  │  Qwen3.6-27B Q4_K_M    │
                                                  │  somi-tts (Qwen3-TTS)  │
                                                  └────────────────────────┘
                                                  (or: cloud API — DeepSeek,
                                                   OpenAI, etc. — via toggle)
    
    
Runtime Loop
    
    
init()                              # load wake word, STT, TTS models; build LLM client
loop:
    wait_for_wake_word()            # SLEEP  — openWakeWord blocks until wake word
    audio = record_until_silence()  # LISTEN — capture with VAD endpoint detection
    text = stt(audio)               # THINK  — faster-whisper, local CPU
    response = llm(text)            # THINK  — local Titan OR cloud API (toggle)
    response = sanitize(response)   # THINK  — strip emoji/symbols so TTS won't crash
    speech = tts(response)          # THINK  — Qwen3-TTS remote (default) OR local
    play(speech)                    # SPEAK  — sounddevice playback
    
    
Interruption ("barge-in") — the user starts talking while Somi is speaking — is a
later concern. v0.1 is a blocking loop; asyncio comes when interruption matters.
    
Component Map
    
| Stage     | Implementation      | Default location | Notes                                     |
|-----------|---------------------|------------------|-------------------------------------------|
| Wake word | openWakeWord        | Desktop          | No key, no account, local MIT             |
| Capture   | sounddevice + VAD   | Desktop          | Mic access must be local                  |
| STT       | faster-whisper      | Desktop          | CTranslate2 backend, fast on CPU, no GPU  |
| LLM       | llama-server (HTTP) | LLM Box          | GPU that fits the LLM of choice           |
| LLM (alt) | cloud API           | —                | DeepSeek/OpenAI/etc. via same HTTP client |
| TTS       | Qwen3-TTS           | LLM Box (CUDA)   | bfloat16, sub-second synthesis            |
| TTS (alt) | Qwen3-TTS           | Desktop (CPU)    | Fallback; ~3x real-time, slower           |
| Vision    | Florence-2          | Desktop          | Planned — screen awareness, not started   |
    
The Two Toggles
    
Both the brain (LLM) and the voice (TTS) are swappable through config, not code.
    
1. LLM backend — local vs cloud API
    
Same OpenAI-compatible client for both; only the base URL / key change.
    
    
SOMI_LLM_BACKEND=local     # llama-server on the LLM Box (default)
SOMI_LLM_BACKEND=api       # any OpenAI-compatible cloud API
    
    
- local → SOMI_LLM_BASE_URL=http://<llm-box>:8080/v1, no key
- api   → SOMI_LLM_BASE_URL=https://api.deepseek.com/v1, SOMI_LLM_API_KEY=...
    
The client code is identical; a factory (get_llm_client()) picks the base URL.
    
2. TTS backend — local vs remote
    
One interface, two backends, mirroring the LLM pattern.
    
    
SOMI_TTS_BACKEND=remote     # HTTP call to the TTS server on the LLM Box (default)
SOMI_TTS_BACKEND=local      # load Qwen3-TTS in-process on desktop CPU
    
    
- remote → SOMI_TTS_URL=http://<llm-box>:8081/v1/audio/speech
- local  → model loaded in-process, CPU inference on the desktop (slower fallback)
    
    
somi/tts/
  init.py     # factory: get_tts_backend()
  base.py         # TTSEngine abstract: synthesize(text) -> (wav_bytes, sample_rate)
  local.py        # in-process Qwen3-TTS (desktop CPU)
  remote.py       # HTTP client to LLM Box TTS server
    
    
Config Surface (env vars)

| Variable          | Purpose                               | Default                               |
|-------------------|---------------------------------------|---------------------------------------|
| SOMI_LLM_BACKEND  | local or api                          | local                                 |
| SOMI_LLM_BASE_URL | OpenAI-compatible endpoint            | http://<llm-box>:8080/v1              |
| SOMI_LLM_API_KEY  | Cloud API key (only when backend=api) | —                                     |
| SOMI_LLM_MODEL    | Model name sent to the endpoint       | (server default)                      |
| SOMI_TTS_BACKEND  | local or remote                       | remote                                |
| SOMI_TTS_URL      | TTS server endpoint (backend=remote)  | http://<llm-box>:8081/v1/audio/speech |
    
Secrets stay out of git — .env is already ignored. Load with python-dotenv or
manual os.getenv.
    
Decision Log
    
- openWakeWord for wake word — local, low-latency, MIT, no account and no API
  key (replaced Porcupine, which was key-gated and closed-source). Built-in wake
  word (hey_jarvis) for now; a custom "hey somi" model is the planned polish.
- faster-whisper for STT — CTranslate2 backend is much faster on CPU than
  stock Whisper; no GPU required, so it stays on the desktop.
- Qwen3.6-27B (Q4_K_M) for the LLM — the only machine that fits it is the LLM
  Box. Served over the LAN by llama-server (systemd) rather than loaded into the
  desktop process.
- OpenAI-compatible HTTP everywhere — llama-server exposes /v1/chat/completions,
  which means the LLM client is identical whether the brain is local or a cloud API.
  This is what makes the local/api toggle trivial.
- Qwen3-TTS (0.6B, Serena voice) for TTS — runs on the LLM Box (CUDA) by
  default, because CPU synthesis was ~3x real-time (11s for a 3.8s reply), too
  slow for conversation. The 0.6B model in bfloat16 fits alongside the 27B LLM.
- bfloat16, not float16, for TTS — float16 overflows on Qwen3-TTS (its
  activations exceed fp16's ~65504 max, producing NaN and a device-side assert)
  on any GPU. bfloat16 keeps float32's exponent range at half the memory.
  See server/README.md for the full gotchas (Triton removal, Turing caveat).
    
Current Status
    
- [x] Project scaffold (pyproject.toml, src/somi/, hatchling build)
- [x] Wake word detection (wake.py — sounddevice + openWakeWord)
- [x] Capture with silence detection (VAD)
- [x] STT (stt.py — faster-whisper)
- [x] LLM client (llm.py — local + api toggle)
- [x] TTS (tts/ — remote default + local fallback)
- [x] Orchestrator (main.py — full loop with sanitize step)
- [ ] Vision (Florence-2)

