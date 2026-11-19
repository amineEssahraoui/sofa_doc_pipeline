
import json
from pathlib import Path

from config.settings import INTERMEDIATE_DIR, RAW_CODE_DIR
from core.cpp.extractor import SofaExtractor


def build_unified_data(component="CGLinearSolver"):

    input_path = (
        Path(INTERMEDIATE_DIR)
        / component
        / "includes.json"
    )

    data = json.loads(input_path.read_text(encoding="utf-8"))
    sha = data["resolved_commit"]

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
        / sha
    )

    extractor = SofaExtractor()
    unified = []

    # 1. Local Data<T>
    for file_data in data["files"]:
        for attr in file_data.get("attributes", []):
            if attr["category"] != "SOFA_Data":
                continue

            unified.append({
                **attr,
                "origin": "local",
                "source_file": file_data["file"],
                "default_expression": None,
                "sofa_name": None,
                "description": None,
                "required": None
            })

    # 2. Enrich local attributes using constructor metadata
    for file_data in data["files"]:
        for constructor in file_data.get("constructor_metadata", []):
            for param in constructor["sofa_parameters"]:
                for attr in unified:
                    if (
                        attr["origin"] == "local"
                        and attr["name"] == param["attribute"]
                    ):
                        attr["default_expression"] = param["default_expression"]
                        attr["sofa_name"] = param["sofa_name"]
                        attr["description"] = param["description"]

            for required in constructor["required_fields"]:
                for attr in unified:
                    if attr["name"] == required["attribute"]:
                        attr["required"] = required["required_expression"]

    parent_sources_path = input_path.parent / "parent_sources.json"

    parent_sources = json.loads(
        parent_sources_path.read_text(encoding="utf-8")
    )

    parent_sources_by_name = {
        parent["parent"]: parent
        for parent in parent_sources
        if parent["status"] in ("cached", "downloaded")
    }

    # 3. Direct parent attributes
    for dependency in data["parent_dependencies"]:

        if dependency["status"] != "resolved":
            continue

        parent_name = dependency["parent_name"]

        parent_source = parent_sources_by_name.get(parent_name)

        if parent_source is None:
            raise FileNotFoundError(
                f"No downloaded source for parent {parent_name}"
            )

        if parent_source["resolved_commit"] != sha:
            raise ValueError(
                f"Commit mismatch for parent {parent_name}"
            )

        if not Path(parent_source["repository_path"]).as_posix().endswith(
            dependency["header_path"]
        ):
            raise ValueError(
                f"Parent path mismatch for {parent_name}"
            )

        path = Path(parent_source["local_path"])

        if not path.is_file():
            raise FileNotFoundError(
                f"Missing cached parent: {path}"
            )
        source = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        attributes = extractor.extract_attributes(source)

        for attr in attributes:

            if attr["category"] != "SOFA_Data":
                continue

            # Keep attributes belonging to the target parent,
            # not unrelated classes declared in the same file.
            owner = attr["owner_class"]
            owner_base = owner.split("<", 1)[0].split("::")[-1]

            if owner_base != parent_name:
                continue

            unified.append({
                **attr,
                "origin": "inherited_direct",
                "source_file": parent_source["repository_path"],
                "default_expression": None,
                "sofa_name": None,
                "description": None,
                "required": None
            })

    # 4. Apply required flags observed in CGLinearSolver constructor
    for file_data in data["files"]:
        for constructor in file_data.get("constructor_metadata", []):
            for required in constructor["required_fields"]:
                for attr in unified:
                    if attr["name"] == required["attribute"]:
                        attr["required"] = required["required_expression"]

    result = {
        "component": component,
        "resolved_commit": sha,
        "scope": "local_and_direct_parents",
        "attributes": unified
    }

    output = input_path.parent / "unified_data.json"

    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n[COMPONENT] {component}")

    for attr in unified:
        print(
            f"[DATA] {attr['name']} "
            f"| {attr['owner_class']} "
            f"| {attr['origin']} "
            f"| Default: {attr['default_expression']} "
            f"| Required: {attr['required']}"
        )

    print(f"\n[TOTAL] {len(unified)} Data<T>")
    print(f"[SUCCESS] {output}")

    return result


if __name__ == "__main__":
    build_unified_data()
