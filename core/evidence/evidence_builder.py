
import json
from pathlib import Path

from config.settings import INTERMEDIATE_DIR


def load_evidence_sources(component):
    """
    Load and validate the five sources required
    to construct an Evidence Pack.
    """

    folder = Path(INTERMEDIATE_DIR) / component

    filenames = {
        "method_links": "method_links.json",
        "structured_data": "unified_data_enriched.json",
        "code_snippets": "code_snippets.json",
        "code_chunks": "code_chunks.json",
        "official_documentation": "official_documentation.json",
    }

    sources = {}

    for key, filename in filenames.items():
        path = folder / filename

        if not path.is_file():
            raise FileNotFoundError(
                f"Missing evidence source: {path}"
            )

        sources[key] = json.loads(
            path.read_text(encoding="utf-8")
        )

    # Validate expected JSON structures
    for key in [
        "method_links",
        "structured_data",
        "official_documentation",
    ]:
        if not isinstance(sources[key], dict):
            raise TypeError(
                f"{key} must be a dictionary"
            )

    for key in ["code_snippets", "code_chunks"]:
        if not isinstance(sources[key], list):
            raise TypeError(
                f"{key} must be a list"
            )

    # Validate component identity
    for key, data in sources.items():
        if isinstance(data, dict):
            items = [data]
        else:
            items = data

        for item in items:
            if item.get("component") != component:
                raise ValueError(
                    f"Component mismatch in {key}"
                )

    # Validate C++ source consistency
    code_commit = sources["method_links"]["resolved_commit"]

    if sources["structured_data"]["resolved_commit"] != code_commit:
        raise ValueError("Structured data commit mismatch")

    for key in ["code_snippets", "code_chunks"]:
        for item in sources[key]:
            if item.get("resolved_commit") != code_commit:
                raise ValueError(
                    f"C++ commit mismatch in {key}"
                )

    # Official documentation is a separate source.
    # Its associated commit does not prove an exact
    # historical match with the C++ repository.

    return {
        "component": component,
        "code_commit": code_commit,
        "sources": sources,
    }

def build_architecture_data(includes_data):

    """
    Build architectural evidence from existing
    C++ extraction results.
    """

    classes = []
    includes = []

    for file_data in includes_data.get("files", []):

        source_file = file_data["file"]

        for class_data in file_data.get("classes", []):

            classes.append({
                **class_data,
                "source_file": source_file,
            })

        if file_data.get("includes"):

            includes.append({
                "source_file": source_file,
                "headers": file_data["includes"],
            })

    return {
        "classes": classes,
        "parent_dependencies": includes_data.get(
            "parent_dependencies", []
        ),
        "includes": includes,
    }

def build_constructor_data(includes_data):
    """
    Collect constructor metadata and initialization evidence
    from existing extraction outputs.
    """

    from copy import deepcopy

    constructor_data = []

    for file_data in includes_data.get("files", []):

        source_file = file_data["file"]

        constructors = file_data.get("constructors", [])
        metadata = file_data.get("constructor_metadata", [])

        if not constructors and not metadata:
            continue

        constructor_data.append({
            "source_file": source_file,
            "constructors": deepcopy(constructors),
            "metadata": deepcopy(metadata),
        })

    return constructor_data

def build_evidence_pack(component):
    """
    Assemble validated evidence sources into a
    traceable Evidence Pack.

    No LLM calls and no changes to source JSONs.
    """

    loaded = load_evidence_sources(component)

    sources = loaded["sources"]
    code_commit = loaded["code_commit"]

    documentation = sources["official_documentation"]

    # Load existing architectural evidence

    component_dir = Path(INTERMEDIATE_DIR) / component

    includes_data = json.loads(
        (component_dir / "includes.json").read_text(
            encoding="utf-8"
        )
    )

    # Validate architectural evidence provenance

    if includes_data["component"] != component:
        raise ValueError("Architecture component mismatch")

    if includes_data["resolved_commit"] != code_commit:
        raise ValueError("Architecture commit mismatch")

    architecture = build_architecture_data(includes_data)
    constructor_metadata = build_constructor_data(includes_data)

    # Assemble the Evidence Pack

    pack = {
        "component": component,
        "schema_version": "1.0",
        "provenance": {
            "code_commit": code_commit,
            "documentation": {
                "canonical_url": documentation.get("canonical_url"),
                "html_sha256": documentation.get("html_sha256"),
                "associated_code_commit": documentation.get(
                    "resolved_commit"
                ),
                "version_match_verified": False,
            },
        },
        "evidence": {
            "method_links": sources["method_links"]["method_links"],
            "structured_attributes": sources["structured_data"]["attributes"],
            "code_snippets": sources["code_snippets"],
            "code_chunks": sources["code_chunks"],
            "documentation": {
                "introduction": documentation.get("introduction", []),
                "sections": documentation["sections"],
                "tables": documentation["tables"],
            },
            "architecture": architecture,
            "constructor_metadata": constructor_metadata,
        },
        "statistics": {
            "method_links": len(
                sources["method_links"]["method_links"]
            ),
            "structured_attributes": len(
                sources["structured_data"]["attributes"]
            ),
            "code_snippets": len(sources["code_snippets"]),
            "code_chunks": len(sources["code_chunks"]),
            "documentation_sections": len(
                documentation["sections"]
            ),
            "documentation_tables": len(
                documentation["tables"]
            ),
            "architecture_classes": len(
                architecture["classes"]
            ),
            "architecture_parent_dependencies": len(
                architecture["parent_dependencies"]
            ),
            "architecture_include_files": len(
                architecture["includes"]
            ),
            "constructor_files": len(constructor_metadata),

            "constructors": sum(
                len(item["constructors"])
                for item in constructor_metadata
            ),

            "constructor_metadata": sum(
                len(item["metadata"])
                for item in constructor_metadata
            ),
        },
    }

    output_path = component_dir / "evidence_pack.json"

    output_path.write_text(
        json.dumps(
            pack,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(f"[EVIDENCE PACK] {component}")
    print(f"[CLASSES] {len(architecture['classes'])}")
    print(f"[PARENT DEPENDENCIES] {len(architecture['parent_dependencies'])}")
    print(f"[SAVED] {output_path}")

    return pack
