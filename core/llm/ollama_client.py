
import json
from urllib.request import Request, urlopen

from config.llm_settings import get_llm_settings


def generate_with_ollama(messages, settings=None):
    """
    Generate text using a local Ollama model.

    Args:
        messages: Chat messages with role and content.
        settings: Optional LLMSettings instance.

    Returns:
        A normalized generation result.
    """

    if settings is None:
        settings = get_llm_settings("ollama")

    if settings.provider != "ollama":
        raise ValueError("Ollama settings are required")

    if not messages:
        raise ValueError("Messages cannot be empty")

    request_payload = {
        "model": settings.model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": settings.temperature,
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": settings.max_output_tokens,
        },
    }

    request = Request(
        url=f"{settings.ollama_base_url}/api/chat",
        data=json.dumps(
            request_payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    with urlopen(
        request,
        timeout=settings.timeout,
    ) as response:
        raw_response = json.load(response)

    message = raw_response.get("message") or {}

    return {
        "provider": "ollama",
        "model": raw_response.get("model", settings.model),
        "content": message.get("content") or "",
        "finish_reason": raw_response.get("done_reason"),
        "usage": {
            "input_tokens": raw_response.get("prompt_eval_count"),
            "output_tokens": raw_response.get("eval_count"),
            "total_duration_ns": raw_response.get("total_duration"),
            "prompt_duration_ns": raw_response.get(
                "prompt_eval_duration"
            ),
            "generation_duration_ns": raw_response.get(
                "eval_duration"
            ),
        },
        "parameters": request_payload["options"],
        "raw_response": raw_response,
    }
