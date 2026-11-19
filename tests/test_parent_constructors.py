
import json
from pathlib import Path

from config.settings import INTERMEDIATE_DIR
from core.cpp.extractor import SofaExtractor


def test_parent_constructor_metadata():
    component = "CGLinearSolver"

    metadata_path = (
        Path(INTERMEDIATE_DIR)
        / component
        / "parent_implementations.json"
    )

    sources = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    extractor = SofaExtractor()
    total = 0

    for source in sources:
        path = Path(source["local_path"])

        assert path.is_file(), f"Missing file: {path}"

        code = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        metadata = extractor.extract_constructor_metadata(code)

        print(f"\n[PARENT] {source['parent']}")
        print(f"[FILE] {path.name}")
        print(f"[CONSTRUCTORS FOUND] {len(metadata)}")

        for constructor in metadata:
            print(f"  [CONSTRUCTOR] {constructor['constructor']}")

            for param in constructor["sofa_parameters"]:
                print(
                    f"    [SOFA PARAM] {param['attribute']}"
                    f" | Default: {param['default_expression']}"
                    f" | Name: {param['sofa_name']}"
                )
                total += 1

    print(f"\n[TOTAL PARAMETERS FOUND] {total}")



def test_graph_initialization():

    component = "CGLinearSolver"

    metadata_path = (
        Path(INTERMEDIATE_DIR)
        / component
        / "parent_implementations.json"
    )

    sources = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    for source in sources:

        path = Path(source["local_path"])
        lines = path.read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines()

        matches = [
            i for i, line in enumerate(lines)
            if "d_graph" in line
        ]

        if not matches:
            continue

        print(f"\n[FILE] {path.name}")

        for i in matches:
            print(f"\n[MATCH] Line {i + 1}")

            for j in range(
                max(0, i - 3),
                min(len(lines), i + 4)
            ):
                print(f"{j + 1}: {lines[j]}")
