"""Generate SOFA technical documentation from existing Evidence Packs."""

import argparse
import copy
import hashlib
import json
import re
import sys
import time
from dataclasses import is_dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# The numbering follows the final documentation order, not development order.
SECTIONS = {
    1: ("overview", "Component Overview", 2048),
    2: ("architecture", "Architecture and Inheritance", 2560),
    3: ("mathematical_formulation", "Mathematical Formulation", 3072),
    4: ("internal_execution", "Internal Architecture and Execution", 3072),
    5: ("data_fields", "Data Fields and Links", 2560),
    6: ("diagnostics_usage", "Diagnostics and Usage", 3072),
}

EXPECTED_H2 = {
    1: ("Purpose and Role", "Numerical or Physical Problem", "General Approach"),
    2: ("Class Architecture", "Inheritance Hierarchy",
        "Inherited and Local Responsibilities", "Architectural Dependencies"),
    3: ("Mathematical Problem", "Mathematical Formulation", "Numerical Algorithm"),
    4: ("Internal Responsibilities", "Execution Workflow",
        "Delegation and Component Interactions", "Execution Modes and Specific Behavior"),
    5: ("Local Data Fields", "Inherited Data Fields",
        "Links and Component References", "Configuration Constraints and Interactions"),
    6: ("Practical Usage and Integration", "Configuration Guidelines",
        "Diagnostics and Troubleshooting", "Limitations and Recommendations"),
}

FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*$")


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def json_hash(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def discover_components(directory):
    # Only components with prepared evidence are available for generation.
    available = {}
    for path in sorted(directory.glob("*/evidence_pack.json")):
        if path.is_file() and re.fullmatch(r"[A-Za-z0-9_]+", path.parent.name):
            available[path.parent.name] = path
    return available


def parse_sections(value):
    if value.strip().lower() == "fully":
        return list(SECTIONS), True
    parts = [part.strip() for part in value.split(",")]
    if not parts or any(part not in {str(n) for n in SECTIONS} for part in parts):
        raise argparse.ArgumentTypeError("Use section numbers 1-6 separated by commas, or fully.")
    return sorted({int(part) for part in parts}), False


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be positive.")
    return number


def nonnegative_float(value):
    import math
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("Value must be finite and non-negative.")
    return number


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", help="Component with an existing Evidence Pack.")
    parser.add_argument("--sections", type=parse_sections,
                        help="Section numbers (e.g. 1,2,6) or fully.")
    parser.add_argument("--provider", choices=("groq", "ollama"),
                        help="Override the configured LLM provider.")
    parser.add_argument("--max-output-tokens", type=positive_int,
                        help="Override output limits for all requested sections.")
    parser.add_argument("--delay", type=nonnegative_float, default=60,
                        help="Seconds between requests (default: 15).")
    parser.add_argument("--list-components", action="store_true",
                        help="List components with prepared evidence.")
    parser.add_argument("--list-sections", action="store_true",
                        help="List available section numbers.")
    args = parser.parse_args(argv)
    if not (args.list_components or args.list_sections):
        if not args.component or args.sections is None:
            parser.error("--component and --sections are required for generation.")
    return parser, args


def lines_outside_fences(text):
    # Preserve fenced XML, Python and C++ examples during normalization and assembly.
    active = None
    for line in text.splitlines():
        match = FENCE.match(line)
        outside = active is None and match is None
        if match:
            marker, suffix = match.groups()
            if active is None:
                active = marker
            elif marker[0] == active[0] and len(marker) >= len(active) and not suffix.strip():
                active = None
        yield line, outside, active


def heading_text(value):
    return re.sub(r"[ \t]+#+\s*$", "", value).strip()


def normalize_markdown(text, section_id):
    title = SECTIONS[section_id][1]
    canonical = {title.casefold(): "# " + title}
    canonical.update({name.casefold(): "## " + name for name in EXPECTED_H2[section_id]})
    output, changes = [], []
    first_content = True
    for index, (line, outside, _) in enumerate(lines_outside_fences(text), 1):
        new = line
        if outside:
            candidate = re.sub(r"^#{1,6}\s*", "", line.strip())
            if candidate.startswith("**") and candidate.endswith("**"):
                candidate = candidate[2:-2].strip()
            candidate = heading_text(candidate)
            if first_content and candidate.casefold() == title.casefold():
                new = "# " + title
            else:
                new = canonical.get(candidate.casefold(), line)
        if line.strip():
            first_content = False
        if new != line:
            changes.append({"line": index, "original": line, "normalized": new})
        output.append(new)
    return "\n".join(output).strip(), changes


def validate_markdown(text, section_id):
    title = SECTIONS[section_id][1]
    headings = []
    active = None
    for line, outside, active in lines_outside_fences(text):
        match = HEADING.match(line) if outside else None
        if match:
            headings.append((len(match[1]), heading_text(match[2])))
    expected = [(1, title)] + [(2, name) for name in EXPECTED_H2[section_id]]
    major = [(level, name) for level, name in headings if level <= 2]
    starts_correctly = bool(text.strip()) and text.strip().splitlines()[0] == "# " + title
    # Architecture, Mathematics and Data Fields can contain deeper headings.
    section_key = SECTIONS[section_id][0]
    allowed_depth = 3 if section_key in (
        "architecture",
        "mathematical_formulation",
        "data_fields",
    ) else 2

    checks = {
        "starts_with_expected_title": starts_correctly,
        "expected_major_headings": major == expected,
        "allowed_heading_depth": all(level <= allowed_depth for level, _ in headings),
        "code_fences_closed": active is None,
    }
    return {"valid": all(checks.values()), "checks": checks,
            "headings": [{"level": level, "title": name} for level, name in headings]}


def settings_with_limit(settings, limit):
    # Use a copy so the provider's global configuration is not changed.
    if int(settings.max_output_tokens) == limit:
        return settings
    if is_dataclass(settings):
        updated = replace(settings, max_output_tokens=limit)
    elif hasattr(settings, "model_copy"):
        updated = settings.model_copy(update={"max_output_tokens": limit})
    elif hasattr(settings, "_replace"):
        updated = settings._replace(max_output_tokens=limit)
    else:
        updated = copy.copy(settings)
        updated.max_output_tokens = limit
    if int(updated.max_output_tokens) != limit:
        raise RuntimeError("The requested output token limit was not applied.")
    return updated


def retrieve_source_map(payload):
    mapping = payload.get("source_files", {})
    return mapping if isinstance(mapping, dict) else {}


def source_legend(mapping):
    if not mapping:
        return ""
    lines = ["**Local source references for this section**", ""]
    for ref, path in mapping.items():
        value = path if isinstance(path, str) else json.dumps(path, ensure_ascii=False)
        lines.append(f"- `{ref}`: `{value}`")
    return "\n".join(lines)


def assemble_document(component, requested, documents, source_maps):
    # Local source identifiers are scoped to their section, not globally renamed.
    missing = [number for number in requested if number not in documents]
    title = f"# {component} - Technical Documentation"
    if missing:
        title += " (Partial)"
    parts = [title, "This document has been generated from supplied evidence. "
             "It has not undergone exhaustive factual verification."]
    if missing:
        parts.append("**Incomplete generation. Missing or rejected sections:** " +
                     ", ".join(f"{n}. {SECTIONS[n][1]}" for n in missing) + ".")
    parts.append("## Table of Contents\n\n" + "\n".join(
        f"- {n}. {SECTIONS[n][1]}" for n in requested if n in documents))
    for number in requested:
        if number not in documents:
            continue
        lines = []
        for line, outside, _ in lines_outside_fences(documents[number]):
            match = HEADING.match(line) if outside else None
            if match:
                level, text = len(match[1]), heading_text(match[2])
                if level == 1:
                    line = f"## {number}. {SECTIONS[number][1]}"
                else:
                    line = "#" * min(level + 1, 6) + " " + text
            lines.append(line)
        section_text = "\n".join(lines)
        legend = source_legend(source_maps.get(number, {}))
        if legend:
            section_text += "\n\n" + legend
        parts.append(section_text)
    return "\n\n".join(parts) + "\n"


def section_stem(number):
    return f"{number:02d}_{SECTIONS[number][0]}"


def generate_section(number, component, pack, base_settings, args):
    # Reuse the existing evidence selection, RAG routing and prompt construction.
    from core.generation.documentation_generator import prepare_documentation_section
    from core.llm.groq_client import generate_with_groq
    from core.llm.ollama_client import generate_with_ollama

    key, title, profile_limit = SECTIONS[number]
    provider = base_settings.provider
    limit = args.max_output_tokens or (profile_limit if provider == "groq"
                                       else int(base_settings.max_output_tokens))
    settings = settings_with_limit(base_settings, limit)
    started = now()
    start = time.perf_counter()
    prepared = prepare_documentation_section(component=component,
                                             evidence_pack=pack, section=key)
    preparation_seconds = time.perf_counter() - start
    payload = prepared["evidence_payload"]
    source_map = retrieve_source_map(payload)
    # Keep provenance and retrieval context but do not duplicate Markdown files.
    metadata = {
        "section_id": number, "section": key, "title": title,
        "provider": provider, "requested_model": settings.model,
        "temperature": settings.temperature, "max_output_tokens": limit,
        "started_at_utc": started,
        "rag_active": prepared["rag_active"],
        "retrieval_queries": prepared.get("retrieval_queries", []),
        "retrieved_context": prepared.get("retrieved_context"),
        "source_files": source_map,
        "evidence_payload_sha256": json_hash(payload),
        "messages_sha256": json_hash(prepared["messages"]),
        "preparation_seconds": round(preparation_seconds, 3),
        "factual_verification_performed": False,
    }
    request_started = time.perf_counter()
    try:
        client = {"groq": generate_with_groq, "ollama": generate_with_ollama}[provider]
        response = client(messages=prepared["messages"], settings=settings)
        raw = response.get("content") or ""
        normalized, changes = normalize_markdown(raw, number)
        validation = validate_markdown(normalized, number)
        finish = response.get("finish_reason")
        status = "GENERATED" if finish == "stop" and validation["valid"] else "REVIEW_REQUIRED"
        metadata.update({
            "status": status, "response_model": response.get("model"),
            "finish_reason": finish, "usage": response.get("usage"),
            "parameters": response.get("parameters"),
            "raw_markdown_validation": validate_markdown(raw, number),
            "markdown_validation": validation, "normalization_changes": changes,
            "output_characters": len(normalized), "output_words": len(normalized.split()),
            "output_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        })
        # Reject incomplete or invalid sections from the deliverable.
        return normalized if status == "GENERATED" else None, metadata
    except Exception as error:
        metadata.update({"status": "ERROR", "error_type": type(error).__name__,
                         "error_message": str(error)})
        return None, metadata
    finally:
        metadata.update({"finished_at_utc": now(),
                         "llm_elapsed_seconds": round(time.perf_counter() - request_started, 3),
                         "elapsed_seconds": round(time.perf_counter() - start, 3)})


def aggregate_usage(results):
    # Missing provider metrics remain unknown rather than being counted as zero.
    totals = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        values = [(item.get("usage") or {}).get(key) for item in results]
        known = [value for value in values if isinstance(value, int) and not isinstance(value, bool)]
        totals[key] = sum(known) if known else None
        totals[key + "_reported_sections"] = len(known)
    return totals


def run_generation(args, pack_path, output_dir):
    from config.llm_settings import get_llm_settings
    from config.prompts import SECTION_SYSTEM_RULES, SECTION_TASK_PROMPTS

    component = args.component
    requested, full = args.sections
    raw_pack = pack_path.read_bytes()
    pack = json.loads(raw_pack.decode("utf-8-sig"))
    if not isinstance(pack, dict) or pack.get("component") != component:
        raise ValueError("Evidence Pack component mismatch.")
    if not isinstance(pack.get("evidence"), dict):
        raise ValueError("Missing or invalid evidence object.")
    for number in requested:
        key = SECTIONS[number][0]
        if key not in SECTION_SYSTEM_RULES or key not in SECTION_TASK_PROMPTS:
            raise ValueError(f"Missing prompts for section {number}: {key}")
    base_settings = get_llm_settings(args.provider)
    if base_settings.provider not in ("groq", "ollama"):
        raise ValueError(f"Unsupported provider: {base_settings.provider}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    mode_label = "FULL" if full else "-".join(f"S{n}" for n in requested)
    generation_id = f"{component}_{mode_label}_{timestamp}_{uuid4().hex[:8]}"
    run_dir = output_dir / generation_id
    metadata_dir = run_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=False)
    started = now()
    start = time.perf_counter()
    documents, source_maps, results = {}, {}, []
    print(f"Component: {component}")
    print(f"Provider: {base_settings.provider} ({base_settings.model})")
    print(f"Output directory: {run_dir}")

    for index, number in enumerate(requested):
        print(f"Generating section {number}: {SECTIONS[number][1]}", flush=True)
        section_start = time.perf_counter()
        section_started = now()
        try:
            document, metadata = generate_section(number, component, pack, base_settings, args)
        except Exception as error:
            document = None
            metadata = {"section_id": number, "section": SECTIONS[number][0],
                        "status": "ERROR", "error_type": type(error).__name__,
                        "error_message": str(error), "started_at_utc": section_started,
                        "finished_at_utc": now(),
                        "elapsed_seconds": round(time.perf_counter() - section_start, 3),
                        "factual_verification_performed": False}
        if document is not None:
            documents[number] = document
            source_maps[number] = metadata.get("source_files", {})
            if not full:
                filename = section_stem(number) + ".md"
                legend = source_legend(source_maps[number])
                content = document + ("\n\n" + legend if legend else "")
                (run_dir / filename).write_text(content + "\n", encoding="utf-8")
                metadata["document"] = filename
        write_json(metadata_dir / (section_stem(number) + ".json"), metadata)
        results.append(metadata)
        print(f"Section {number}: {metadata['status']}")
        if metadata.get("error_message"):
            print(f"  {metadata['error_message']}", file=sys.stderr)
        if index < len(requested) - 1 and args.delay:
            time.sleep(args.delay)

    failures = [number for number in requested if number not in documents]
    status = "SUCCESS" if not failures else ("PARTIAL_SUCCESS" if documents else "FAILED")
    assembled_filename = None
    if full and documents:
        assembled_filename = component + ("_PARTIAL" if failures else "") + ".md"
        assembled = assemble_document(component, requested, documents, source_maps)
        (run_dir / assembled_filename).write_text(assembled, encoding="utf-8")
    summary = {
        "generation_id": generation_id, "component": component,
        "mode": "full" if full else "partial", "status": status,
        "requested_sections": requested, "generated_sections": list(documents),
        "failed_or_rejected_sections": failures,
        "provider": base_settings.provider, "model": base_settings.model,
        "source_commit": (pack.get("provenance") or {}).get("code_commit"),
        "evidence_pack_sha256": hashlib.sha256(raw_pack).hexdigest(),
        "evidence_pack_path": str(pack_path),
        "usage": aggregate_usage(results),
        "started_at_utc": started, "finished_at_utc": now(),
        "elapsed_seconds": round(time.perf_counter() - start, 3),
        "assembled": assembled_filename is not None,
        "assembled_document": assembled_filename,
        "complete_document": full and not failures,
        "factual_verification_performed": False,
        "sections": [{"id": item["section_id"], "status": item["status"],
                      "metadata": "metadata/" + section_stem(item["section_id"]) + ".json"}
                     for item in results],
    }
    write_json(metadata_dir / "generation_summary.json", summary)
    print(f"Generation status: {status}")
    print(f"Generated sections: {len(documents)}/{len(requested)}")
    print(f"Results: {run_dir}")
    return 0 if status == "SUCCESS" else (2 if status == "PARTIAL_SUCCESS" else 1)


def main(argv=None):
    parser, args = parse_arguments(argv)
    if args.list_sections:
        for number, (key, title, _) in SECTIONS.items():
            print(f"{number}: {title} ({key})")
        if not args.list_components:
            return 0
    from config.settings import INTERMEDIATE_DIR, OUTPUT_DIR

    available = discover_components(Path(INTERMEDIATE_DIR))
    if args.list_components:
        for component in available:
            print(component)
        if not available:
            print("No prepared Evidence Packs found.")
        return 0
    if args.component not in available:
        parser.error(f"No prepared Evidence Pack for {args.component!r}. Use --list-components.")
    try:
        return run_generation(args, available[args.component], Path(OUTPUT_DIR))
    except Exception as error:
        print(f"Generation failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
