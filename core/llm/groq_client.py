
import os

from groq import Groq

from config.llm_settings import get_llm_settings


def generate_with_groq(messages, settings=None):
    """
    Generate text using the Groq Chat Completions API.

    Args:
        messages: Chat messages with role and content.
        settings: Optional LLMSettings instance.

    Returns:
        A normalized generation result.
    """

    if settings is None:
        settings = get_llm_settings("groq")

    if settings.provider != "groq":
        raise ValueError("Groq settings are required")

    if not messages:
        raise ValueError("Messages cannot be empty")

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or api_key == "your_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is missing or not configured"
        )

    client = Groq(
        api_key=api_key,
        timeout=settings.timeout,
    )

    response = client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=settings.temperature,
        max_completion_tokens=settings.max_output_tokens,
        stream=False,
    )

    if not response.choices:
        raise RuntimeError("Groq returned no completion choices")

    choice = response.choices[0]
    message = choice.message
    usage = response.usage

    return {
        "provider": "groq",
        "model": response.model,
        "content": message.content or "",
        "finish_reason": choice.finish_reason,
        "usage": {
            "input_tokens": (
                usage.prompt_tokens if usage else None
            ),
            "output_tokens": (
                usage.completion_tokens if usage else None
            ),
            "total_tokens": (
                usage.total_tokens if usage else None
            ),
        },
        "parameters": {
            "temperature": settings.temperature,
            "max_completion_tokens": settings.max_output_tokens,
        },
        "raw_response": response.model_dump(mode="json"),
    }
