    Somi — Design
    
    Voice-first AI companion. Runs fully local by default, with optional cloud-LLM
    fallback. This document captures the architecture, flow, and the decisions that
    would otherwise live only in my head.
    
    Architecture Overview
    
    A single orchestrator wires five stages together. Each stage is a swappable module
    behind a small interface, so a component can be moved or replaced without touching
    the rest of the pipeline.
    
    
                        ────────────── DESKTOP (9600X, 32GB) ──────────────
                                                                          
     [Microphone] ──► wake word ──► record/VAD ──► STT ──► LLM client ──► TTS ──► [Speaker]
                                                                                      
                        ────────────────────────────────────┼───────────────
                                                            │ LAN (OpenAI-compatible HTTP)
                                                            ▼
                                                  ┌────────────────────────┐
                                                  │  LLM BOX (RTX Titan)   │
                                                  │  llama-server          │
                                                  │  Qwen3.6-27B Q4_K_M    │
                                                  │  (optional TTS offload)│
                                                  └────────────────────────┘
                                                  (or: cloud API — DeepSeek,
                                                   OpenAI, etc. — via toggle)
    
    
    Runtime Loop
    
    
    init()                              # load wake word, STT, TTS models; build LLM client
    loop:
        wait_for_wake_word()            # SLEEP  — openWakeWord blocks until "Hey Somi"
        audio = record_until_silence()  # LISTEN — capture with VAD endpoint detection
        text = stt(audio)               # THINK  — faster-whisper, local CPU
        response = llm(text)            # THINK  — local Titan OR cloud API (toggle)
        speech = tts(response)          # THINK  — Qwen3-TTS local OR remote (toggle)
        play(speech)                    # SPEAK  — sounddevice playback
    
    
    Interruption ("barge-in") — the user starts talking while Somi is speaking — is a
    later concern. v0.1 is a blocking loop; asyncio comes when interruption matters.
    
    Component Map
    
    | Stage     | Implementation      | Default location | Notes                                     |
    |-----------|---------------------|------------------|-------------------------------------------|
    | Wake word | openWakeWord           | Desktop          | Mic latency is critical; tiny footprint   |
    | Capture   | sounddevice + VAD   | Desktop          | Mic access must be local                  |
    | STT       | faster-whisper      | Desktop          | CTranslate2 backend, fast on CPU, no GPU  |
    | LLM       | llama-server (HTTP) | LLM Box          | GPU that fits the LLM of choice           |
    | LLM (alt) | cloud API           | —                | DeepSeek/OpenAI/etc. via same HTTP client |
    | TTS       | Qwen3-TTS           | LLM BOX (TITAN)    | Latency-sensitive; default local          |
    | TTS (alt) | Qwen3-TTS           | Desktop (CPU)    | Edge-case offload when desktop is busy    |
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
    
    
    SOMI_TTS_BACKEND=local      # load Qwen3-TTS in-process on desktop (default)
    SOMI_TTS_BACKEND=remote     # HTTP call to a TTS server on the LLM Box
    
    
    - local  → model loaded in-process, CPU inference on the desktop
    - remote → SOMI_TTS_URL=http://<llm-box>:8081/v1/audio/speech (small server,
      built later; the remote client is a stub from day one)
    
    
    somi/tts/
      init.py     # factory: get_tts_backend(config)
      base.py         # TTSEngine abstract: synthesize(text) -> audio bytes
      local.py        # in-process Qwen3-TTS (desktop CPU)
      remote.py       # HTTP client to LLM Box TTS server
    
    
    Config Surface (env vars)
    
    | Variable           | Purpose                               | Default                  |
    |--------------------|---------------------------------------|--------------------------|
    | SOMI_PICOVOICE_KEY | openWakeWord                          | — (required)             |
    | SOMI_WAKE_KEYWORD  | Path to custom .ppn, or built-in name | openWakeWord                |
    | SOMI_LLM_BACKEND   | local or api                          | local                    |
    | SOMI_LLM_BASE_URL  | OpenAI-compatible endpoint            | http://<llm-box>:8080/v1 |
    | SOMI_LLM_API_KEY   | Cloud API key (only when backend=api) | —                        |
    | SOMI_LLM_MODEL     | Model name sent to the endpoint       | (server default)         |
    | SOMI_TTS_BACKEND   | local or remote                       | local                    |
    | SOMI_TTS_URL       | TTS server endpoint (backend=remote)  | —                        |
    
    Secrets stay out of git — .env is already ignored. Load with python-dotenv or
    manual os.getenv.
    
    Decision Log
    
    - openWakeWord for wake word — local, low-latency, small footprint, free-tier key.
      Custom wake word ("Hey Somi") via a .ppn file; built-in fallback for testing.
    - faster-whisper for STT — CTranslate2 backend is much faster on CPU than
      stock Whisper; no GPU required, so it stays on the desktop.
    - Qwen3.6-27B (Q4_K_M) for the LLM — the only machine that fits it is my LLM
      Box. Served over the LAN by llama-server (systemd) rather than loaded into the
      desktop process.
    - OpenAI-compatible HTTP everywhere — llama-server exposes /v1/chat/completions,
      which means the LLM client is identical whether the brain is local or a cloud API.
      This is what makes the local/api toggle trivial.
    - Qwen3-TTS for TTS (over Piper/Kokoro) — chosen voice model. Runs on desktop
      CPU by default; TTS is latency-sensitive and lives on the machine with the
      speaker. The LLM Box is a CPU offload option for edge cases, not the default.
    - Florence-2 for screen awareness — planned so Somi can see/describe what's on
      screen. Local to the desktop (it needs the screen). Not started.
    
    Current Status
    
    - [x] Project scaffold (pyproject.toml, src/somi/, hatchling build)
    - [x] Wake word detection (wake.py — sounddevice + openWakeWord)
    - [x] Capture with silence detection (VAD)
    - [x] STT (stt.py — faster-whisper)
    - [ ] LLM client (llm.py — local + api toggle)
    - [ ] TTS (tts/ — local + remote toggle)
    - [ ] Orchestrator (main.py — wire the loop)
    - [ ] Vision (Florence-2)
    
