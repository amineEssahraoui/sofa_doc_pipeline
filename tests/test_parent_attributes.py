
from pathlib import Path

from config.settings import RAW_CODE_DIR, INTERMEDIATE_DIR
from core.cpp.extractor import SofaExtractor


def test_parent_attributes():

    extractor = SofaExtractor()

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
    )

    parents = [
        "MatrixLinearSolver.h",
        "IterativeSolver.h"
    ]

    for parent in parents:

        files = list(cache.rglob(parent))

        assert files, f"Parent file not found: {parent}"

        # Use the most recent downloaded version.
        # The correct SHA must ultimately match the component.
        file_path = files[0]

        print(f"\n[PARENT] {parent}")
        print(f"[SOURCE] {file_path}")

        source_code = file_path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        attributes = extractor.extract_attributes(source_code)
        assert isinstance(attributes, list)

        for attr in attributes:
            if attr["category"] == "SOFA_Data":
                print(
                    f"  [DATA] {attr['owner_class']}::"
                    f"{attr['name']} ({attr['type']}) "
                    f"- Line {attr['line']}"
                )

    print("\n[SUCCESS] Parent attributes inspected")



def test_missing_inherited_fields():

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
        / "5156bf1d6bda91b0a8b4a4812e4e71919fcab3d1"
    )

    for filename in ["MatrixLinearSolver.h", "IterativeSolver.h"]:

        files = list(cache.rglob(filename))
        assert len(files) == 1, f"Expected one file: {filename}"

        path = files[0]
        lines = path.read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines()

        print(f"\n[FILE] {filename}")

        for index, line in enumerate(lines):
            if any(name in line for name in ["d_maxIter", "d_tolerance"]):
                print(f"\n[MATCH] Line {index + 1}")

                for j in range(max(0, index - 2), min(len(lines), index + 3)):
                    print(f"{j + 1}: {lines[j]}")


def test_iterative_solver_ast():

    from core.cpp.cpp_parser import SofaCppParser

    parser = SofaCppParser()

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
        / "5156bf1d6bda91b0a8b4a4812e4e71919fcab3d1"
    )

    files = list(cache.rglob("IterativeSolver.h"))
    assert len(files) == 1

    tree, source = parser.parse_file(files[0])

    targets = {"d_maxIter", "d_tolerance"}

    def visit(node, parents=()):

        if node.type == "field_declaration":

            content = parser.get_node_text(node, source)

            if any(name in content for name in targets):

                print("\n[FIELD]", content)
                print("[PARENTS]", " -> ".join(parents))
                print("[AST]", node)

        for child in node.named_children:
            visit(child, parents + (node.type,))

    visit(tree.root_node)


def test_iterative_solver_structure():
    from core.cpp.cpp_parser import SofaCppParser

    parser = SofaCppParser()

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
        / "5156bf1d6bda91b0a8b4a4812e4e71919fcab3d1"
    )

    files = list(cache.rglob("IterativeSolver.h"))
    assert len(files) == 1

    tree, source = parser.parse_file(files[0])
    lines = source.decode("utf-8", errors="replace").splitlines()

    print("\n[SOURCE] Lines 25-55")
    for i in range(24, min(55, len(lines))):
        print(f"{i + 1}: {lines[i]}")

    print("\n[AST NODES] Lines 35-50")

    def visit(node, depth=0):
        start = node.start_point.row + 1
        end = node.end_point.row + 1

        if start <= 50 and end >= 35 and depth <= 5:
            print(
                "  " * depth,
                node.type,
                f"lines {start}-{end}"
            )

        for child in node.named_children:
            if child.start_point.row + 1 <= 50 and child.end_point.row + 1 >= 35:
                visit(child, depth + 1)

    visit(tree.root_node)

def test_parent_data_regression():
    from core.cpp.cpp_parser import SofaCppParser

    extractor = SofaExtractor()
    parser = SofaCppParser()

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
        / "5156bf1d6bda91b0a8b4a4812e4e71919fcab3d1"
    )

    expected = {
        "IterativeSolver.h": {
            "d_maxIter",
            "d_tolerance",
            "d_graph"
        },
        "MatrixLinearSolver.h": {
            "d_parallelInverseProduct",
            "d_factorizationInvalidation"
        }
    }

    for filename, names in expected.items():
        files = list(cache.rglob(filename))
        assert len(files) == 1

        source = files[0].read_text(
            encoding="utf-8",
            errors="replace"
        )

        attributes = extractor.extract_attributes(source)

        found = {
            attr["name"]
            for attr in attributes
            if attr["category"] == "SOFA_Data"
        }

        print(f"\n[PARENT] {filename}")
        print(f"[FOUND] {sorted(found)}")
        print(f"[MISSING] {sorted(names - found)}")

        assert names <= found, (
            f"Missing Data<T> in {filename}: {names - found}"
        )


def test_factorization_ast_regression():
    from core.cpp.cpp_parser import SofaCppParser

    parser = SofaCppParser()

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
        / "5156bf1d6bda91b0a8b4a4812e4e71919fcab3d1"
    )

    files = list(cache.rglob("MatrixLinearSolver.h"))
    assert len(files) == 1

    source = files[0].read_text(
        encoding="utf-8",
        errors="replace"
    )

    lines = source.splitlines()

    print("\n[SOURCE CONTEXT]")
    for i, line in enumerate(lines):
        if "d_factorizationInvalidation" in line:
            for j in range(max(0, i - 4), min(len(lines), i + 5)):
                print(f"{j + 1}: {lines[j]}")

    def inspect(tree, source_bytes, label):
        print(f"\n[{label}]")

        target = b"d_factorizationInvalidation"
        position = source_bytes.find(target)

        assert position >= 0, "Attribute not found in source"

        def visit(node):
            if not (
                node.start_byte <= position < node.end_byte
            ):
                return

            print(
                node.type,
                f"lines {node.start_point.row + 1}"
                f"-{node.end_point.row + 1}"
            )

            for child in node.named_children:
                visit(child)

        visit(tree.root_node)

    # Current parser: SOFA export macros masked
    tree, source_bytes = parser.parse_source(source)
    inspect(tree, source_bytes, "WITH MACRO MASKING")

    # Original Tree-sitter parser: no masking
    original_bytes = source.encode("utf-8")
    original_tree = parser.parser.parse(original_bytes)

    inspect(original_tree, original_bytes, "WITHOUT MACRO MASKING")


def test_parent_initialization_locations():
    import json

    index = (
        Path(INTERMEDIATE_DIR)
        / "CGLinearSolver"
        / "includes.json"
    )

    data = json.loads(index.read_text(encoding="utf-8"))
    sha = data["resolved_commit"]

    cache = (
        Path(RAW_CODE_DIR)
        / "_shared_cache"
        / "sofa-framework"
        / "sofa"
        / sha
    )

    for filename in ["IterativeSolver.h", "MatrixLinearSolver.h"]:
        files = list(cache.rglob(filename))
        assert len(files) == 1

        print(f"\n[PARENT] {filename}")

        lines = files[0].read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines()

        for i, line in enumerate(lines, 1):
            if (
                "initData(" in line
                or "IterativeSolver(" in line
                or "MatrixLinearSolver(" in line
            ):
                print(f"[LINE {i}] {line.strip()}")
