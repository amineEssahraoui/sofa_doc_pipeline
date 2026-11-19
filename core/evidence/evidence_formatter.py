
from copy import deepcopy


def build_llm_payload(targeted):
    """
    Convert a targeted evidence selection into
    a structured, traceable LLM payload.

    No LLM call, summarization, or interpretation.
    """

    component = targeted["component"]
    provenance = deepcopy(targeted["provenance"])

    compact = deepcopy(targeted)

    # Import locally to avoid unnecessary coupling.
    from core.evidence.evidence_selector import compact_targeted_evidence

    compact = compact_targeted_evidence(compact)

    methods = compact.get("methods")

    payload = {
        "component": component,
        "provenance": provenance,
        "methods": [],
        "attributes": [],
        "documentation": [],
    }

    if methods:
        for link in methods["method_links"]:
            payload["methods"].append({
                "type": "declaration_and_implementations",
                "data": link,
            })

        for snippet in methods["code_snippets"]:
            payload["methods"].append({
                "type": "cpp_snippet",
                "data": snippet,
            })

        for chunk in methods["code_chunks"]:
            payload["methods"].append({
                "type": "cpp_ast_chunk",
                "data": chunk,
            })

    for selection in compact["attributes"]:
        for attribute in selection["attributes"]:
            payload["attributes"].append({
                "type": "sofa_attribute",
                "data": attribute,
            })

    for selection in compact["documentation"]:
        for section in selection["sections"]:
            payload["documentation"].append({
                "type": "official_section",
                "data": section,
            })

        for table in selection["tables"]:
            payload["documentation"].append({
                "type": "official_table",
                "data": table,
            })

    return payload


def build_documentation_payload(pack):
    """
    Build a complete, compact documentation payload.

    Preserve all method declarations, attributes,
    official documentation and source provenance.

    Avoid sending duplicate C++ code.
    """

    from copy import deepcopy
    from core.evidence.evidence_selector import compact_targeted_evidence

    evidence = pack["evidence"]

    targeted = {
        "component": pack["component"],
        "provenance": deepcopy(pack["provenance"]),
        "methods": {
            "method_links": deepcopy(evidence["method_links"]),
            "code_snippets": deepcopy(evidence["code_snippets"]),
            "code_chunks": deepcopy(evidence["code_chunks"]),
        },
        "attributes": [],
        "documentation": [],
    }

    compact = compact_targeted_evidence(targeted)

    return {
        "component": pack["component"],
        "provenance": deepcopy(pack["provenance"]),
        "method_links": compact["methods"]["method_links"],
        "code_snippets": compact["methods"]["code_snippets"],
        "code_chunks": compact["methods"]["code_chunks"],
        "structured_attributes": deepcopy(
            evidence["structured_attributes"]
        ),
        "official_documentation": deepcopy(
            evidence["documentation"]
        ),
    }
