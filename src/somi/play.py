"""Playback for Somi using sounddevice"""

import io

import numpy as np
import sounddevice as sd
import soundfile as sf


def play(wav_bytes: bytes, sample_rate: int) -> None:
    audio, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
    