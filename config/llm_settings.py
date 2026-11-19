
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    temperature: float
    max_output_tokens: int
    timeout: int
    ollama_base_url: str
    ollama_num_ctx: int


def get_llm_settings(provider=None):
    """
    Load LLM configuration from environment variables.

    Supported providers:
    - ollama
    - groq
    """

    selected_provider = (
        provider or os.getenv("LLM_PROVIDER", "ollama")
    ).strip().lower()

    if selected_provider not in {"ollama", "groq"}:
        raise ValueError(
            f"Unsupported provider: {selected_provider}"
        )

    if selected_provider == "groq":
        model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b"
        )
    else:
        model = os.getenv(
            "OLLAMA_MODEL",
            "llama3:8b"
        )

    return LLMSettings(
        provider=selected_provider,
        model=model,
        temperature=float(
            os.getenv("LLM_TEMPERATURE", "0")
        ),
        max_output_tokens=int(
            os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048")
        ),
        timeout=int(
            os.getenv("LLM_TIMEOUT", "600")
        ),
        ollama_base_url=os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434"
        ).rstrip("/"),
        ollama_num_ctx=int(
            os.getenv("OLLAMA_NUM_CTX", "8192")
        ),
    )
