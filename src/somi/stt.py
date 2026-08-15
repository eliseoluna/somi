"""Speech-to-text transcription for Somi using faster-whisper"""

from faster_whisper import WhisperModel

MODEL_SIZE = "small"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

_model = None

def load_model(model_size: str = MODEL_SIZE) -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(model_size, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model

def transcribe(audio) -> str:
    model = load_model()
    segments, info = model.transcribe(audio, beam_size=5)
    text = "".join(segment.text for segment in segments)
    return text.strip()

# Test block
if __name__ == "__main__":
    from somi.capture import record_until_silence
    print("Speak...")
    audio = record_until_silence()
    print("Transcribing...")
    text = transcribe(audio)
    print(f"You said: {text}")