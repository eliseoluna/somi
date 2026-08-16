"""TTS engine interface"""

from typing import Protocol


class TTSEngine(Protocol):
    def synthesize(self, text: str) -> tuple[bytes, int]:
        """Return (wav_bytes, sample_rate)."""
        ...
        