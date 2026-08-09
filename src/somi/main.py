def main():
    init_wake_word()
    init_stt()          # load whisper once
    init_tts()          # load Qwen3-TTS once
    init_llm()          # connect to Titan box (just and HTTP client)

    while true:
        wait_for_wake_word("Hey Somi")      # SLEEP
        audio = record_until_silence()      # LISTEN
        text = stt(audio)                   # THINK (part 1)
        response = llm(text)                # THINK (part 2)
        audio = tts(response)               # THINK (part 3)
        play(audio)                         # SPEAK