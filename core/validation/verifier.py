@'
import json
import uuid
import re
import time
import traceback

from pathlib import Path
from datetime import datetime, timezone

from config.settings import (
    INTERMEDIATE_DIR,
    RAG_ENABLED,
    RAG_SECTIONS,
    COMPONENT_TOP_K,
)

from config.llm_settings import get_llm_settings

from config.prompts import compact_retrieved_context

from core.evidence.evidence_selector import (
    build_mathematical_evidence,
)

from core.generation.documentation_generator import (
    generate_documentation_section,
)


# ==================================================
# 1. Experiment configuration
# ==================================================

COMPONENTS = [
    "BDFIntegrationScheme",
    "NewmarkIntegrationScheme",
    "NewtonRaphsonSolver",
    "CGLinearSolver",
    "PCGLinearSolver",
    "BarycentricMapping",
]

EXPERIMENT_VERSION = "mathematical_formulation_v3"
PROMPT_VERSION = "v1"
EVIDENCE_VARIANT = "optimized_mathematical_evidence"

PROVIDER = "groq"
SECTION = "mathematical_formulation"

SLEEP_SECONDS = 15

settings = get_llm_settings(PROVIDER)

assert settings.model == "openai/gpt-oss-120b"
assert settings.temperature == 0.0
assert settings.max_output_tokens == 3072

assert RAG_ENABLED
assert SECTION in RAG_SECTIONS
assert COMPONENT_TOP_K == 3


# ==================================================
# 2. Utility functions
# ==================================================

def save_json(path, data):

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def compact_size(value):

    return len(json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ))


def create_run_id():

    return (
        datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        + "_"
        + uuid.uuid4().hex[:8]
    )


# ==================================================
# 3. Expected documentation structure
# ==================================================

REQUIRED_TITLE = "# Mathematical Formulation"

REQUIRED_HEADINGS = [
    "## Mathematical Problem",
    "## Mathematical Formulation",
    "## Numerical Algorithm",
]


def validate_structure(generated_text):

    generated_titles = []
    generated_headings = []

    inside_code_block = False

    for line in generated_text.splitlines():

        stripped = line.strip()

        if stripped.startswith("```"):

            inside_code_block = not inside_code_block

            continue

        if inside_code_block:
            continue

        if re.match(r"^#\s+", stripped):

            generated_titles.append(stripped)

        elif re.match(r"^##\s+", stripped):

            generated_headings.append(stripped)

    title_complete = (
        generated_titles == [REQUIRED_TITLE]
    )

    structure_complete = (
        title_complete
        and generated_headings == REQUIRED_HEADINGS
    )

    missing_headings = [
        heading
        for heading in REQUIRED_HEADINGS
        if heading not in generated_headings
    ]

    unexpected_headings = [
        heading
        for heading in generated_headings
        if heading not in REQUIRED_HEADINGS
    ]

    return {
        "title_complete": title_complete,
        "structure_complete": structure_complete,
        "generated_titles": generated_titles,
        "generated_headings": generated_headings,
        "missing_headings": missing_headings,
        "unexpected_headings": unexpected_headings,
    }


# ==================================================
# 4. Display experiment configuration
# ==================================================

print("=" * 70)
print("MATHEMATICAL FORMULATION V3")
print("=" * 70)

print("[EXPERIMENT]", EXPERIMENT_VERSION)
print("[SECTION]", SECTION)
print("[PROVIDER]", PROVIDER)
print("[MODEL]", settings.model)
print("[TEMPERATURE]", settings.temperature)
print("[MAX OUTPUT TOKENS]", settings.max_output_tokens)

print("[PROMPT VERSION]", PROMPT_VERSION)
print("[EVIDENCE VARIANT]", EVIDENCE_VARIANT)

print("[GENERAL RAG]", False)
print("[GENERAL TOP K]", 0)

print("[COMPONENT RAG]", True)
print("[COMPONENT TOP K]", COMPONENT_TOP_K)

print("[CODE SNIPPETS]", False)
print("[CODE CHUNKS]", False)
print("[CONSTRUCTOR BODIES]", False)

print("[COMPONENTS]", len(COMPONENTS))
print("[SLEEP SECONDS]", SLEEP_SECONDS)

print("=" * 70)


# ==================================================
# 5. Experiment summaries
# ==================================================

summary = []

experiment_started_at = time.perf_counter()


# ==================================================
# 6. Generate documentation
# ==================================================

for index, component in enumerate(
    COMPONENTS,
    start=1,
):

    print("\n" + "=" * 70)

    print(
        f"[{index}/{len(COMPONENTS)}] "
        f"{component}"
    )

    print("=" * 70)

    run_id = create_run_id()

    output_dir = (
        Path("data/experiments")
        / component
        / EXPERIMENT_VERSION
        / PROVIDER
        / SECTION
        / run_id
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:

        # ==========================================
        # 6.1. Load existing Evidence Pack
        # ==========================================

        evidence_path = (
            INTERMEDIATE_DIR
            / component
            / "evidence_pack.json"
        )

        evidence_pack = json.loads(
            evidence_path.read_text(
                encoding="utf-8"
            )
        )

        assert evidence_pack["component"] == component

        print(
            "[CODE COMMIT]",
            evidence_pack["provenance"]["code_commit"],
        )


        # ==========================================
        # 6.2. Build optimized mathematical evidence
        # ==========================================

        payload = build_mathematical_evidence(
            evidence_pack
        )

        assert not payload.get("code_snippets")
        assert not payload.get("code_chunks")
        assert not payload.get("constructor_metadata")
        assert not payload.get("constructor_evidence")

        payload_characters = compact_size(payload)

        documentation = payload.get(
            "official_documentation",
            {},
        )

        equations = [
            item
            for item in documentation.get(
                "introduction", []
            )
            if item.get("type") == "equation"
        ]

        equations.extend([
            item
            for section in documentation.get(
                "sections", []
            )
            for item in section.get(
                "content", []
            )
            if item.get("type") == "equation"
        ])

        evidence_statistics = {

            "method_links": len(
                payload.get("method_links", [])
            ),

            "structured_attributes": len(
                payload.get("structured_attributes", [])
            ),

            "code_snippets": len(
                payload.get("code_snippets", [])
            ),

            "code_chunks": len(
                payload.get("code_chunks", [])
            ),

            "documentation_sections": len(
                documentation.get("sections", [])
            ),

            "official_equations": len(equations),

            "source_files": len(
                payload.get("source_files", {})
            ),
        }

        print(
            "[PAYLOAD CHARACTERS]",
            payload_characters,
        )

        for key, value in evidence_statistics.items():

            print(
                f"[{key.upper()}]",
                value,
            )

        save_json(
            output_dir / "evidence_payload.json",
            payload,
        )

        save_json(
            output_dir / "evidence_statistics.json",
            evidence_statistics,
        )


        # ==========================================
        # 6.3. Generate documentation
        # ==========================================

        print("[GENERATION] Starting...")

        result = generate_documentation_section(
            component=component,
            evidence_pack=evidence_pack,
            section=SECTION,
            provider=PROVIDER,
        )

        prepared = result["prepared"]
        metadata = result["metadata"]
        generated_text = result["generated_text"]

        retrieved_context = (
            prepared.get("retrieved_context") or {}
        )

        retrieval_queries = prepared.get(
            "retrieval_queries", []
        )

        general_chunks = retrieved_context.get(
            "general", []
        )

        component_chunks = retrieved_context.get(
            "component_specific", []
        )

        assert prepared["evidence_payload"] == payload

        assert prepared["rag_active"]

        assert not general_chunks, (
            "General RAG must be disabled"
        )

        assert len(component_chunks) <= COMPONENT_TOP_K

        assert component_chunks, (
            "No component-specific scientific context retrieved"
        )

        print("[RAG ACTIVE]", prepared["rag_active"])

        print("[GENERAL CHUNKS]", len(general_chunks))

        print("[COMPONENT CHUNKS]", len(component_chunks))


        # ==========================================
        # 6.4. Analyze actual message size
        # ==========================================

        system_characters = len(
            prepared["system_prompt"]
        )

        user_characters = len(
            prepared["user_prompt"]
        )

        total_message_characters = sum(
            len(message["content"])
            for message in prepared["messages"]
        )

        estimated_input_tokens = round(
            total_message_characters / 4
        )

        print(
            "[SYSTEM PROMPT CHARACTERS]",
            system_characters,
        )

        print(
            "[USER PROMPT CHARACTERS]",
            user_characters,
        )

        print(
            "[TOTAL MESSAGE CHARACTERS]",
            total_message_characters,
        )

        print(
            "[ESTIMATED INPUT TOKENS]",
            estimated_input_tokens,
        )


        # ==========================================
        # 6.5. Validate document structure
        # ==========================================

        validation = validate_structure(
            generated_text
        )

        status = (
            "GENERATED"

            if (
                metadata["finish_reason"] == "stop"
                and generated_text.strip()
                and validation["structure_complete"]
            )

            else "REVIEW_REQUIRED"
        )


        # ==========================================
        # 6.6. Update experiment metadata
        # ==========================================

        metadata.update({

            "experiment_version":
                EXPERIMENT_VERSION,

            "prompt_version":
                PROMPT_VERSION,

            "evidence_variant":
                EVIDENCE_VARIANT,

            "run_id":
                run_id,

            "status":
                status,

            "previous_experiment":
                "mathematical_formulation_v1",

            "optimization":
                "Disable general scientific RAG",

            "word_count":
                len(generated_text.split()),

            "payload_characters":
                payload_characters,

            "system_prompt_characters":
                system_characters,

            "user_prompt_characters":
                user_characters,

            "total_message_characters":
                total_message_characters,

            "estimated_input_tokens":
                estimated_input_tokens,

            "evidence_statistics":
                evidence_statistics,

            "general_top_k":
                0,

            "component_top_k":
                COMPONENT_TOP_K,

            "scientific_rag_enabled":
                prepared["rag_active"],

            "general_rag_enabled":
                False,

            "component_rag_enabled":
                True,

            "official_documentation_enabled":
                True,

            "code_snippets_enabled":
                False,

            "code_chunks_enabled":
                False,

            "constructor_bodies_enabled":
                False,

            "method_links_enabled":
                True,

            "structured_attributes_enabled":
                True,

            "sleep_seconds":
                SLEEP_SECONDS,

            "validation_level":
                "generation_and_structure_only",

            **validation,

        })


        # ==========================================
        # 6.7. Save all experiment artifacts
        # ==========================================

        (
            output_dir / "system_prompt.txt"
        ).write_text(
            prepared["system_prompt"],
            encoding="utf-8",
        )

        (
            output_dir / "user_prompt.txt"
        ).write_text(
            prepared["user_prompt"],
            encoding="utf-8",
        )

        save_json(
            output_dir / "messages.json",
            prepared["messages"],
        )

        save_json(
            output_dir / "evidence_payload.json",
            prepared["evidence_payload"],
        )

        save_json(
            output_dir / "retrieval_queries.json",
            retrieval_queries,
        )

        save_json(
            output_dir / "retrieved_context.json",
            retrieved_context,
        )

        save_json(
            output_dir / "compact_context.json",
            compact_retrieved_context(
                retrieved_context
            ),
        )

        save_json(
            output_dir / "response.json",
            result["llm_result"],
        )

        save_json(
            output_dir / "metadata.json",
            metadata,
        )

        (
            output_dir / "generated_section.md"
        ).write_text(
            generated_text,
            encoding="utf-8",
        )


        # ==========================================
        # 6.8. Display component results
        # ==========================================

        print("\n" + "-" * 70)
        print("COMPONENT GENERATION SUMMARY")
        print("-" * 70)

        print("[COMPONENT]", component)
        print("[STATUS]", status)

        print(
            "[STRUCTURE COMPLETE]",
            validation["structure_complete"],
        )

        print(
            "[MISSING HEADINGS]",
            validation["missing_headings"],
        )

        print(
            "[UNEXPECTED HEADINGS]",
            validation["unexpected_headings"],
        )

        print(
            "[WORDS]",
            metadata["word_count"],
        )

        print(
            "[FINISH REASON]",
            metadata["finish_reason"],
        )

        print(
            "[USAGE]",
            metadata["usage"],
        )

        print(
            "[PREPARATION SECONDS]",
            metadata["preparation_seconds"],
        )

        print(
            "[GENERATION SECONDS]",
            metadata["elapsed_seconds"],
        )

        print(
            "[TOTAL SECONDS]",
            metadata["total_elapsed_seconds"],
        )

        print("[SAVED]", output_dir)

        summary.append({

            "component": component,

            "status": status,

            "run_id": run_id,

            "finish_reason":
                metadata["finish_reason"],

            "structure_complete":
                validation["structure_complete"],

            "word_count":
                metadata["word_count"],

            "payload_characters":
                payload_characters,

            "total_message_characters":
                total_message_characters,

            "usage":
                metadata["usage"],

            "general_chunks":
                len(general_chunks),

            "component_chunks":
                len(component_chunks),

            "elapsed_seconds":
                metadata["elapsed_seconds"],

            "output_dir":
                str(output_dir),

        })


    # ==============================================
    # 7. Handle generation errors
    # ==============================================

    except Exception as error:

        print("[ERROR]", str(error))

        error_details = {

            "component": component,

            "section": SECTION,

            "experiment_version":
                EXPERIMENT_VERSION,

            "prompt_version":
                PROMPT_VERSION,

            "evidence_variant":
                EVIDENCE_VARIANT,

            "provider": PROVIDER,

            "model": settings.model,

            "temperature": settings.temperature,

            "max_output_tokens":
                settings.max_output_tokens,

            "general_top_k": 0,

            "component_top_k":
                COMPONENT_TOP_K,

            "run_id": run_id,

            "status": "FAILED",

            "error_type":
                type(error).__name__,

            "error":
                str(error),

            "traceback":
                traceback.format_exc(),

            "timestamp_utc":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "output_dir":
                str(output_dir),

        }

        save_json(
            output_dir / "error.json",
            error_details,
        )

        save_json(
            output_dir / "metadata.json",
            error_details,
        )

        summary.append(error_details)

        print("[STATUS] FAILED")

        print("[ERROR SAVED]", output_dir)


    # ==============================================
    # 8. Delay between generations
    # ==============================================

    if index < len(COMPONENTS):

        print(
            f"\n[SLEEP] "
            f"{SLEEP_SECONDS} seconds"
        )

        time.sleep(SLEEP_SECONDS)


# ==================================================
# 9. Global experiment statistics
# ==================================================

generated = sum(
    item["status"] == "GENERATED"
    for item in summary
)

review_required = sum(
    item["status"] == "REVIEW_REQUIRED"
    for item in summary
)

failed = sum(
    item["status"] == "FAILED"
    for item in summary
)

total_input_tokens = 0
total_output_tokens = 0
total_tokens = 0

for item in summary:

    usage = item.get("usage") or {}

    input_tokens = (
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or 0
    )

    output_tokens = (
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or 0
    )

    total_input_tokens += input_tokens

    total_output_tokens += output_tokens

    total_tokens += (
        usage.get("total_tokens")
        or input_tokens + output_tokens
    )

total_elapsed_seconds = round(
    time.perf_counter()
    - experiment_started_at,
    3,
)

global_summary = {

    "experiment_version":
        EXPERIMENT_VERSION,

    "prompt_version":
        PROMPT_VERSION,

    "evidence_variant":
        EVIDENCE_VARIANT,

    "optimization":
        "Disable general scientific RAG",

    "section":
        SECTION,

    "provider":
        PROVIDER,

    "model":
        settings.model,

    "temperature":
        settings.temperature,

    "max_output_tokens":
        settings.max_output_tokens,

    "scientific_rag_enabled":
        True,

    "general_rag_enabled":
        False,

    "component_rag_enabled":
        True,

    "general_top_k":
        0,

    "component_top_k":
        COMPONENT_TOP_K,

    "code_snippets_enabled":
        False,

    "code_chunks_enabled":
        False,

    "constructor_bodies_enabled":
        False,

    "total_components":
        len(COMPONENTS),

    "generated":
        generated,

    "review_required":
        review_required,

    "failed":
        failed,

    "total_input_tokens":
        total_input_tokens,

    "total_output_tokens":
        total_output_tokens,

    "total_tokens":
        total_tokens,

    "total_elapsed_seconds":
        total_elapsed_seconds,

    "components":
        summary,

}


# ==================================================
# 10. Save global experiment summary
# ==================================================

summary_dir = (
    Path("data/experiments")
    / "_summaries"
    / EXPERIMENT_VERSION
)

summary_dir.mkdir(
    parents=True,
    exist_ok=True,
)

summary_path = (
    summary_dir
    / f"summary_{create_run_id()}.json"
)

save_json(
    summary_path,
    global_summary,
)


# ==================================================
# 11. Display final summary
# ==================================================

print("\n" + "=" * 70)
print("MATHEMATICAL FORMULATION V3 SUMMARY")
print("=" * 70)

for item in summary:

    print(
        f"{item['component']:<30}"
        f" : {item['status']}"
    )

print("-" * 70)

print("[TOTAL COMPONENTS]", len(COMPONENTS))
print("[GENERATED]", generated)
print("[REVIEW REQUIRED]", review_required)
print("[FAILED]", failed)

print("[TOTAL INPUT TOKENS]", total_input_tokens)
print("[TOTAL OUTPUT TOKENS]", total_output_tokens)
print("[TOTAL TOKENS]", total_tokens)

print(
    "[TOTAL ELAPSED SECONDS]",
    total_elapsed_seconds,
)

print("[SUMMARY SAVED]", summary_path)

print("=" * 70)
print("[DONE]")

'@ | python -