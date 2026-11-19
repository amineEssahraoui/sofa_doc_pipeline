
import json
from pathlib import Path

from config.settings import INTERMEDIATE_DIR
from core.cpp.extractor import SofaExtractor


def enrich_inherited_data(component="CGLinearSolver"):

    folder = Path(INTERMEDIATE_DIR) / component

    unified_path = folder / "unified_data.json"
    implementations_path = folder / "parent_implementations.json"

    unified = json.loads(unified_path.read_text(encoding="utf-8"))
    implementations = json.loads(
        implementations_path.read_text(encoding="utf-8")
    )

    extractor = SofaExtractor()
    enriched_count = 0

    for source in implementations:
        if source["resolved_commit"] != unified["resolved_commit"]:
            raise ValueError(
                f"Commit mismatch for parent {source['parent']}: "
                f"expected {unified['resolved_commit']}, "
                f"got {source['resolved_commit']}"
            )
        
        path = Path(source["local_path"])
        code = path.read_text(encoding="utf-8", errors="replace")

        constructors = extractor.extract_constructor_metadata(code)

        for constructor in constructors:
            for param in constructor["sofa_parameters"]:

                for attr in unified["attributes"]:

                    if (
                        attr["origin"] == "inherited_direct"
                        and attr["name"] == param["attribute"]
                        and attr["owner_class"].split("<")[0].split("::")[-1]
                        == source["parent"]
                    ):
                        attr["default_expression"] = param[
                            "default_expression"
                        ]
                        attr["sofa_name"] = param["sofa_name"]
                        attr["description"] = param["description"]

                        attr["initialization_source"] = {
                            "file": source["repository_path"],
                            "line": param["line"],
                            "commit": source["resolved_commit"]
                        }

                        enriched_count += 1

    output = folder / "unified_data_enriched.json"

    output.write_text(
        json.dumps(unified, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n[COMPONENT] {component}")

    for attr in unified["attributes"]:
        print(
            f"[DATA] {attr['name']} "
            f"| Default: {attr['default_expression']} "
            f"| SOFA name: {attr['sofa_name']}"
        )

    print(f"\n[ENRICHED] {enriched_count} inherited parameters")
    print(f"[SAVED] {output}")

    return unified


if __name__ == "__main__":
    enrich_inherited_data()
