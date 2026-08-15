"""Audio capture with silence-based endpoint detection for Somi"""

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000     # matches Porcupine and faster-whisper
FRAME = 512             # 32ms per frame at 16kHz

def record_until_silence(threshold_db=-40.0, silence_sec=0.7, max_sec=20.0):
    silent = 0
    has_speech = False
    silence_limit = int(silence_sec / (FRAME / SAMPLE_RATE))
    max_frames = int(max_sec / (FRAME / SAMPLE_RATE))
    chunks = []

    with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1,
                           dtype="int16", blocksize=FRAME) as stream:
        while len(chunks) < max_frames:
            data, _ = stream.read(FRAME)
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            chunks.append(audio)
            rms = np.sqrt(np.mean(audio ** 2))
            db = 20 * np.log10(rms + 1e-9)

            if db > threshold_db:
                has_speech = True
                silent = 0
            elif has_speech:
                silent += 1

            if has_speech and silent >= silence_limit:
                break

    return np.concatenate(chunks)

# Test block
if __name__ == "__main__":
    audio = record_until_silence()
    print(f"Captured {len(audio) / SAMPLE_RATE:.1f} seconds")
    
