"""Playback for Somi using sounddevice"""

import io

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.signal import resample_poly


def _device_sample_rate() -> int | None:
    """Best-effort device sample rate; None if underterminable."""
    try:
        return int(sd.query_devices(kind="output")["default_samplerate"])
    except Exception:
        return None

def play(wav_bytes: bytes, sample_rate: int) -> None:
    audio, _ = sf.read(io.BytesIO(wav_bytes), dtype="float32")

    # Resample once up front so the OS does zero real-time resampling
    # Kokoro outputs 24kHz; most devices run 44.1/48kHz. Converting here
    # (instead of letting PipeWire do it live under load) is what makes
    # playback stable even when other audio is playing.
    device_rate = _device_sample_rate()
    if device_rate and device_rate != sample_rate:
        gcd = np.gcd(device_rate, sample_rate)
        audio = resample_poly(audio, device_rate // gcd, sample_rate // gcd)
        audio = audio.astype(np.float32)
        sample_rate = device_rate

    sd.play(audio, samplerate=sample_rate, blocksize=4096, latency="high")
    sd.wait()