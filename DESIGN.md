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
    
    
    loop:
        wait_for_wake_word()            # SLEEP  — openWakeWord blocks until wake word
        audio = record_until_silence()  # LISTEN — capture with VAD endpoint detection
        text = stt(audio)               # THINK  — faster-whisper, local CPU
        response = llm(text)            # THINK  — local/desktop/cloud (toggle)
        response = sanitize(response)   # THINK  — strip emoji/symbols so TTS won't crash
        speech = tts(response)          # THINK  — Kokoro (default) OR remote Qwen3-TTS
        play(speech)                    # SPEAK  — sounddevice playback
    
    
    Models load lazily on first use (whisper on first transcribe, Kokoro on first
    synthesize), so idle Somi holds only the tiny wake-word model — near-zero
    resource footprint for the on/off switch.
    
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
    | LLM (alt) | llama-server (local) | Desktop          | LM Studio / Vulkan, or NVIDIA GPU         |
    | TTS       | Kokoro-82M           | Desktop (CPU)    | Fast, natural, no server                  |
    | TTS (alt) | Qwen3-TTS (remote)   | LLM Box (CUDA)   | Highest quality; bfloat16, optional       |
    | Vision    | mmproj or Florence-2 | Desktop/Titan    | Planned — screen awareness, not started   |
    
    Config & Settings
    
    Config lives in ~/.config/somi/config.toml (XDG), loaded by settings.py with
    three-layer precedence:
    
        env var (SOMI_<SECTION>_<KEY>)  >  config.toml  >  built-in default
    
    The file is machine-specific and stays out of git (see config.example.toml for
    the documented template). SOMI_CONFIG overrides the file location.
    
    LLM backend — three-way
    
    Same OpenAI-compatible client for all three; only the base URL / key change.
    
        backend = "local"      # llama-server on the LLM Box over LAN (default)
        backend = "api"        # any OpenAI-compatible cloud API
        backend = "desktop"    # llama-server / LM Studio on this machine
    
    - local   → base_url = http://<llm-box>:8080/v1, no key
    - api     → base_url = https://api.deepseek.com/v1, api_key = ***
    - desktop → base_url = http://localhost:1234/v1 (LM Studio), no key
    
    The client code is identical; a factory (get_llm_client()) picks the base URL.
    All three accept the same messages list, which is what makes the RAG layer
    (see below) backend-agnostic.
    
    TTS backend — kokoro vs remote
    
        backend = "kokoro"     # Kokoro-82M on desktop CPU (default)
        backend = "remote"     # HTTP call to Qwen3-TTS server on the LLM Box
    
    - kokoro → local ONNX model, no server, fast, natural
    - remote → url = http://<llm-box>:8081/v1/audio/speech
    
    
    somi/tts/
      init.py     # factory: get_tts_backend()
      base.py         # TTSEngine abstract: synthesize(text) -> (wav_bytes, sample_rate)
      kokoro.py       # Kokoro-82M (desktop CPU, default)
      remote.py       # HTTP client to LLM Box TTS server
    
    
    Conversation Memory
    
    chat() keeps a module-level _history list of {"role", "content"} dicts,
    capped at MAX_HISTORY_MESSAGES = 10 (~5 exchanges) to keep context small.
    clear_history() resets it. History stores the raw LLM reply; sanitization stays
    in main.py so only TTS is affected, not the LLM's context.
    
    Service Lifecycle
    
    service.py manages a local llama-server process for the desktop backend —
    start/stop/restart/is_running, with a pidfile so start and stop work across
    separate processes. Remote services (Titan's llama-server, somi-tts) are systemd
    units on another box and are out of scope. This is the muscle behind the future
    GUI on/off switch and model manager.
    
    Decision Log
    
    - openWakeWord for wake word — local, low-latency, MIT, no account and no API
      key (replaced Porcupine, which was key-gated and closed-source). Built-in wake
      word (hey_jarvis) for now; a custom "hey somi" model is next.
    - faster-whisper for STT — CTranslate2 backend is much faster on CPU than
      stock Whisper; no GPU required, so it stays on the desktop.
    - Qwen3.6-27B (Q4_K_M) for the LLM — the only machine that fits it is the LLM
      Box. Served over the LAN by llama-server (systemd) rather than loaded into the
      desktop process.
    - OpenAI-compatible HTTP everywhere — llama-server and LM Studio both expose
      /v1/chat/completions, which means the LLM client is identical whether the brain
      is local, desktop, or a cloud API. This is what makes the toggle trivial and the
      RAG layer backend-agnostic.
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
    - config.toml + settings.py — moved config out of env-var-only into a TOML
      file with env-var override, so the settings GUI is just a form over a file.
      Also removed hardcoded paths/keys from committed code.
    - Lazy model loading — whisper and Kokoro load on first use, so idle Somi
      uses near-zero resources. This is what makes the on/off switch trivial.
    - Resample-to-device-rate playback — Kokoro outputs 24kHz but devices run
      44.1/48kHz; resampling once up front (scipy) instead of letting PipeWire do it
      live under load eliminated choppy/stretched audio when other sources play.
    
    Current Status
    
    - [x] Project scaffold (pyproject.toml, src/somi/, hatchling build)
    - [x] Wake word detection (wake.py — sounddevice + openWakeWord)
    - [x] Capture with silence detection (VAD)
    - [x] STT (stt.py — faster-whisper)
    - [x] LLM client (llm.py — three-way backend toggle)
    - [x] TTS (tts/ — kokoro default + remote fallback)
    - [x] Orchestrator (main.py — full loop with sanitize step)
    - [x] Conversation memory (multi-turn context in llm.py)
    - [x] Three-way LLM backend (desktop option, tested via LM Studio)
    - [x] Service lifecycle manager (service.py)
    - [ ] Custom "hey somi" wake word  ← NEXT
    - [ ] Intent routing (weather + calendar tools)
    - [ ] RAG layer (retrieval + injection)
    - [ ] GUI state 3 (normal window: settings, chat, RAG tabs)
    - [ ] GUI states 1+2 (overlay: circle + popups, layer-shell)
    - [ ] Vision (screen awareness)
    - [ ] Sentry mode (post-vision)
    - [ ] .somi file format (post-vision/GUI)
    
    GUI Vision
    
    Voice-first stays the identity. The GUI is bolt-on usefulness, not a takeover —
    Somi speaks and listens first; the visual layer surfaces state and adds the
    things that are easier with a screen.
    
    The Three States
    
    
    State 1 — circle (resting)      State 2 — popup (glance)      State 3 — full window
    
    
    | State | What it is                        | Content                                            |
    |-------|-----------------------------------|----------------------------------------------------|
    | 1     | Small circle, always-on-top       | Resize (+/-), expand, weather, calendar, on/off    |
    | 2     | Small popup docked next to circle | Response text, or weather/calendar glance          |
    | 3     | Normal window                     | Settings, chat history, RAG, full weather/calendar |
    
    Transitions:
    
    - 1 -> 2 : triggered by the voice loop (Somi speaks) OR user click (weather/calendar)
    - 1 -> 3 : user clicks expand (the ONLY way into state 3)
    - 3 -> 1 : user collapses, or auto after idle
    - 2 -> 1 : Somi finishes speaking, or user dismisses
    
    Glance vs Full
    
    Every feature gets two renderings — the organizing principle of the whole GUI:
    
    - Glance (state 2): at-a-glance, minimal interaction
    - Full (state 3): the tab where you actually do things
    
    Weather: glance = current + today; full = change location, extended forecast.
    Calendar: glance = today/next events; full = create/edit events + reminders.
    Response: glance = the popup; full = chat history tab.
    
    Two kinds of state-2 popups (different plumbing)
    
    - Automatic — Somi's response. Triggered by the voice loop (external event).
      Rides the publish/subscribe IPC seam.
    - Clicked — weather/calendar. Triggered by the user inside the GUI.
      Pure GUI-internal state, no IPC needed.
    
    Same visual language, different event sources. Don't conflate them in code.
    
    Two windows under the hood
    
    States 1+2 are a floating overlay; state 3 is a normal window. Qt can't live-swap
    FramelessWindowHint + WindowStaysOnTopHint for a normal window, so it's two
    top-level windows, never visible at once:
    
    - Overlay window: frameless, always-on-top -> circle (state 1) + popups (state 2)
    - Main window: normal, resizable -> everything in state 3
    
    Expanding hides the overlay and shows the main window; collapsing reverses it.
    
    Wayland reality
    
    State 3 is easy (normal window). States 1+2 are hard: a frameless always-on-top
    circle that stays put in a corner needs the layer-shell protocol (what dunst and
    waybar use). Build order is therefore the reverse of visual order:
    
    1. State 3 (normal window) — the functional heart, easy, forces the IPC plumbing
    2. States 1+2 (overlay) — layer-shell / corner positioning, cosmetics on top
    
    Button set (state 1)
    
    - Resize (+/-) — browser-zoom style, fixed increments
    - Expand — the only path into state 3 (settings, chat, RAG all live there)
    - Weather — glance popup
    - Calendar — glance popup
    - On/off — the hybrid toggle (below), duplicated in settings
    
    On/off switch (hybrid)
    
    Present on the circle AND in settings. Two independent settings:
    
    - Brain switch: local / api / desktop
    - Server on/off + fallback: if the local brain is off, either fall back to
      cloud api automatically, or report "brain offline" — user choice.
    
    Built on service.py (start/stop the local server) + the backend config.
    
    Dependency: intent routing comes first
    
    Weather and calendar glance views are NOT cosmetic — they render data from the
    weather tool + Google Calendar sync. So the tools (layer 2) must exist before
    the glance views. Realistic build order:
    
    1. Response popup (automatic state 2) — can build now, just renders LLM text
    2. State 3 skeleton — normal window, tabs, no live data yet
    3. Weather + calendar tools (intent routing)
    4. Glance views + circle — render the tools; the hard Wayland work, last
    
    Process split
    
    The voice loop and the GUI stay separate processes. The loop publishes state
    messages ({"state": "speaking", "text": "..."}); the GUI subscribes and
    renders. Somi runs fine headless (no GUI) or with the notifier attached.
    
    RAG (brainstorm)
    
    Retrieval-augmented generation so Somi can answer from your own documents,
    notes, and code. One retrieval layer serves all three LLM backends, because all
    three are OpenAI-compatible and accept the same messages list.
    
    - Retrieval is local: embeddings + a vector store on the desktop.
    - Injection is identical regardless of backend: prepend the top-k retrieved
      chunks to the messages list before calling chat().
    - No server-side RAG needed — the desktop retrieves and injects before sending,
      whether the backend is api, local, or desktop.
    
        query -> embed -> vector search -> inject top-k -> chat(messages)
    
    Near-term: build the retrieval + injection layer. Deferred: fancy chunking,
    hybrid search, re-ranking, server-side RAG for large corpora.
    
    Sentry Mode (brainstorm, post-vision)
    
    Unattended-space monitoring. A hybrid detector -> captioner pipeline:
    
    - YOLO watches the video stream cheaply (object detection). Fast but "dumb" —
      it flags "person detected" without describing what's happening.
    - Florence-2 provides the detailed description, triggered only when YOLO sees
      something of interest.
    
        camera -> YOLO (fast, always-on) -> [interesting event] -> Florence-2 -> log/alert
    
    - Compatible with PTZ webcams (e.g. Insta360) that can pan to look around.
      Note: PTZ control is a camera-integration concern, separate from the vision
      pipeline.
    - Reality check: YOLO at 60fps is optimistic on the 9600X CPU (~15-30fps);
      60fps needs a GPU (the Titan over LAN, or a future card).
    - Privacy: monitoring a shared space (roommates) needs clear consent surfaced
      in the UI, not just the code.
    
    .somi File Format (brainstorm, post-vision/GUI)
    
    A portable, encrypted container for sharing Somi's output (context, files, voice
    notes) between Somi instances.
    
    - Compression: zstd (easy).
    - Encryption: the real work is KEY EXCHANGE, not the cipher. Options:
      - shared passphrase -> symmetric (simplest; chacha20-poly1305 or age)
      - per-recipient keys -> asymmetric/PKI (proper, but a real project)
    - Framing: it's "encrypted-at-rest, shareable bundle of context + files", not
      merely "a file format". The cipher is ~10% of the work; key exchange is 90%.

