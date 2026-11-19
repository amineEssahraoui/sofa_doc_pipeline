
import json
from pathlib import Path

from config.settings import INTERMEDIATE_DIR
from core.ingestion.ingestor import SofaIngestor


def test_parent_implementation_paths():

    index_path = (
        Path(INTERMEDIATE_DIR)
        / "CGLinearSolver"
        / "includes.json"
    )

    data = json.loads(index_path.read_text(encoding="utf-8"))
    sha = data["resolved_commit"]

    ingestor = SofaIngestor()

    repository_files = ingestor.get_repository_files(
        "sofa-framework",
        "sofa",
        sha
    )

    parents = ["IterativeSolver", "MatrixLinearSolver"]

    for parent in parents:
        print(f"\n[PARENT] {parent}")

        candidates = [
            path for path in repository_files
            if Path(path).name in {
                f"{parent}.cpp",
                f"{parent}.inl",
                f"{parent}.h"
            }
        ]

        for path in sorted(candidates):
            print(f"  [CANDIDATE] {path}")

        assert candidates, (
            f"No source files found for {parent}"
        )
