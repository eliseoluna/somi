"""LLM client for Somi - local llama-server or cloud API via OpenAI-compatible HTTP"""

import os
from openai import OpenAI

DEFAULT_MODEL = "Qwen3.6-27B-Q4_K_M.gguf"       # whatever llama-server names the model

def get_llm_client() -> OpenAI:
    backend = os.getenv("SOMI_LLM_BACKEND", "local")

    if backend == "api":
        return OpenAI(
            base_url=os.getenv("SOMI_LLM_BASE_URL", "https://api.deepseek.com/v1"),
            api_key=os.getenv("SOMI_LLM_API_KEY"),           
        )
    # local (default)
    return OpenAI(
        base_url=os.getenv("SOMI_LLM_BASE_URL", "http://10.0.0.215:8080/v1"),
        api_key="not-needed",           # llama-server ignores it, but openai lib wants one
    )


def chat(text: str, client: OpenAI | None = None) -> str:
    client = client or get_llm_client()
    model = os.getenv("SOMI_LLM_MODEL", DEFAULT_MODEL)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    return response.choices[0].message.content

# Test block
if __name__ == "__main__":
    print(chat("Say hello in exactly three words."))