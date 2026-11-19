
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config.llm_settings import PROJECT_ROOT


EXPERIMENT_VERSION = "baseline_v1"


def calculate_sha256(content):
    """
    Calculate the SHA256 checksum of UTF-8 text.
    """
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def save_json(path, data):
    """
    Save a JSON file without altering its content.
    """
    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def record_experiment(result, version=EXPERIMENT_VERSION):
    """
    Save a complete LLM documentation experiment.

    Preserves:
    - System and user prompts
    - Structured evidence payload
    - Exact generated text
    - Raw provider response
    - Model configuration and usage
    - Experiment metadata and checksums

    Does not call an LLM or modify generated text.
    """

    component = result["component"]
    section = result["section"]
    prepared = result["prepared"]
    llm_result = result["llm_result"]

    metadata = dict(result["metadata"])

    provider = metadata["provider"]

    run_id = (
        datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        + "_"
        + uuid4().hex[:8]
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "experiments"
        / component
        / version
        / provider
        / section
        / run_id
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    system_prompt = prepared["system_prompt"]
    user_prompt = prepared["user_prompt"]
    generated_text = result["generated_text"]
    evidence_payload = prepared["evidence_payload"]

    # Preserve the exact prompts.
    (output_dir / "system_prompt.txt").write_text(
        system_prompt,
        encoding="utf-8",
    )

    (output_dir / "user_prompt.txt").write_text(
        user_prompt,
        encoding="utf-8",
    )

    # Preserve structured evidence.
    save_json(
        output_dir / "evidence_payload.json",
        evidence_payload,
    )

    # Preserve the messages sent to the model.
    save_json(
        output_dir / "messages.json",
        prepared["messages"],
    )

    # Preserve the unmodified model output.
    (output_dir / "generated_section.md").write_text(
        generated_text,
        encoding="utf-8",
    )

    # Preserve the original provider response.
    save_json(
        output_dir / "response.json",
        llm_result["raw_response"],
    )

    # Add experimental traceability information.
    metadata.update({
        "run_id": run_id,
        "experiment_version": version,
        "recorded_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "system_prompt_sha256": calculate_sha256(
            system_prompt
        ),
        "user_prompt_sha256": calculate_sha256(
            user_prompt
        ),
        "evidence_payload_sha256": calculate_sha256(
            json.dumps(
                evidence_payload,
                sort_keys=True,
                ensure_ascii=False,
            )
        ),
        "generated_text_sha256": calculate_sha256(
            generated_text
        ),
        "output_directory": str(output_dir),
    })

    save_json(
        output_dir / "metadata.json",
        metadata,
    )

    return output_dir
