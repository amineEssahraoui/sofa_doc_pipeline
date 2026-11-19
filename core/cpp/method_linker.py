
import json
import re
import sys

from pathlib import Path

from config.settings import INTERMEDIATE_DIR

def owner_base(owner):
    """CGLinearSolver<TMatrix,TVector> -> CGLinearSolver"""
    return owner.split("<", 1)[0].split("::")[-1]


def method_name(signature):
    """Extract the method name from an inline signature."""
    match = re.search(r"([A-Za-z_]\w*)\s*\(", signature)
    return match.group(1) if match else None


def parameter_types(signature):
    """Normalize parameter types for method matching."""

    start = signature.find("(")
    if start == -1:
        return None

    depth = 0
    end = None

    for i in range(start, len(signature)):
        if signature[i] == "(":
            depth += 1
        elif signature[i] == ")":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end is None:
        return None

    content = signature[start + 1:end].strip()

    if not content or content == "void":
        return []

    # Split parameters without splitting template arguments.
    parameters = []
    current = []
    template_depth = 0

    for char in content:
        if char == "<":
            template_depth += 1
        elif char == ">":
            template_depth -= 1

        if char == "," and template_depth == 0:
            parameters.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    parameters.append("".join(current).strip())

    normalized = []

    for parameter in parameters:

        # Remove comments used instead of parameter names.
        parameter = re.sub(r"/\*.*?\*/", "", parameter).strip()

        # Remove parameter names, preserving unnamed const-qualified types.
        unnamed_const_type = re.fullmatch(
            r"const\s+[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*",
            parameter,
        )

        if not unnamed_const_type and (
            re.search(r"\s+[A-Za-z_]\w+$", parameter)
            or re.search(r"[*&]\s*[A-Za-z_]\w+$", parameter)
        ):
            parameter = re.sub(
                r"[A-Za-z_]\w+$", "", parameter
            ).strip()

        # Top-level const does not affect by-value parameter matching.
        if re.fullmatch(
            r"const\s+[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*",
            parameter,
        ):
            parameter = re.sub(r"^const\s+", "", parameter)

        # Ignore whitespace differences.
        parameter = re.sub(r"\s+", "", parameter)

        normalized.append(parameter)

    return normalized


def build_method_links(data):
    """Link declarations to compatible definitions."""

    declarations = []
    definitions = []

    for file_data in data["files"]:
        file_path = file_data["file"]

        for method in file_data.get("methods", []):
            declarations.append({
                **method,
                "file": file_path
            })

        for method in file_data.get("method_definitions", []):
            definitions.append({
                **method,
                "file": file_path,
                "name": method["name"]
            })

        for method in file_data.get("inline_definitions", []):
            definitions.append({
                **method,
                "file": file_path,
                "name": method_name(method["signature"])
            })

    links = []
    component = data["component"]

    for declaration in declarations:

        name = declaration["name"]
        expected_types = parameter_types(declaration["signature"])

        implementations = []

        for definition in definitions:

            if definition["name"] != name:
                continue

            if owner_base(definition["owner"]) != component:
                continue

            actual_types = parameter_types(definition["signature"])

            # Do not confuse overloads with different parameters.
            if expected_types != actual_types:
                continue

            implementations.append({
                "file": definition["file"],
                "start_line": definition["start_line"],
                "end_line": definition["end_line"],
                "owner": definition["owner"],
                "kind": definition["kind"],
                "signature": definition["signature"]
            })

        links.append({
            "method": name,
            "declaration": {
                "file": declaration["file"],
                "line": declaration["line"],
                "signature": declaration["signature"]
            },
            "implementations": implementations,
            "status": (
                "matched" if implementations else "unresolved"
            )
        })

    # Include inline methods that have no separate declaration.
    for definition in definitions:

        if definition["kind"] != "inline_definition":
            continue

        if owner_base(definition["owner"]) != component:
            continue

        name = definition["name"]

        if not name:
            continue

        actual_types = parameter_types(definition["signature"])

        already_linked = any(
            link["method"] == name
            and parameter_types(link["declaration"]["signature"]) == actual_types
            for link in links
        )

        if already_linked:
            continue

        links.append({
            "method": name,
            "declaration": None,
            "implementations": [{
                "file": definition["file"],
                "start_line": definition["start_line"],
                "end_line": definition["end_line"],
                "owner": definition["owner"],
                "kind": "inline_definition",
                "signature": definition["signature"]
            }],
            "status": "matched"
        })

    return {
        "component": component,
        "resolved_commit": data["resolved_commit"],
        "method_links": links
    }


def main():

    components = [
        "CGLinearSolver",
        "PCGLinearSolver",
        "BarycentricMapping",
        "NewmarkIntegrationScheme",
        "BDFIntegrationScheme",
        "NewtonRaphsonSolver",
    ]

    if len(sys.argv) > 1:
        components = [sys.argv[1]]

    for component in components:
        print(f"\n{'=' * 50}")
        print(f"[COMPONENT] {component}")
        print(f"{'=' * 50}")

        path = (
            Path(INTERMEDIATE_DIR)
            / component
            / "includes.json"
        )

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            result = build_method_links(data)

            for link in result["method_links"]:
                print(f"\n[METHOD] {link['method']}")
                print(f"  [STATUS] {link['status']}")

                for impl in link["implementations"]:
                    filename = Path(impl["file"]).name

                    print(
                        f"  [IMPLEMENTATION] {filename} "
                        f"- Lines {impl['start_line']}-"
                        f"{impl['end_line']}"
                    )

            output_path = path.parent / "method_links.json"

            with output_path.open("w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"\n[SUCCESS] Saved: {output_path}")

        except Exception as e:
            print(
                f"\n[ERROR] {component}: "
                f"{type(e).__name__}: {e}"
            )


if __name__ == "__main__":
    main()
