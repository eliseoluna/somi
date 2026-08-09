""""Wake word detection for Somi using Porcupine."""

import struct
import pvporcupine
import sounddevice as sd

def listen_for_wake_word(
        access_key: str,
        keyword_path: str | None = None,
        sensitivity: float = 0.7,
) -> None:
    """
    Blocks until the wake word is detected.

    Args:
        access_key: Free Picovoice key from picovoice.ai (sign up, copy from console)
        keyword_path: Path to custom wake word .ppn file, or None for built-in
        sensitivity: 0.0 to 1.0 - higher = more sensitive, more false positive
    """
    # Step 1: create the wake word detector
    if keyword_path:
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path],
            sensitivities=[sensitivity],
        )
    else:
        # Fall back to built-in "Porcupine" wake word for testing
        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=["porcupine"],
            sensitivities=[sensitivity],
        )

    # Step 2: open the microphone
    stream = sd.RawInputStream(
        channels=1,
        samplerate=porcupine.sample_rate,
        dtype="int16",
        blocksize=porcupine.frame_length,
    )

    print("Listening for wake word...")

    with stream:
        while True:
            data, _ = stream.read(porcupine.frame_length)
            pcm = struct.unpack_from("h" * porcupine.frame_length, data)

            if porcupine.process(pcm) >= 0:
                print("Wake word detected!")
                return