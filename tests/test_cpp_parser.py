
from pathlib import Path

from core.cpp.cpp_parser import SofaCppParser
from config.settings import RAW_CODE_DIR


def find_cg_header():
    """Locate the downloaded CGLinearSolver header."""
    files = list(
        (RAW_CODE_DIR / "CGLinearSolver").glob(
            "*/Sofa/**/CGLinearSolver.h"
        )
    )

    assert files, "CGLinearSolver.h introuvable"

    return files[0]


def test_cpp_parser_initialization():
    """Check that Tree-sitter can parse a simple C++ class."""
    parser = SofaCppParser()

    tree, source = parser.parse_source(
        "class Test : public Parent {};"
    )

    assert tree.root_node.type == "translation_unit"
    assert not parser.has_syntax_errors(tree)


def test_cg_header_parsing():
    """Check parsing of the real SOFA header."""
    parser = SofaCppParser()

    file_path = find_cg_header()
    tree, source = parser.parse_file(file_path)

    assert tree.root_node.type == "translation_unit"
    assert b"CGLinearSolver" in source

    print(f"\n[FILE] {file_path.name}")
    print(f"[SYNTAX ERRORS] {parser.has_syntax_errors(tree)}")


def test_cg_field_structure():
    """Inspect how Tree-sitter represents C++ fields."""
    parser = SofaCppParser()

    tree, source = parser.parse_file(find_cg_header())

    fields = []

    def visit(node):
        if node.type == "field_declaration":
            code = parser.get_node_text(node, source)

            fields.append({
                "line": node.start_point.row + 1,
                "code": code,
                "node": str(node)
            })

        for child in node.named_children:
            visit(child)

    visit(tree.root_node)

    assert fields, "Aucun attribut C++ détecté"

    print("\n[FIELD DECLARATIONS]")

    for field in fields:
        print(f"\n[LINE {field['line']}]")
        print(field["code"][:300])
        print(f"[CST] {field['node']}")

    assert any(
        "d_warmStart" in field["code"]
        for field in fields
    )

    assert any(
        "d_smallDenominatorThreshold" in field["code"]
        for field in fields
    )

def test_cg_syntax_errors_diagnostic():
    """Locate Tree-sitter syntax errors in CGLinearSolver.h."""
    parser = SofaCppParser()
    tree, source = parser.parse_file(find_cg_header())

    errors = []

    def visit(node):
        if node.type == "ERROR" or node.is_missing:
            errors.append(node)

        for child in node.children:
            visit(child)

    visit(tree.root_node)

    print("\n[TREE-SITTER DIAGNOSTIC]")

    if not errors:
        print("No syntax errors found.")

    for node in errors:
        print(f"\n[ERROR] Line {node.start_point.row + 1}")
        print(f"[TYPE] {node.type}")
        print(f"[CODE] {parser.get_node_text(node, source)[:300]}")

    print(f"\n[TOTAL ERRORS] {len(errors)}")


def test_cg_constructor_structure():
    """Inspect the constructor syntax in CGLinearSolver.inl."""

    parser = SofaCppParser()

    files = list(
        (RAW_CODE_DIR / "CGLinearSolver").glob(
            "*/Sofa/**/CGLinearSolver.inl"
        )
    )

    assert files, "CGLinearSolver.inl introuvable"

    tree, source = parser.parse_file(files[0])

    constructors = []

    def visit(node):
        if node.type == "function_definition":
            declarator = node.child_by_field_name("declarator")

            if declarator is not None:
                signature = parser.get_node_text(
                    declarator, source
                )

                if "::CGLinearSolver(" in signature:
                    constructors.append(node)

                    print("\n[CONSTRUCTOR FOUND]")
                    print(f"[LINE] {node.start_point.row + 1}")
                    print(f"[SIGNATURE] {signature}")
                    print(f"[CST] {node}")

                    print("\n[CHILD NODES]")
                    for child in node.named_children:
                        print(
                            child.type,
                            "->",
                            parser.get_node_text(child, source)[:250]
                        )

        for child in node.named_children:
            visit(child)

    visit(tree.root_node)

    assert constructors, "Constructeur CGLinearSolver non détecté"



def test_cg_method_definitions():
    """Inspect C++ method definitions in CGLinearSolver files."""

    parser = SofaCppParser()

    component_dir = RAW_CODE_DIR / "CGLinearSolver"

    # Search downloaded .cpp and .inl files.
    files = list(component_dir.glob("*/Sofa/**/CGLinearSolver.cpp"))
    files += list(component_dir.glob("*/Sofa/**/CGLinearSolver.inl"))

    assert files, "No CGLinearSolver implementation files found"

    definitions = []

    def visit(node, source, filename):

        if node.type == "function_definition":

            declarator = node.child_by_field_name("declarator")
            body = node.child_by_field_name("body")

            if declarator is not None and body is not None:

                signature = parser.get_node_text(
                    declarator, source
                )

                # We focus on CGLinearSolver member functions.
                if "::" in signature and "CGLinearSolver" in signature:

                    definition = {
                        "file": filename,
                        "signature": signature,
                        "start_line": node.start_point.row + 1,
                        "end_line": node.end_point.row + 1,
                        "body": parser.get_node_text(body, source)
                    }

                    definitions.append(definition)

                    print(f"\n[METHOD DEFINITION] {signature}")
                    print(f"[FILE] {filename}")
                    print(
                        f"[LINES] {definition['start_line']}"
                        f"-{definition['end_line']}"
                    )
                    print(
                        f"[BODY PREVIEW] "
                        f"{definition['body'][:250]}"
                    )

        for child in node.named_children:
            visit(child, source, filename)

    for file_path in files:

        tree, source = parser.parse_file(file_path)

        print(f"\n[ANALYZING] {file_path.name}")

        visit(tree.root_node, source, file_path.name)

    assert definitions, "No CGLinearSolver methods detected"

    assert any(
        "::solve(" in item["signature"]
        for item in definitions
    ), "CGLinearSolver::solve() not found"

def test_reinit_ast():
    parser = SofaCppParser()

    code = """
    class CGLinearSolver {
    public:
        void reinit() override {};
    };
    """

    tree, source = parser.parse_source(code)

    print("\n[TREE-SITTER AST]")
    print(tree.root_node)

    print("\n[FUNCTION NODES]")

    def visit(node):
        if node.type in ("function_definition", "field_declaration"):
            print(
                node.type,
                parser.get_node_text(node, source)
            )

        for child in node.named_children:
            visit(child)

    visit(tree.root_node)