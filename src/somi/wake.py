""""Wake word detection for Somi using openWakeWord."""

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

FRAME = 1280        # 80ms at 16kHz - openWakeWord's native frame size
THRESHOLD = 0.5

def listen_for_wake_word(
        wake_word: str = "hey_jarvis",
        threshold: float = THRESHOLD,
) -> None:
    """
    Blocks until the wake word is detected.

    Args:
        wake_word: Name of a built-in wake word model (e.g. "hey_jarvis",
                    "hey_mycroft", "alexa") or path to a custom .tflite/.onnx model
        threshold: Detection score 0.0 to 1.0, higher = fewer false positives
    """
    model = Model(
        wakeword_models=[wake_word],
        inference_framework="onnx",
    )

    stream = sd.RawInputStream(
        channels=1,
        samplerate=16000,
        dtype="int16",
        blocksize=FRAME,
    )

    print("Listening for wake word...")

    with stream:
        while True:
            data, _ = stream.read(FRAME)
            frame = np.frombuffer(data, dtype=np.int16)

            prediction = model.predict(frame)
            score = prediction[wake_word]

            if score >= threshold:
                print(f"Wake word detected! (score {score:.2f})")
                return

# Test block
if __name__ == "__main__":
    listen_for_wake_word()