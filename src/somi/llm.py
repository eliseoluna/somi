"""LLM client for Somi - three way backend via OpenAI-compatible HTTP."""

from openai import OpenAI

from somi import settings

DEFAULT_MODEL = "Qwen3.6-27B-Q4_K_M.gguf"


def get_llm_client() -> OpenAI:
    backend = settings.get("llm", "backend")

    if backend == "api":
        return OpenAI(
            base_url=settings.get("llm", "base_url"),
            api_key=settings.get("llm", "api_key"),
        )

    # local and desktop both use llama-server (no key needed)
    return OpenAI(
        base_url=settings.get("llm", "base_url"),
        api_key="not-needed",   # llama-server ignores it, but openai lib wants one
    )


SYSTEM_PROMPT = (
    "You are Somi, a voice assistant. Respond in plain spoken English, "
    "no more than 2-3 sentences. No markdown, no emoji, no LaTeX, no "
    "bullet points, no symbols or specials characters - only words exactly "
    "as they would be spoken aloud."
)


def chat(text: str, client: OpenAI | None = None) -> str:
    client = client or get_llm_client()
    model = settings.get("llm", "model")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content

# Test block
if __name__ == "__main__":
    print(chat("Say hello in exactly three words."))