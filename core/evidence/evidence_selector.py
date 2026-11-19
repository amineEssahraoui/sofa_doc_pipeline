
def select_method_evidence(pack, method_name):
    """
    Select evidence for a specific C++ method.

    Keeps all matching overloads and their
    original source information.
    """

    evidence = pack["evidence"]

    method_links = [
        item
        for item in evidence["method_links"]
        if item["method"] == method_name
    ]

    snippets = [
        item
        for item in evidence["code_snippets"]
        if item["method"] == method_name
    ]

    chunks = [
        item
        for item in evidence["code_chunks"]
        if item["method"] == method_name
    ]

    return {
        "component": pack["component"],
        "method": method_name,
        "provenance": pack["provenance"],
        "method_links": method_links,
        "code_snippets": snippets,
        "code_chunks": chunks,
        "statistics": {
            "method_links": len(method_links),
            "code_snippets": len(snippets),
            "code_chunks": len(chunks),
        },
    }



def select_method_overload(pack, method_name, signature_contains):
    """
    Select one or more overloads using a signature fragment.

    The fragment must appear in the C++ signature.
    """

    selected = select_method_evidence(pack, method_name)

    def matches(item):
        signature = item.get("signature", "")

        if not signature and item.get("declaration"):
            signature = item["declaration"].get(
                "signature", ""
            )

        return signature_contains in signature

    snippets = [
        item
        for item in selected["code_snippets"]
        if matches(item)
    ]

    chunks = [
        item
        for item in selected["code_chunks"]
        if matches(item)
    ]

    links = [
        item
        for item in selected["method_links"]
        if (
            item.get("declaration")
            and signature_contains
            in item["declaration"].get("signature", "")
        )
    ]

    return {
        "component": selected["component"],
        "method": method_name,
        "signature_filter": signature_contains,
        "provenance": selected["provenance"],
        "method_links": links,
        "code_snippets": snippets,
        "code_chunks": chunks,
        "statistics": {
            "method_links": len(links),
            "code_snippets": len(snippets),
            "code_chunks": len(chunks),
        },
    }


def select_attribute_evidence(pack, attribute_name):
    """
    Select a SOFA Data attribute by its exact
    public name or C++ variable name.

    Preserve inheritance and source metadata.
    """

    attributes = pack["evidence"]["structured_attributes"]

    matches = [
        item
        for item in attributes
        if (
            item.get("sofa_name") == attribute_name
            or item.get("name") == attribute_name
        )
    ]

    return {
        "component": pack["component"],
        "attribute": attribute_name,
        "provenance": {
            "code_commit": pack["provenance"]["code_commit"]
        },
        "attributes": matches,
        "statistics": {
            "matches": len(matches)
        }
    }


def select_documentation_evidence(pack, section_title):
    """
    Select an official documentation section
    and its associated tables.

    Preserve original content and provenance.
    """

    documentation = pack["evidence"]["documentation"]

    sections = [
        section
        for section in documentation["sections"]
        if section["title"] == section_title
    ]

    tables = [
        table
        for table in documentation["tables"]
        if table["section"] == section_title
    ]

    return {
        "component": pack["component"],
        "section_title": section_title,
        "provenance": pack["provenance"]["documentation"],
        "sections": sections,
        "tables": tables,
        "statistics": {
            "sections": len(sections),
            "tables": len(tables),
        },
    }

def build_targeted_evidence(
    pack,
    method_name=None,
    attribute_names=None,
    section_titles=None,
):
    """
    Build a targeted evidence selection.

    All selectors use explicit names.
    No LLM calls or semantic matching.
    """

    attribute_names = attribute_names or []
    section_titles = section_titles or []

    result = {
        "component": pack["component"],
        "provenance": pack["provenance"],
        "methods": None,
        "attributes": [],
        "documentation": [],
    }

    if method_name:
        result["methods"] = select_method_evidence(
            pack, method_name
        )

    for name in attribute_names:
        result["attributes"].append(
            select_attribute_evidence(pack, name)
        )

    for title in section_titles:
        result["documentation"].append(
            select_documentation_evidence(pack, title)
        )

    return result


from copy import deepcopy


def compact_targeted_evidence(targeted):
    """
    Remove duplicated C++ code from a targeted selection.

    Prefer AST chunks only when they reconstruct
    the original snippet exactly.
    """

    result = deepcopy(targeted)
    methods = result.get("methods")

    if methods is None:
        return result

    snippets = methods["code_snippets"]
    chunks = methods["code_chunks"]

    kept_snippets = []
    kept_chunks = []
    used_chunk_ids = set()

    for snippet in snippets:
        matching = sorted(
            [
                chunk for chunk in chunks
                if (
                    chunk["method"] == snippet["method"]
                    and chunk["source_file"] == snippet["source_file"]
                    and chunk["signature"] == snippet["signature"]
                    and chunk["start_line"] >= snippet["start_line"]
                    and chunk["end_line"] <= snippet["end_line"]
                )
            ],
            key=lambda x: x["start_line"]
        )

        reconstructed = "".join(
            chunk["code"] for chunk in matching
        )

        if matching and reconstructed == snippet["code"]:
            for chunk in matching:
                chunk_id = (
                    chunk["source_file"],
                    chunk["start_line"],
                    chunk["end_line"],
                    chunk["signature"]
                )

                if chunk_id not in used_chunk_ids:
                    kept_chunks.append(chunk)
                    used_chunk_ids.add(chunk_id)
        else:
            kept_snippets.append(snippet)

    methods["code_snippets"] = kept_snippets
    methods["code_chunks"] = kept_chunks

    methods["statistics"] = {
        "method_links": len(methods["method_links"]),
        "code_snippets": len(kept_snippets),
        "code_chunks": len(kept_chunks),
    }

    return result


from copy import deepcopy


def build_overview_evidence(pack):
    """
    Select evidence for the Component Overview section.

    Include official introduction and documentary paragraphs.
    Exclude C++ methods, attributes, snippets and AST chunks.
    """

    from copy import deepcopy

    if not isinstance(pack, dict):
        raise TypeError("Evidence Pack must be a dictionary")

    component = pack.get("component")

    if not component:
        raise ValueError("Missing component identifier")

    documentation = pack["evidence"]["documentation"]

    selected_sections = []

    for section in documentation.get("sections", []):
        title = section.get("title", "")

        if title.strip().lower() == "examples":
            continue

        paragraphs = [
            deepcopy(item)
            for item in section.get("content", [])
            if item.get("type") == "paragraph"
        ]

        if paragraphs:
            selected_sections.append({
                "title": title,
                "content": paragraphs,
            })

    introduction = [
        deepcopy(item)
        for item in documentation.get("introduction", [])
        if item.get("type") == "paragraph"
    ]

    return {
        "component": component,
        "provenance": deepcopy(pack["provenance"]),
        "official_documentation": {
            "introduction": introduction,
            "sections": selected_sections,
        },
    }


def build_architecture_evidence(pack):
    """
    Build compact evidence for Architecture and Inheritance.

    Preserve architectural facts and source traceability
    while removing redundant and algorithm-specific information.
    """

    from copy import deepcopy

    if not isinstance(pack, dict):
        raise TypeError("Evidence Pack must be a dictionary")

    component = pack.get("component")

    if not component:
        raise ValueError("Missing component identifier")

    evidence = pack["evidence"]
    documentation = evidence["documentation"]

    # ==================================================
    # 1. Shared source file references
    # ==================================================

    source_files = {}
    file_lookup = {}

    def file_ref(path):

        if not path:
            return None

        if path not in file_lookup:

            reference = f"F{len(file_lookup) + 1}"

            file_lookup[path] = reference
            source_files[reference] = path

        return file_lookup[path]

    # ==================================================
    # 2. Architecture and inheritance
    # ==================================================

    raw_architecture = evidence["architecture"]

    classes = []

    for item in raw_architecture["classes"]:

        class_data = deepcopy(item)

        if "source_file" in class_data:
            class_data["source_file"] = file_ref(
                class_data["source_file"]
            )

        classes.append(class_data)

    parent_dependencies = [
        {
            key: deepcopy(parent[key])
            for key in (
                "class",
                "parent",
                "status",
                "header_path",
            )
            if key in parent
        }
        for parent in raw_architecture["parent_dependencies"]
    ]

    includes = [
        {
            "source_file": file_ref(item["source_file"]),
            "headers": deepcopy(item["headers"]),
        }
        for item in raw_architecture["includes"]
    ]

    architecture = {
        "classes": classes,
        "parent_dependencies": parent_dependencies,
        "includes": includes,
    }

    # ==================================================
    # 3. Official documentation
    # ==================================================

    introduction = [
        item["text"]
        for item in documentation.get("introduction", [])
        if item.get("type") == "paragraph"
    ]

    selected_sections = []
    template_groups = {}

    for section in documentation.get("sections", []):

        title = section.get("title", "")

        if title.strip().lower() in ("example", "examples"):
            continue

        content = [
            deepcopy(item)
            for item in section.get("content", [])
            if item.get("type") in ("paragraph", "list")
        ]

        if not content:
            continue

        # Group repeated template documentation.

        is_template_section = any(
            item.get("type") == "paragraph"
            and item.get("text", "").strip().lower() == "templates:"
            for item in content
        )

        if is_template_section:

            target = None
            namespace = None
            parents = []
            templates = []
            current_field = None
            extra_content = []

            for item in content:

                if item.get("type") == "paragraph":

                    text = item.get("text", "").strip()
                    lower_text = text.lower()

                    if lower_text == "templates:":
                        current_field = "templates"

                    elif lower_text.startswith("target"):
                        target = text.partition(":")[2].strip()
                        current_field = None

                    elif lower_text.startswith("namespace"):
                        namespace = text.partition(":")[2].strip()
                        current_field = None

                    elif lower_text.startswith("parents"):
                        current_field = "parents"

                    else:
                        extra_content.append(item)
                        current_field = None

                elif item.get("type") == "list":

                    values = item.get("items", [])

                    if current_field == "templates":
                        templates.extend(values)

                    elif current_field == "parents":
                        parents.extend(values)

                    else:
                        extra_content.append(item)

            group_key = (
                target,
                namespace,
                tuple(parents),
            )

            if group_key not in template_groups:

                template_groups[group_key] = {
                    "target": target,
                    "namespace": namespace,
                    "documented_parents": parents,
                    "templates": [],
                    "source_sections": [],
                }

            group = template_groups[group_key]

            for template in templates or [title]:

                if template not in group["templates"]:
                    group["templates"].append(template)

            group["source_sections"].append(title)

            if extra_content:
                selected_sections.append({
                    "title": title,
                    "content": extra_content,
                })

            continue

        selected_sections.append({
            "title": title,
            "content": content,
        })

    official_documentation = {
        "introduction": introduction,
        "sections": selected_sections,
        "template_groups": list(template_groups.values()),
    }

    # ==================================================
    # 4. Compact structured attributes
    # ==================================================

    structured_attributes = []

    attribute_fields = (
        "name",
        "type",
        "category",
        "owner_class",
        "visibility",
        "origin",
        "description",
        "line",
    )

    for attribute in evidence.get("structured_attributes", []):

        item = {
            key: deepcopy(attribute[key])
            for key in attribute_fields
            if key in attribute
        }

        if "source_file" in attribute:

            item["source_file"] = file_ref(
                attribute["source_file"]
            )

        # Normalize unnecessary whitespace.

        if isinstance(item.get("description"), str):

            item["description"] = " ".join(
                item["description"].split()
            )

        structured_attributes.append(item)

    # ==================================================
    # 5. Compact method links
    # ==================================================

    method_links = []

    for method in evidence.get("method_links", []):

        declaration = deepcopy(
            method.get("declaration")
        )

        if declaration:

            if "file" in declaration:

                declaration["file"] = file_ref(
                    declaration["file"]
                )

            if isinstance(declaration.get("signature"), str):

                declaration["signature"] = " ".join(
                    declaration["signature"].split()
                )

        implementations = []

        for implementation in method.get("implementations", []):

            item = {
                key: deepcopy(implementation[key])
                for key in (
                    "start_line",
                    "end_line",
                    "owner",
                    "kind",
                )
                if key in implementation
            }

            if "file" in implementation:

                item["file"] = file_ref(
                    implementation["file"]
                )

            implementations.append(item)

        method_links.append({
            "method": method["method"],
            "declaration": declaration,
            "implementations": implementations,
            "status": method.get("status"),
        })

    # ==================================================
    # 7. Final architecture payload
    # ==================================================

    return {
        "component": component,

        "provenance": deepcopy(pack["provenance"]),

        "source_reference_note": (
            "Resolve file identifiers using source_files "
            "when citing C++ evidence. A missing implementation "
            "snippet does not imply an inherited or absent method."
        ),

        "source_files": source_files,

        "architecture": architecture,

        "official_documentation": official_documentation,

        "structured_attributes": structured_attributes,

        "method_links": method_links,
        "code_snippets": [],
    }


def build_data_fields_evidence(pack):
    """
    Select and optimize evidence for Data Fields and Links.

    Reuse existing extraction and consolidation outputs,
    preserve conflicting evidence, and remove redundancy.
    """

    import json
    from copy import deepcopy
    from config.settings import INTERMEDIATE_DIR

    component = pack["component"]
    evidence = pack["evidence"]
    documentation = evidence["documentation"]

    # ==================================================
    # 1. Load existing extracted declarations
    # ==================================================

    includes_path = (
        INTERMEDIATE_DIR
        / component
        / "includes.json"
    )

    includes_data = json.loads(
        includes_path.read_text(encoding="utf-8")
    )

    if includes_data["component"] != component:
        raise ValueError("Component mismatch in includes.json")

    if (
        includes_data["resolved_commit"]
        != pack["provenance"]["code_commit"]
    ):
        raise ValueError("Commit mismatch in includes.json")

    # ==================================================
    # 2. Shared source file references
    # ==================================================

    source_files = {}
    file_lookup = {}

    def file_ref(path):

        if not path:
            return None

        if path not in file_lookup:

            reference = f"F{len(file_lookup) + 1}"

            file_lookup[path] = reference
            source_files[reference] = path

        return file_lookup[path]

    # ==================================================
    # 3. Select existing enriched attributes
    # ==================================================

    categories = {
        "SOFA_Data",
        "SOFA_Link",
        "SOFA_DeprecatedData",
    }

    structured_attributes = []
    seen_attributes = set()

    def add_attribute(attribute):

        item = deepcopy(attribute)

        identity = (
            item.get("owner_class"),
            item.get("name"),
            item.get("source_file"),
            item.get("line"),
        )

        if identity in seen_attributes:
            return

        seen_attributes.add(identity)

        if item.get("source_file"):
            item["source_file"] = file_ref(
                item["source_file"]
            )

        initialization_source = item.get(
            "initialization_source"
        )

        if initialization_source:

            if initialization_source.get("file"):

                initialization_source["file"] = file_ref(
                    initialization_source["file"]
                )

        structured_attributes.append(item)

    for attribute in evidence["structured_attributes"]:

        if attribute.get("category") in categories:
            add_attribute(attribute)

    # ==================================================
    # 4. Recover existing local declarations
    # ==================================================

    for file_data in includes_data.get("files", []):

        for attribute in file_data.get("attributes", []):

            if attribute.get("category") not in categories:
                continue

            item = {
                **deepcopy(attribute),
                "origin": "local",
                "source_file": file_data["file"],
            }

            add_attribute(item)

    # ==================================================
    # 5. Index local structured attributes
    # ==================================================

    local_attribute_lookup = {}

    for attribute in structured_attributes:

        if attribute.get("origin") != "local":
            continue

        name = attribute.get("name")

        local_attribute_lookup.setdefault(
            name, []
        ).append(attribute)

    # ==================================================
    # 6. Optimize constructor evidence
    # ==================================================

    constructor_evidence = {
        "sofa_parameters": [],
        "required_fields": [],
        "deprecated_fields": [],
        "link_fields": [],
        "constructor_bodies": [],
    }

    metadata_categories = (
        "sofa_parameters",
        "required_fields",
        "deprecated_fields",
        "link_fields",
    )

    metadata_lookup = {}

    for file_data in evidence["constructor_metadata"]:

        reference = file_ref(file_data["source_file"])

        for metadata in file_data.get("metadata", []):

            for category in metadata_categories:

                for record in metadata.get(category, []):

                    item = deepcopy(record)

                    line = item.pop("line", None)

                    source_expression = item.pop(
                        "source_expression",
                        None,
                    )

                    matched_attributes = (
                        local_attribute_lookup.get(
                            item.get("attribute"),
                            [],
                        )
                    )

                    redundant_fields = []

                    # Remove only information already present
                    # in a uniquely matched structured attribute.

                    if (
                        category == "sofa_parameters"
                        and len(matched_attributes) == 1
                    ):

                        existing = matched_attributes[0]

                        constructor_name = (
                            metadata.get("constructor") or ""
                        )

                        owner = (
                            existing.get("owner_class") or ""
                        ).split("<", 1)[0].split("::")[-1]

                        constructor_owner = (
                            constructor_name.rsplit("::", 1)[0]
                            .split("<", 1)[0]
                            .split("::")[-1]
                        )

                        if (
                            existing.get("category") == "SOFA_Data"
                            and owner == constructor_owner
                        ):

                            for key in (
                                "default_expression",
                                "sofa_name",
                                "description",
                            ):

                                if (
                                    key in item
                                    and key in existing
                                    and item[key] == existing[key]
                                ):

                                    redundant_fields.append(key)
                                    item.pop(key)

                    # Keep original initialization expressions
                    # when metadata is incomplete or differs.

                    fully_redundant = (
                        category == "sofa_parameters"
                        and len(redundant_fields) == 3
                    )

                    source = {
                        "file": reference,
                        "line": line,
                        "constructor": metadata.get(
                            "constructor"
                        ),
                    }

                    if (
                        source_expression
                        and not fully_redundant
                    ):

                        source["source_expression"] = (
                            source_expression
                        )

                    if redundant_fields:

                        item["reused_attribute_fields"] = (
                            redundant_fields
                        )

                    identity = (
                        category,
                        json.dumps(
                            item,
                            sort_keys=True,
                            ensure_ascii=False,
                        ),
                    )

                    if identity not in metadata_lookup:

                        item["sources"] = []

                        metadata_lookup[identity] = item

                        constructor_evidence[category].append(
                            item
                        )

                    sources = metadata_lookup[identity][
                        "sources"
                    ]

                    if source not in sources:
                        sources.append(source)

        # Preserve constructor bodies because they may
        # override initialization values or required flags.

        for constructor in file_data.get("constructors", []):

            body = constructor.get("body") or ""

            if "".join(body.split()) in ("", "{}"):
                continue

            constructor_evidence["constructor_bodies"].append({
                "source_file": reference,
                "class": constructor.get("class"),
                "signature": constructor.get("signature"),
                "line": constructor.get("line"),
                "body": body,
            })

    # ==================================================
    # 7. Select architectural ownership evidence
    # ==================================================

    architecture = {
        "classes": [],
        "parent_dependencies": [],
    }

    for class_data in evidence["architecture"]["classes"]:

        item = deepcopy(class_data)

        if item.get("source_file"):

            item["source_file"] = file_ref(
                item["source_file"]
            )

        architecture["classes"].append(item)

    for parent in evidence["architecture"]["parent_dependencies"]:

        item = {
            key: deepcopy(parent[key])
            for key in (
                "class",
                "parent",
                "status",
                "header_path",
            )
            if key in parent
        }

        architecture["parent_dependencies"].append(item)

    # ==================================================
    # 8. Deduplicate official documentation records
    # ==================================================

    official_documentation = {
        "data_fields": [],
        "links": [],
    }

    document_lookup = {}

    for table in documentation.get("tables", []):

        category = table.get(
            "category", ""
        ).strip().lower()

        section = table.get("section")

        if category == "data":
            target = "data_fields"

        elif category == "links":
            target = "links"

        else:
            continue

        for record in table.get("records", []):

            item = deepcopy(record)

            identity = (
                target,
                json.dumps(
                    item,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            )

            if identity not in document_lookup:

                item["source_sections"] = []

                document_lookup[identity] = item

                official_documentation[target].append(item)

            sections = document_lookup[identity][
                "source_sections"
            ]

            if section not in sections:
                sections.append(section)

    # ==================================================
    # 9. Share repeated documentation section groups
    # ==================================================

    documentation_section_groups = {}
    section_group_lookup = {}

    for category in ("data_fields", "links"):

        for record in official_documentation[category]:

            sections = record.pop("source_sections", [])

            identity = tuple(
                sorted(
                    sections,
                    key=lambda value: str(value),
                )
            )

            if identity not in section_group_lookup:

                reference = (
                    f"D{len(section_group_lookup) + 1}"
                )

                section_group_lookup[identity] = reference

                documentation_section_groups[reference] = (
                    list(identity)
                )

            record["section_group"] = (
                section_group_lookup[identity]
            )

    # ==================================================
    # 10. Return optimized section evidence
    # ==================================================

    return {
        "component": component,

        "provenance": deepcopy(pack["provenance"]),

        "source_reference_note": (
            "Resolve F identifiers using source_files. "
            "Resolve D identifiers using "
            "documentation_section_groups. "
            "Constructor fields listed in "
            "reused_attribute_fields retain their values "
            "from the matching local structured attribute. "
            "Distinguish C++ declarations, initializations, "
            "constructor modifications and official "
            "documentation. Documentation-only fields "
            "do not establish C++ ownership or inheritance. "
            "Missing values indicate unavailable evidence, "
            "not necessarily absent defaults or requirements."
        ),

        "source_files": source_files,

        "documentation_section_groups": (
            documentation_section_groups
        ),

        "architecture": architecture,

        "structured_attributes": structured_attributes,

        "constructor_evidence": constructor_evidence,

        "official_documentation": official_documentation,
    }


def build_mathematical_evidence(pack):
    """
    Build compact mathematical evidence without
    transmitting C++ implementation bodies.

    Preserve mathematical documentation, method
    interfaces, relevant attributes and provenance.
    """

    from copy import deepcopy

    component = pack["component"]
    evidence = pack["evidence"]
    documentation = evidence["documentation"]

    # ==================================================
    # 1. Shared source file references
    # ==================================================

    source_files = {}
    file_lookup = {}

    def file_ref(path):

        if not path:
            return None

        if path not in file_lookup:

            reference = f"F{len(file_lookup) + 1}"

            file_lookup[path] = reference
            source_files[reference] = path

        return file_lookup[path]

    # ==================================================
    # 2. Official mathematical documentation
    # ==================================================

    allowed_types = {
        "paragraph",
        "equation",
        "list",
    }

    introduction = [
        deepcopy(item)
        for item in documentation.get("introduction", [])
        if item.get("type") in allowed_types
    ]

    selected_sections = []

    for section in documentation.get("sections", []):

        title = section.get("title", "")

        if title.strip().lower() in ("example", "examples"):
            continue

        content = [
            deepcopy(item)
            for item in section.get("content", [])
            if item.get("type") in allowed_types
        ]

        if not content:
            continue

        # Exclude repetitive template architecture sections.

        is_template_section = any(
            item.get("type") == "paragraph"
            and item.get("text", "").strip().lower()
            == "templates:"
            for item in content
        )

        if is_template_section:

            # Preserve equations when available.

            content = [
                item
                for item in content
                if item.get("type") == "equation"
            ]

        if content:

            selected_sections.append({
                "title": title,
                "content": content,
            })

    official_documentation = {
        "introduction": introduction,
        "sections": selected_sections,
    }

    # ==================================================
    # 3. Compact method links
    # ==================================================

    method_links = []

    for method in evidence.get("method_links", []):

        declaration = method.get("declaration")

        compact_declaration = None

        if declaration:

            compact_declaration = {
                "file": file_ref(
                    declaration.get("file")
                ),
                "line": declaration.get("line"),
                "signature": declaration.get("signature"),
            }

        implementations = []

        for implementation in method.get(
            "implementations", []
        ):

            implementations.append({
                "file": file_ref(
                    implementation.get("file")
                ),
                "start_line": implementation.get(
                    "start_line"
                ),
                "end_line": implementation.get(
                    "end_line"
                ),
                "owner": implementation.get("owner"),
                "signature": implementation.get(
                    "signature"
                ),
                "kind": implementation.get("kind"),
            })

        method_links.append({
            "method": method["method"],
            "declaration": compact_declaration,
            "implementations": implementations,
            "status": method.get("status"),
        })

    # ==================================================
    # 4. Compact structured attributes
    # ==================================================

    structured_attributes = []

    attribute_fields = (
        "name",
        "sofa_name",
        "type",
        "category",
        "owner_class",
        "origin",
        "default_expression",
        "description",
        "line",
    )

    for attribute in evidence.get(
        "structured_attributes", []
    ):

        if attribute.get("category") in (
            "SOFA_Link",
            "SOFA_DeprecatedData",
        ):
            continue

        item = {
            key: deepcopy(attribute[key])
            for key in attribute_fields
            if attribute.get(key) is not None
        }

        if attribute.get("source_file"):

            item["source_file"] = file_ref(
                attribute["source_file"]
            )

        if isinstance(item.get("description"), str):

            item["description"] = " ".join(
                item["description"].split()
            )

        structured_attributes.append(item)

    # ==================================================
    # 5. Final mathematical payload
    # ==================================================

    return {
        "component": component,

        "provenance": deepcopy(pack["provenance"]),

        "source_reference_note": (
            "Resolve F identifiers using source_files. "
            "C++ method signatures and implementation "
            "locations establish interfaces and source "
            "locations, not internal algorithmic behavior. "
            "Distinguish general mathematical theory "
            "from officially documented formulations. "
            "No C++ implementation bodies are supplied."
        ),

        "source_files": source_files,

        "official_documentation": official_documentation,

        "method_links": method_links,

        "structured_attributes": structured_attributes,

        "code_snippets": [],

        "code_chunks": [],
    }

def build_internal_execution_evidence(pack):
    """
    Build compact implementation evidence for
    Internal Architecture and Execution.

    Preserve complete C++ method bodies, source traceability,
    execution context and specialization differences.

    Remove redundant code and compact supporting metadata
    without splitting or truncating implementation bodies.
    """

    import re
    from copy import deepcopy

    component = pack["component"]
    provenance = pack["provenance"]
    evidence = pack["evidence"]

    # ==================================================
    # 1. Shared source file references
    # ==================================================

    source_files = {}
    file_lookup = {}

    def file_ref(path):

        if not path:
            return None

        if path not in file_lookup:

            reference = f"F{len(file_lookup) + 1}"

            file_lookup[path] = reference
            source_files[reference] = path

        return file_lookup[path]

    # ==================================================
    # 2. Preserve complete C++ implementations
    # ==================================================

    raw_snippets = evidence.get("code_snippets", [])
    raw_chunks = evidence.get("code_chunks", [])

    implementations = []
    seen_implementations = set()

    for snippet in raw_snippets:

        identity = (
            snippet.get("source_file"),
            snippet.get("resolved_commit"),
            snippet.get("start_line"),
            snippet.get("end_line"),
            snippet.get("signature"),
            snippet.get("code"),
        )

        if identity in seen_implementations:
            continue

        seen_implementations.add(identity)

        item = {

            "method": snippet["method"],

            "file": file_ref(
                snippet["source_file"]
            ),

            "lines": [
                snippet["start_line"],
                snippet["end_line"],
            ],

            "code": snippet["code"],
        }

        # Preserve a distinct commit when necessary.

        resolved_commit = snippet.get(
            "resolved_commit"
        )

        if (
            resolved_commit
            and resolved_commit != provenance["code_commit"]
        ):

            item["commit"] = resolved_commit

        implementations.append(item)

    # ==================================================
    # 3. Preserve non-redundant AST chunks
    # ==================================================

    standalone_chunks = []

    for chunk in raw_chunks:

        covered = any(

            snippet.get("source_file")
            == chunk.get("source_file")

            and snippet.get("resolved_commit")
            == chunk.get("resolved_commit")

            and snippet.get("signature")
            == chunk.get("signature")

            and snippet.get("method")
            == chunk.get("method")

            and snippet["start_line"]
            <= chunk["start_line"]

            and snippet["end_line"]
            >= chunk["end_line"]

            and chunk.get("code")

            and chunk["code"]
            in snippet.get("code", "")

            for snippet in raw_snippets
        )

        if covered:
            continue

        item = {

            "method": chunk["method"],

            "signature": chunk.get("signature"),

            "file": file_ref(
                chunk["source_file"]
            ),

            "lines": [
                chunk["start_line"],
                chunk["end_line"],
            ],

            "chunk_index": chunk.get(
                "chunk_index"
            ),

            "code": chunk["code"],

            "active_scope_headers": deepcopy(
                chunk.get("active_scope_headers", [])
            ),

            "scope_continuity": deepcopy(
                chunk.get("scope_continuity", [])
            ),

            "ast_context": deepcopy(
                chunk.get("ast_context", [])
            ),
        }

        resolved_commit = chunk.get(
            "resolved_commit"
        )

        if (
            resolved_commit
            and resolved_commit != provenance["code_commit"]
        ):

            item["commit"] = resolved_commit

        standalone_chunks.append(item)

    # ==================================================
    # 4. Compact method interfaces
    # ==================================================

    method_interfaces = []

    available_definitions = {

        (
            item["method"],
            source_files[item["file"]],
            item["lines"][0],
            item["lines"][1],
        )

        for item in implementations
    }

    available_methods = {

        item["method"]

        for item in implementations
    }

    for method in evidence.get(
        "method_links", []
    ):

        declaration = method.get(
            "declaration"
        ) or {}

        item = {

            "method": method["method"],

            "declaration_file": file_ref(
                declaration.get("file")
            ),

            "declaration_line": declaration.get(
                "line"
            ),
        }

        missing_definitions = []

        for definition in method.get(
            "implementations", []
        ):

            identity = (

                method["method"],

                definition.get("file"),

                definition.get("start_line"),

                definition.get("end_line"),
            )

            if identity in available_definitions:
                continue

            missing_definitions.append({

                "file": file_ref(
                    definition.get("file")
                ),

                "lines": [
                    definition.get("start_line"),
                    definition.get("end_line"),
                ],

                "owner": definition.get("owner"),

                "signature": definition.get(
                    "signature"
                ),

                "kind": definition.get("kind"),
            })

        has_body = (
            method["method"] in available_methods
        )

        if not has_body or missing_definitions:

            item["signature"] = declaration.get(
                "signature"
            )

            item["status"] = method.get(
                "status"
            )

        if missing_definitions:

            item["definitions_without_body"] = (
                missing_definitions
            )

        method_interfaces.append(item)

    # ==================================================
    # 5. Compact constructor execution evidence
    # ==================================================

    constructors = []

    known_attributes = {

        attribute["name"]: attribute

        for attribute in evidence.get(
            "structured_attributes", []
        )

        if attribute.get("name")
    }

    for file_data in evidence.get(
        "constructor_metadata", []
    ):

        for constructor in file_data.get(
            "constructors", []
        ):

            initializers = []

            for initializer in constructor.get(
                "initializers", []
            ):

                name = initializer.get(
                    "attribute"
                )

                expression = initializer.get(
                    "expression", ""
                )

                attribute = known_attributes.get(
                    name
                )

                category = (
                    attribute.get("category")
                    if attribute
                    else None
                )

                if (

                    isinstance(expression, str)

                    and "initData(" in expression

                    and attribute is not None

                    and category == "SOFA_Data"

                    and attribute.get(
                        "default_expression"
                    ) is not None

                ):

                    # Compact data initialization metadata.
                    # Preserve the field name, default value
                    # and source location.

                    initializers.append({

                        "attribute": name,

                        "sofa_name": attribute.get(
                            "sofa_name"
                        ),

                        "default": attribute.get(
                            "default_expression"
                        ),

                        "line": initializer.get(
                            "line"
                        ),
                    })

                else:

                    # Preserve parent constructors, links,
                    # internal state and unknown initializers.

                    initializers.append(
                        deepcopy(initializer)
                    )

            item = {

                "file": file_ref(
                    file_data["source_file"]
                ),

                "class": constructor.get(
                    "class"
                ),

                "line": constructor.get(
                    "line"
                ),

                "signature": constructor.get(
                    "signature"
                ),
            }

            if initializers:

                item["initializers"] = initializers

            if constructor.get("body"):

                item["body"] = deepcopy(
                    constructor["body"]
                )

            constructors.append(item)

    # ==================================================
    # 6. Select attributes used in implementation
    # ==================================================

    combined_code = "\n".join(

        item["code"]

        for item in implementations + standalone_chunks
    )

    # Include constructor evidence in identifier matching.

    combined_code += "\n" + str(constructors)

    identifiers = set(

        re.findall(
            r"\b[A-Za-z_][A-Za-z0-9_]*\b",
            combined_code,
        )
    )

    structured_attributes = []

    attribute_fields = (

        "name",

        "sofa_name",

        "owner_class",

        "default_expression",

        "line",
    )

    for attribute in evidence.get(
        "structured_attributes", []
    ):

        if attribute.get("name") not in identifiers:
            continue

        item = {

            key: deepcopy(attribute[key])

            for key in attribute_fields

            if attribute.get(key) is not None
        }

        if attribute.get("source_file"):

            item["file"] = file_ref(
                attribute["source_file"]
            )

        initialization_source = attribute.get(
            "initialization_source"
        )

        # Preserve the actual initialization location
        # when a default value originates in another file.

        if (
            initialization_source
            and item.get("default_expression") is not None
        ):

            item["default_source"] = [

                file_ref(
                    initialization_source.get("file")
                ),

                initialization_source.get("line"),
            ]

        structured_attributes.append(item)

    # ==================================================
    # 7. Compact architecture and inheritance
    # ==================================================

    raw_architecture = evidence.get(
        "architecture", {}
    )

    classes = []

    for entry in raw_architecture.get(
        "classes", []
    ):

        item = {

            "class": entry.get("class"),

            "parents": deepcopy(
                entry.get("parents", [])
            ),

            "file": file_ref(
                entry.get("source_file")
            ),

            "line": entry.get("line"),
        }

        classes.append(item)

    # ==================================================
    # 8. Minimal official documentation
    # ==================================================

    documentation = evidence.get(
        "documentation", {}
    )

    introduction = [

        deepcopy(item)

        for item in documentation.get(
            "introduction", []
        )

        if item.get("type") == "paragraph"
    ]

    # ==================================================
    # 9. Final implementation evidence
    # ==================================================

    return {

        "component": component,

        "provenance": {

            "code_commit": provenance["code_commit"],

            "documentation": {

                "canonical_url": provenance.get(
                    "documentation", {}
                ).get("canonical_url"),

                "version_match_verified": provenance.get(
                    "documentation", {}
                ).get("version_match_verified"),
            },
        },

        "source_files": source_files,

        "classes": classes,

        "method_interfaces": method_interfaces,

        "structured_attributes": structured_attributes,

        "constructors": constructors,

        "implementations": implementations,

        "standalone_chunks": standalone_chunks,

        "official_documentation": {

            "introduction": introduction,

            "sections": [],
        },
    }

def build_diagnostics_usage_evidence(pack):
    """
    Build compact, evidence-grounded documentation
    context for Diagnostics and Usage.

    Selection is generic and component-independent.
    """

    import re
    import json

    component = pack.get("component")
    evidence = pack.get("evidence", {})
    provenance = pack.get("provenance", {})

    documentation = evidence.get("documentation", {})
    attributes = evidence.get("structured_attributes", [])
    snippets = evidence.get("code_snippets", [])
    chunks = evidence.get("code_chunks", [])
    constructors = evidence.get("constructor_metadata", [])
    architecture = evidence.get("architecture", {})
    method_links = evidence.get("method_links", [])

    source_files = {}
    file_index = {}
    limitations = []

    # ==============================================
    # 1. Compact source references
    # ==============================================

    def file_ref(path):

        if not path:
            return None

        if path not in file_index:

            ref = f"F{len(file_index) + 1}"

            file_index[path] = ref
            source_files[ref] = path

        return file_index[path]

    def compact(record):
        return {
            key: value
            for key, value in record.items()
            if value is not None
            and value != ""
            and value != []
            and value != {}
        }

    def unique(records):

        result = []
        seen = set()

        for record in records:

            identity = json.dumps(
                record,
                sort_keys=True,
                ensure_ascii=False,
            )

            if identity not in seen:

                seen.add(identity)
                result.append(record)

        return result

    # ==============================================
    # 2. Documentation and example selection
    # ==============================================

    usage_pattern = re.compile(
        r"\b(?:usage|using|use|used|configuration|"
        r"configure|parameter|require|required|requires|"
        r"assume|assumes|assumption|compatible|"
        r"compatibility|support|supported|limitation|"
        r"warning|note|recommend|restriction|"
        r"convergence|divergence|initialization|"
        r"integration|prerequisite|example)\w*\b",
        re.I,
    )

    usage_title_pattern = re.compile(
        r"\b(?:usage|configuration|examples?|"
        r"limitations?|requirements?|prerequisites?|"
        r"warnings?|compatibility|diagnostics?)\b",
        re.I,
    )

    scene_name_pattern = re.compile(
        r"^[\w.\-/\\]+\.(?:scn|xml|py|pscn)$",
        re.I,
    )

    usage_documentation = []
    example_candidates = []

    sections = [
        {
            "title": "Introduction",
            "content": documentation.get(
                "introduction", []
            ),
        },
        *documentation.get("sections", []),
    ]

    xml_component_pattern = re.compile(
        r"<(?:[\w.-]+:)?"
        + re.escape(component or "")
        + r"(?=[\s/>])"
    )

    python_component_pattern = re.compile(
        r"\baddObject\s*\(\s*['\"]"
        + re.escape(component or "")
        + r"['\"]"
    )

    for section in sections:

        title = section.get("title", "")
        relevant_title = bool(
            usage_title_pattern.search(title)
        )

        current_scene = None

        for block in section.get("content", []):

            if not isinstance(block, dict):
                continue

            block_type = block.get("type")

            text = block.get("text", "")

            if not isinstance(text, str):
                text = ""

            # Keep the original scene name.

            if (
                block_type == "paragraph"
                and scene_name_pattern.fullmatch(
                    text.strip()
                )
            ):

                current_scene = text.strip()
                continue

            # Identify genuine component examples.

            if block_type == "code":

                if xml_component_pattern.search(text):

                    language = "xml"

                elif python_component_pattern.search(text):

                    language = "python"

                else:

                    continue

                example_candidates.append(
                    compact({
                        "section": title,
                        "scene": current_scene,
                        "language": language,
                        "code": text,
                    })
                )

                continue

            # Keep practical text and lists.

            if block_type not in (
                "paragraph",
                "list",
                "link",
            ):
                continue

            searchable = json.dumps(
                block,
                ensure_ascii=False,
            )

            if (
                relevant_title
                or usage_pattern.search(searchable)
            ):

                usage_documentation.append({
                    "section": title,
                    "content": block,
                })

    usage_documentation = unique(
        usage_documentation
    )

    # Prefer a complete XML example over Python.
    # Never truncate a selected example.

    example_candidates.sort(
        key=lambda item: (
            item["language"] != "xml",
            len(item["code"]),
        )
    )

    usage_example = (
        example_candidates[0]
        if example_candidates
        else None
    )

    if usage_example is None:

        limitations.append(
            "No concrete usage example containing "
            "the target component was found in "
            "the supplied documentation."
        )

    else:

        usage_example["validation"] = (
            "Documented example; runtime execution "
            "has not been verified."
        )

    # ==============================================
    # 3. Generic diagnostic and edge-case detection
    # ==============================================

    diagnostic_pattern = re.compile(
        r"\bmsg_(?:error|warning|info|debug)"
        r"(?:_when)?\s*\("
        r"|\b(?:assert|static_assert)\s*\("
        r"|\bthrow\b"
        r"|\bComponentState::Invalid\b"
        r"|\bisComponentStateInvalid\s*\("
    )

    control_flow_pattern = re.compile(
        r"\b(?:if|while|switch)\s*\("
    )

    edge_pattern = re.compile(
        r"\bnullptr\b|\bNULL\b"
        r"|\b\w*(?:[Cc]onverg|[Dd]iverg|"
        r"[Tt]hreshold|[Tt]olerance|"
        r"[Ii]nvalid|[Ff]ail|[Rr]esidual|"
        r"[Dd]enominator)\w*\b"
        r"|(?:==|!=|<=|>=|<|>)\s*0(?:\.0)?\b"
        r"|\b(?:isnan|isfinite|isinf)\s*\("
        r"|\b(?:break|continue)\s*;"
        r"|\breturn\s*;"
    )

    integration_pattern = re.compile(
        r"\b(?:initLink|setRequired|setReadOnly|"
        r"getContext|canCreate|dynamic_cast|"
        r"getLink|addSlave|findLinkDest)\b"
    )

    division_pattern = re.compile(
        r"(?<!/)/(?![/*=])\s*"
        r"(?:[A-Za-z_][\w.]*|\()"
    )

    def selection_reasons(code):

        # Ignore comments when detecting markers.
        # The original code remains unchanged.

        searchable = re.sub(
            r"/\*[\s\S]*?\*/|//[^\n]*",
            "",
            code,
        )

        reasons = []

        if diagnostic_pattern.search(searchable):

            reasons.append(
                "explicit_diagnostic"
            )

        if (
            control_flow_pattern.search(searchable)
            and edge_pattern.search(searchable)
        ):

            reasons.append(
                "edge_case_candidate"
            )

        if integration_pattern.search(searchable):

            reasons.append(
                "integration_constraint_candidate"
            )

        if division_pattern.search(searchable):

            reasons.append(
                "numerical_precondition_candidate"
            )

        return reasons

    diagnostic_implementations = []
    selected_records = []

    def add_code_record(record, kind, force=False):

        code = record.get("code", "")

        if not isinstance(code, str) or not code.strip():
            return

        reasons = selection_reasons(code)

        if not reasons:

            if not force:
                return

            reasons = [
                "compact_implementation_fallback"
            ]

        entry = compact({
            "method": record.get("method"),
            "file": file_ref(
                record.get("source_file")
            ),
            "lines": [
                record.get("start_line"),
                record.get("end_line"),
            ],
            "kind": kind,
            "selection_reasons": reasons,
            "code": code,
        })

        resolved_commit = record.get(
            "resolved_commit"
        )

        if (
            resolved_commit
            and resolved_commit
            != provenance.get("code_commit")
        ):

            entry["commit"] = resolved_commit

        if kind == "ast_chunk":

            entry.update(compact({
                "signature": record.get("signature"),
                "chunk_index": record.get("chunk_index"),
                "active_scope_headers":
                    record.get("active_scope_headers"),
                "scope_continuity":
                    record.get("scope_continuity"),
            }))

        diagnostic_implementations.append(entry)
        selected_records.append(record)

    for snippet in snippets:

        add_code_record(
            snippet,
            "implementation",
        )

    # Generic fallback for compact components when
    # lexical heuristics select no implementations.

    MAX_FALLBACK_CODE_CHARACTERS = 4000

    total_implementation_characters = sum(
        len(record.get("code") or "")
        for record in snippets
    )

    if (
        not diagnostic_implementations
        and 0 < total_implementation_characters
        <= MAX_FALLBACK_CODE_CHARACTERS
    ):

        for snippet in snippets:

            add_code_record(
                snippet,
                "implementation",
                force=True,
            )

        limitations.append(
            "Compact implementations were retained "
            "for contextual analysis because no "
            "explicit diagnostic candidates were "
            "identified by the primary heuristics."
        )

    # ==============================================
    # 4. Non-redundant AST evidence
    # ==============================================

    def covered_by_selected_snippet(chunk):

        chunk_code = chunk.get("code", "")

        if not chunk_code:
            return False

        chunk_start = chunk.get("start_line")
        chunk_end = chunk.get("end_line")

        if not isinstance(chunk_start, int):
            return False

        if not isinstance(chunk_end, int):
            return False

        for snippet in selected_records:

            start = snippet.get("start_line")
            end = snippet.get("end_line")

            if not isinstance(start, int):
                continue

            if not isinstance(end, int):
                continue

            if (
                snippet.get("source_file")
                == chunk.get("source_file")

                and snippet.get("resolved_commit")
                == chunk.get("resolved_commit")

                and snippet.get("method")
                == chunk.get("method")

                and snippet.get("signature")
                == chunk.get("signature")

                and start <= chunk_start
                and end >= chunk_end

                and chunk_code
                in snippet.get("code", "")
            ):

                return True

        return False

    for chunk in chunks:

        if covered_by_selected_snippet(chunk):
            continue

        add_code_record(
            chunk,
            "ast_chunk",
        )

    diagnostic_implementations = unique(
        diagnostic_implementations
    )

    selected_code = "\n".join(
        entry["code"]
        for entry in diagnostic_implementations
    )

    # ==============================================
    # 5. Configuration evidence
    # ==============================================

    configuration = []

    selected_attribute_names = set()

    for attribute in attributes:

        name = attribute.get("name", "")
        sofa_name = attribute.get("sofa_name", "")
        category = str(
            attribute.get("category", "")
        ).lower()

        # Keep exposed configuration fields, not
        # arbitrary internal C++ member variables.

        exposed = (
            category in ("sofa_data", "sofa_link")
            or bool(sofa_name)
        )

        if not exposed:
            continue

        description = attribute.get(
            "description", ""
        ) or ""

        used_in_code = bool(
            name
            and re.search(
                r"\b" + re.escape(name) + r"\b",
                selected_code,
            )
        )

        relevant_description = bool(
            usage_pattern.search(description)
            or edge_pattern.search(description)
        )

        required = attribute.get("required")

        is_required = (
            required is True
            or str(required).lower() == "true"
        )

        used_in_example = bool(
            usage_example
            and sofa_name
            and re.search(
                r"\b" + re.escape(sofa_name)
                + r"\s*=",
                usage_example["code"],
            )
        )

        # Retain relevant parameters and links.
        # If no code was selected, retain the
        # available exposed configuration.

        # Retain all exposed configuration fields.
        # Lexical relevance alone must not remove
        # potentially useful user-facing parameters.

        selected_attribute_names.add(name)

        entry = compact({
            "name": name,
            "sofa_name": sofa_name,
            "description": description,
            "type": attribute.get("type"),
            "default": attribute.get(
                "default_expression"
            ),
            "required": required,
            "owner": attribute.get("owner_class"),
            "origin": attribute.get("origin"),
            "file": file_ref(
                attribute.get("source_file")
            ),
            "line": attribute.get("line"),
        })

        initial_source = attribute.get(
            "initialization_source"
        )

        if isinstance(initial_source, dict):

            entry["default_source"] = compact({
                "file": file_ref(
                    initial_source.get("file")
                ),
                "line": initial_source.get("line"),
                "commit": initial_source.get("commit"),
            })

        configuration.append(entry)

    # ==============================================
    # 6. Constructor constraints
    # ==============================================

    configuration_constraints = []

    constraint_pattern = re.compile(
        r"\b(?:initLink|setRequired|setReadOnly|"
        r"setGroup|setValue|setParent|setPersistent|"
        r"setDisplayed|setAutoLink|setFlag)\s*\("
    )

    for file_data in constructors:

        ref = file_ref(
            file_data.get("source_file")
        )

        for constructor in file_data.get(
            "constructors", []
        ):

            relevant_initializers = []

            for initializer in constructor.get(
                "initializers", []
            ):

                expression = initializer.get(
                    "expression", ""
                ) or ""

                name = initializer.get(
                    "attribute", ""
                )

                is_relevant = bool(
                    constraint_pattern.search(expression)
                )

                missing_configuration = (
                    name not in selected_attribute_names
                    and "initData(" in expression
                )

                if (
                    is_relevant
                    or missing_configuration
                ):

                    relevant_initializers.append(
                        initializer
                    )

            body = constructor.get("body")

            if not isinstance(body, str):
                body = ""

            relevant_body = bool(
                constraint_pattern.search(body)
                or selection_reasons(body)
            )

            if (
                relevant_initializers
                or relevant_body
            ):

                configuration_constraints.append(
                    compact({
                        "file": ref,
                        "line": constructor.get("line"),
                        "signature":
                            constructor.get("signature"),
                        "initializers":
                            relevant_initializers,
                        "body":
                            body if relevant_body else None,
                    })
                )

        # Preserve explicit metadata for deprecated
        # and required fields when available.

        for metadata in file_data.get(
            "metadata", []
        ):

            if not isinstance(metadata, dict):
                continue

            for key in (
                "deprecated_fields",
                "required_fields",
            ):

                if metadata.get(key):

                    configuration_constraints.append({
                        "file": ref,
                        "kind": key,
                        "records": metadata[key],
                    })

    # ==============================================
    # 7. Integration and compatibility
    # ==============================================

    integration_constraints = []

    for cls in architecture.get("classes", []):

        if not cls.get("parents"):
            continue

        integration_constraints.append(
            compact({
                "class": cls.get("class"),
                "parents": cls.get("parents"),
                "file": file_ref(
                    cls.get("source_file")
                ),
                "line": cls.get("line"),
            })
        )

    # Official documentation template sections.
    # Do not replicate their Data tables.

    templates = {
        table.get("section")
        for table in documentation.get("tables", [])
        if isinstance(table, dict)
        and table.get("section")
    }

    if templates:

        integration_constraints.append({
            "kind": "documented_template_sections",
            "names": sorted(templates),
        })

    # Preserve unresolved implementation references
    # when the selected evidence uses the method.

    for method in method_links:

        if method.get("implementations"):
            continue

        name = method.get("method")

        if not name:
            continue

        if not re.search(
            r"\b" + re.escape(name) + r"\s*\(",
            selected_code,
        ):
            continue

        declaration = method.get("declaration") or {}

        integration_constraints.append(
            compact({
                "kind": "unresolved_implementation",
                "method": name,
                "status": method.get("status"),
                "signature": declaration.get("signature"),
                "file": file_ref(
                    declaration.get("file")
                ),
                "line": declaration.get("line"),
            })
        )

    # ==============================================
    # 8. Evidence limitations
    # ==============================================

    doc_provenance = provenance.get(
        "documentation", {}
    )

    if not doc_provenance.get(
        "version_match_verified", False
    ):

        limitations.append(
            "The documentation version has not "
            "been verified against the pinned "
            "source-code commit."
        )

    if not diagnostic_implementations:

        limitations.append(
            "No diagnostic or edge-case implementation "
            "was selected by the generic heuristics. "
            "This does not establish the absence "
            "of runtime failure conditions."
        )

    if not configuration:

        limitations.append(
            "No relevant structured configuration "
            "fields were selected."
        )

    limitations.append(
        "Code selection markers identify candidates, "
        "not validated failure conditions. "
        "No runtime tests have been performed."
    )

    # ==============================================
    # 9. Final payload
    # ==============================================

    return {
        "component": component,

        "provenance": {
            "code_commit": provenance.get("code_commit"),

            "documentation": compact({
                "canonical_url":
                    doc_provenance.get("canonical_url"),

                "version_match_verified":
                    doc_provenance.get(
                        "version_match_verified"
                    ),
            }),
        },

        "source_files": source_files,

        "usage_documentation":
            usage_documentation,

        "usage_example":
            usage_example,

        "configuration":
            unique(configuration),

        "configuration_constraints":
            unique(configuration_constraints),

        "diagnostic_implementations":
            diagnostic_implementations,

        "integration_constraints":
            unique(integration_constraints),

        "evidence_limitations":
            limitations,
    }

