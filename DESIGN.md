S    Somi — Design
    
    Voice-first AI companion. Runs fully local by default, with optional cloud-LLM
    fallback. This document captures the architecture, flow, and the decisions that
    would otherwise live only in my head.
    
    Architecture Overview
    
    A single orchestrator wires five stages together. Each stage is a swappable module
    behind a small interface, so a component can be moved or replaced without touching
    the rest of the pipeline.
    
    
                        ┌────────────── DESKTOP (9600X, 32GB) ──────────────┐
                        │                                                  │
     [Microphone] ──► wake word ──► record/VAD ──► STT ──► LLM client ──► TTS ──► play ──► [Speaker]
                        │  openWakeWord sounddevice  faster-   (HTTP)    Kokoro  sounddevice
                        │                          whisper
                        │                                    │                │
                        └────────────────────────────────────┼────────────────┘
                                                             │ LAN (OpenAI-compatible HTTP)
                                                             ▼
                                                  ┌────────────────────────┐
                                                  │  LLM BOX (RTX Titan)   │
                                                  │  llama-server          │
                                                  │  Qwen3.6-27B Q4_K_M    │
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
        speech = tts(response)          # THINK  — Kokoro (default) OR remote Qwen3-TTS
        play(speech)                    # SPEAK  — sounddevice playback
    
    
    Interruption ("barge-in") — the user starts talking while Somi is speaking — is a
    later concern. v0.1 is a blocking loop; asyncio comes when interruption matters.
    
    Component Map
    
    | Stage     | Implementation       | Default location | Notes                                     |
    |-----------|----------------------|------------------|-------------------------------------------|
    | Wake word | openWakeWord         | Desktop          | No key, no account, local MIT             |
    | Capture   | sounddevice + VAD    | Desktop          | Mic access must be local                  |
    | STT       | faster-whisper       | Desktop          | CTranslate2 backend, fast on CPU, no GPU  |
    | LLM       | llama-server (HTTP)  | LLM Box          | GPU that fits the LLM of choice           |
    | LLM (alt) | cloud API            | —                | DeepSeek/OpenAI/etc. via same HTTP client |
    | TTS       | Kokoro-82M           | Desktop (CPU)    | Fast, natural, no server                  |
    | TTS (alt) | Qwen3-TTS (remote)   | LLM Box (CUDA)   | Highest quality; bfloat16, optional       |
    | Vision    | mmproj or Florence-2 | Desktop/Titan    | Planned — screen awareness, not started   |
    
    The Two Toggles
    
    Both the brain (LLM) and the voice (TTS) are swappable through config, not code.
    
    1. LLM backend — local vs cloud API
    
    Same OpenAI-compatible client for both; only the base URL / key change.
    
    
    SOMI_LLM_BACKEND=local     # llama-server on the LLM Box (default)
    SOMI_LLM_BACKEND=api       # any OpenAI-compatible cloud API
    
    
    - local → SOMI_LLM_BASE_URL=http://<llm-box>:8080/v1, no key
    - api   → SOMI_LLM_BASE_URL=https://api.deepseek.com/v1, `SOMI_LLM_API_KEY=***
    
    The client code is identical; a factory (get_llm_client()) picks the base URL.
    
    2. TTS backend — kokoro vs remote
    
    One interface, two backends, mirroring the LLM pattern.
    
    
    SOMI_TTS_BACKEND=kokoro     # Kokoro-82M on desktop CPU (default)
    SOMI_TTS_BACKEND=remote     # HTTP call to Qwen3-TTS server on the LLM Box
    
    
    - kokoro → local ONNX model, no server, fast, natural
    - remote → SOMI_TTS_URL=http://<llm-box>:8081/v1/audio/speech
    
    
    somi/tts/
      init.py     # factory: get_tts_backend()
      base.py         # TTSEngine abstract: synthesize(text) -> (wav_bytes, sample_rate)
      kokoro.py       # Kokoro-82M (desktop CPU, default)
      remote.py       # HTTP client to LLM Box TTS server
    
    
    Config Surface (env vars)
    
    | Variable          | Purpose                               | Default                               |
    |-------------------|---------------------------------------|---------------------------------------|
    | SOMI_LLM_BACKEND  | local or api                          | local                                 |
    | SOMI_LLM_BASE_URL | OpenAI-compatible endpoint            | http://<llm-box>:8080/v1              |
    | SOMI_LLM_API_KEY  | Cloud API key (only when backend=api) | —                                     |
    | SOMI_LLM_MODEL    | Model name sent to the endpoint       | (server default)                      |
    | SOMI_TTS_BACKEND  | kokoro or remote                      | kokoro                                |
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
    - Kokoro-82M for TTS (default) — 82M-parameter ONNX model running on the
      desktop CPU, faster than real-time, voice quality far above Piper. Replaced
      Qwen3-TTS as the default: Qwen3-TTS on the Titan (bf16 emulated on Turing)
      was ~0.7x real-time (15s for a 10s reply), too slow for conversation. Kokoro
      solves the speed problem with no GPU, no server, no bf16.
    - Qwen3-TTS (remote) kept as quality fallback — still the highest-quality
      option, served from the Titan when a natural voice is worth the latency.
      Requires the bfloat16 (not float16) config — float16 overflows on Qwen3-TTS
      (activations exceed fp16's ~65504 max, producing NaN). See server/README.md
      for the full gotchas (Triton removal, Turing caveat).
    
    Current Status
    
    - [x] Project scaffold (pyproject.toml, src/somi/, hatchling build)
    - [x] Wake word detection (wake.py — sounddevice + openWakeWord)
    - [x] Capture with silence detection (VAD)
    - [x] STT (stt.py — faster-whisper)
    - [x] LLM client (llm.py — local + api toggle)
    - [x] TTS (tts/ — kokoro default + remote fallback)
    - [x] Orchestrator (main.py — full loop with sanitize step)
    - [ ] Conversation memory (multi-turn context in llm.py)
    - [ ] Custom "hey somi" wake word
    - [ ] Settings GUI (config form — PySide6)
    - [ ] Vision (screen awareness)
    
    GUI Vision (brainstorm)

    Voice-first stays the identity. The GUI is bolt-on usefulness, not a takeover —
    Somi speaks and listens first; the visual layer surfaces state and adds a few
    things that are genuinely easier with a screen.
    
    Three distinct layers, kept separate on purpose:
    
    1. Widget shell — the window itself. Effort: medium.
    2. Intent routing — weather/calendar skip the LLM. Effort: small but smart.
    3. Agent layer — chat box, file generation, sandbox. Effort: large + security.
    
    The Widget (layer 1)
    
    - Circular, resizable in fixed increments via +/- buttons (browser-zoom style).
    - Always-on-top, moveable, but click-through is NOT required — a normal window
      is acceptable if input-passthrough fights Wayland.
    - Visual states mirror the pipeline: listening / thinking / speaking / looking.
      (Already exists as prints in main.py; it's just a state machine + colors.)
    - Radial toggles extend out from the circle (bottom-left, bottom-right, etc.):
      - a ~720px vertical chat box (type instead of talk)
      - calendar button
      - settings button
    - When the chat box is open, a file section shows files Somi has created.
    
    Intent routing (layer 2)
    
    Weather and calendar lookups should NOT hit the LLM — they're deterministic
    fetches, and generating a sentence about the forecast is wasteful. Flow:
    
        STT → intent classifier → [weather tool | calendar tool | LLM]
    
    Slot extraction ("tomorrow in Dothan") may still need a cheap local parse, but
    the expensive generation is skipped. Google Calendar sync is the calendar source
    (OAuth + token handling — real integration work, deferred).
    
    Agent layer (layer 3)
    
    Letting the LLM write files turns Somi from assistant into agent. "Contained"
    means a sandbox: a dedicated directory, a permission model, and ideally an
    approve-before-write step. Ship the chat box WITHOUT file generation first; add
    the sandbox as its own sub-project.
    
    Open questions / deferred
    
    - Wayland click-through: not set in stone. If input-passthrough is painful, a
      plain always-on-top window is fine. Test early with a PySide6 prototype.
    - Toolkit: PySide6 assumed (Python-native, matches the sounddevice audio stack),
      but confirmed only when the widget prototype runs.
    - Is the circle a widget or window? Deferred until the click-through test.
