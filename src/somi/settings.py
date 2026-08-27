"""Config loading module for Somi - TOML file with env-var override.

Precedence (highest first):
    1. env var SOMI_<SECTION>_<KEY>     (e.g SOMI_LLM_BACKEND)
    2. config.toml
    3. built-in default

The config file lives at ~/.config/somi/config.toml (XDG), override with
SOMI_CONFIG. The file is machine-specific and stays out of git; see
config.example.toml for the documented template.
"""

import os
import tomllib
from pathlib import Path

DEFAULTS = {
    "llm": {
        "backend": "local",                         # local | api | desktop
        "base_url": "http://10.0.0.215:8080/v1",
        "api_key": "",
        "model": "Qwen3.6-27B-Q4_K_M.gguf",
    },
    "tts": {
        "backend": "kokoro",                        # kokoro | remote
        "url": "http://10.0.0.215:8081/v1/audio/speech",
        "kokoro_model": "~/.config/somi/kokoro/kokoro-v1.0.onnx",
        "kokoro_voices": "~/.config/somi/kokoro/voices-v1.0.bin",
        "voice": "af_heart",
        "lang": "en-us",
    },
    "wake": {
        "word": "hey_jarvis",
    },
    "service": {
        "llama_server_bin": "llama-server",
        "model_path": "",
        "context": "8192",
    }
}

def _config_path() -> Path:
    env = os.getenv("SOMI_CONFIG")
    if env:
        return Path(env)
    return Path.home() / ".config" / "somi" / "config.toml"

def _load_toml() -> dict:
    path = _config_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)

def load() -> dict:
    """Return the merged config: defaults overlaid with config.toml values."""
    data = {section: dict(values) for section, values in DEFAULTS.items()}
    toml = _load_toml()
    for section, values in toml.items():
        if section in data:
            data[section].update(values)
    return data

def get(section: str, key: str) -> str:
    """Resolve one setting: env var > config.toml > default."""
    env_key = f"SOMI_{section.upper()}_{key.upper()}"
    if os.getenv(env_key):
        return os.getenv(env_key)

    value = load()[section].get(key, DEFAULTS[section].get(key, ""))
    # expand ~ in paths
    if isinstance(value, str) and value.startswith("~/"):
        value = os.path.expanduser(value)
    return str(value)
