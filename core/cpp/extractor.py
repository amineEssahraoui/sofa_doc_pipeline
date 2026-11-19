
import json
import re
from pathlib import Path

from config.settings import RAW_CODE_DIR, INTERMEDIATE_DIR

from core.cpp.cpp_parser import SofaCppParser

class SofaExtractor:

    def __init__(self):
        self.include_pattern = re.compile(
            r'^\s*#\s*include\s*[<"]([^>"]+)[>"]',
            re.MULTILINE
        )
        self.cpp_parser = SofaCppParser()

    @staticmethod
    def unwrap_function_declarator(declarator):
        """Find a function declarator wrapped by pointer/reference nodes."""
        current = declarator

        while current is not None:
            if current.type == "function_declarator":
                return current

            if current.type not in (
                "pointer_declarator",
                "reference_declarator",
                "parenthesized_declarator",
            ):
                return None

            current = current.child_by_field_name("declarator")

        return None
    
    def extract_includes(self, source_code):
        """Extract active-looking #include directives."""
        return self.include_pattern.findall(source_code)

    @staticmethod
    def classify_attribute(field_type):
        normalized = field_type.strip()

        if re.match(r"^(?:(?:\w+)::)*Data\s*<", normalized):
            return "SOFA_Data"

        if re.match(r"^(?:(?:\w+)::)*(?:SingleLink|MultiLink)\s*<", normalized):
            return "SOFA_Link"

        if re.search(
            r"(?:^|::)DeprecatedData$",
            normalized
        ):
            return "SOFA_DeprecatedData"

        return "internal"
    
    def extract_inheritance(self, source_code):
        """Detect C++ class declarations and their direct base classes."""
        tree, source_bytes = self.cpp_parser.parse_source(source_code)

        classes = []

        def visit(node):
            if node.type == "class_specifier":
                name_node = node.child_by_field_name("name")
                body_node = node.child_by_field_name("body")

                if (
                    name_node is not None
                    and body_node is not None
                    and body_node.type == "field_declaration_list"
                ):
                    class_name = source_bytes[
                        name_node.start_byte:name_node.end_byte
                    ].decode("utf-8")

                    parents = []

                    for child in node.children:
                        if child.type == "base_class_clause":
                            for base in child.named_children:
                                if base.type == "access_specifier":
                                    continue

                                parent = source_bytes[
                                    base.start_byte:base.end_byte
                                ].decode("utf-8").strip()

                                if parent and parent != "virtual":
                                    parents.append(parent)

                    classes.append({
                        "class": class_name,
                        "parents": parents,
                        "line": node.start_point.row + 1
                    })

            for child in node.named_children:
                visit(child)

        visit(tree.root_node)
        return classes


    def extract_attributes(self, source_code):
        """Extract C++ attributes with visibility, owner and initial value."""

        tree, source_bytes = self.cpp_parser.parse_source(source_code)
        attributes = []

        def node_text(node):
            return self.cpp_parser.get_node_text(node, source_bytes)

        def visit(node):

            if node.type in ("class_specifier", "struct_specifier"):

                name_node = node.child_by_field_name("name")
                body_node = node.child_by_field_name("body")

                if name_node is not None and body_node is not None:

                    class_name = node_text(name_node)

                    # C++ defaults: class=private, struct=public
                    visibility = (
                        "private"
                        if node.type == "class_specifier"
                        else "public"
                    )

                    for child in body_node.named_children:

                        # Track visibility changes.
                        if child.type == "access_specifier":
                            visibility = node_text(child).strip()
                            continue

                        if child.type == "field_declaration":

                            type_node = child.child_by_field_name("type")
                            declarator = child.child_by_field_name(
                                "declarator"
                            )

                            if type_node is None or declarator is None:
                                continue

                            # First version: simple member variables.
                            # Exclude method declarations.
                            if declarator.type != "field_identifier":
                                continue

                            field_type = node_text(type_node)
                            field_name = node_text(declarator)

                            initial_node = child.child_by_field_name(
                                "default_value"
                            )

                            initial_value = (
                                node_text(initial_node)
                                if initial_node is not None
                                else None
                            )

                            attributes.append({
                                "name": field_name,
                                "type": field_type,
                                "category": self.classify_attribute(field_type),
                                "owner_class": class_name,
                                "visibility": visibility,
                                "initial_value": initial_value,
                                "line": child.start_point.row + 1
                            })

            # Continue searching for other classes.
            for child in node.named_children:
                visit(child)

        visit(tree.root_node)

        return attributes

    
    def extract_method_declarations(self, source_code):
        """Extract C++ method declarations from class bodies."""

        tree, source_bytes = self.cpp_parser.parse_source(source_code)
        methods = []

        def visit(node):

            if node.type == "class_specifier":

                body_node = node.child_by_field_name("body")

                if body_node is not None:

                    for child in body_node.named_children:

                        if child.type != "field_declaration":
                            continue

                        type_node = child.child_by_field_name("type")
                        declarator = child.child_by_field_name(
                            "declarator"
                        )

                        function_declarator = self.unwrap_function_declarator(declarator)
                        if function_declarator is None:
                            continue

                        name_node = function_declarator.child_by_field_name(
                            "declarator"
                        )

                        if name_node is None:
                            continue

                        method_name = self.cpp_parser.get_node_text(
                            name_node, source_bytes
                        )

                        return_type = (
                            self.cpp_parser.get_node_text(
                                type_node, source_bytes
                            )
                            if type_node is not None
                            else None
                        )

                        if return_type is not None:
                            prefix = source_bytes[
                                child.start_byte:name_node.start_byte
                            ].decode("utf-8").strip()

                            if declarator.type in (
                                "pointer_declarator",
                                "reference_declarator",
                            ):
                                return_type = re.sub(
                                    r"^(?:(?:virtual|static|inline|constexpr)\s+)*",
                                    "",
                                    prefix
                                ).strip()

                        signature = self.cpp_parser.get_node_text(
                            child, source_bytes
                        )

                        methods.append({
                            "name": method_name,
                            "return_type": return_type,
                            "signature": signature,
                            "line": child.start_point.row + 1,
                            "kind": "declaration"
                        })

            for child in node.named_children:
                visit(child)

        visit(tree.root_node)

        return methods

    
    def extract_constructors(self, source_code):
        """Extract constructor definitions and their initializers."""

        tree, source_bytes = self.cpp_parser.parse_source(source_code)
        constructors = []

        def get_text(node):
            return self.cpp_parser.get_node_text(node, source_bytes)

        def visit(node):

            if node.type == "function_definition":

                declarator = node.child_by_field_name("declarator")

                if declarator is not None:
                    name_node = declarator.child_by_field_name(
                        "declarator"
                    )

                    if name_node is not None:
                        full_name = get_text(name_node)

                        # For qualified constructor definitions:
                        # Class<T>::Class()
                        parts = full_name.split("::")

                        if len(parts) >= 2:
                            class_name = parts[-1]
                            owner = parts[-2].split("<")[0]

                            if class_name == owner:

                                signature = get_text(declarator)
                                initializers = []
                                initializer_list = None

                                for child in node.named_children:
                                    if child.type == "field_initializer_list":
                                        initializer_list = child
                                        break

                                if initializer_list is not None:
                                    for item in initializer_list.named_children:

                                        if item.type != "field_initializer":
                                            continue

                                        children = item.named_children

                                        if not children:
                                            continue

                                        attribute_name = get_text(children[0])

                                        expression = (
                                            get_text(children[1])
                                            if len(children) > 1
                                            else None
                                        )

                                        initializers.append({
                                            "attribute": attribute_name,
                                            "expression": expression,
                                            "line": item.start_point.row + 1
                                        })

                                body_node = node.child_by_field_name("body")

                                body = (
                                    get_text(body_node)
                                    if body_node is not None
                                    else None
                                )

                                constructors.append({
                                    "class": class_name,
                                    "signature": signature,
                                    "line": node.start_point.row + 1,
                                    "initializers": initializers,
                                    "body": body
                                })

            for child in node.named_children:
                visit(child)

        visit(tree.root_node)

        return constructors


    def extract_constructor_metadata(self, source_code):
        """Extract SOFA initData parameters and setRequired calls."""

        tree, source_bytes = self.cpp_parser.parse_source(source_code)
        results = []

        def text(node):
            return self.cpp_parser.get_node_text(node, source_bytes)

        def visit(node):
            if node.type == "function_definition":
                declarator = node.child_by_field_name("declarator")

                if declarator is not None:
                    name_node = declarator.child_by_field_name("declarator")

                    if name_node is not None:
                        full_name = text(name_node)
                        parts = full_name.split("::")

                        # Detect Class<T>::Class constructors.
                        if len(parts) >= 2:
                            owner = parts[-2].split("<")[0]
                            name = parts[-1]

                            if owner == name:
                                analyze_constructor(node, full_name)

            for child in node.named_children:
                visit(child)

        def analyze_constructor(node, full_name):
            parameters = []
            required_fields = []
            deprecated_fields = []
            link_fields = []

            # 1. Inspect constructor initializer list.
            for child in node.named_children:
                if child.type != "field_initializer_list":
                    continue

                for item in child.named_children:
                    if item.type != "field_initializer":
                        continue

                    parts = item.named_children
                    if len(parts) < 2:
                        continue

                    attribute = text(parts[0])
                    argument_wrapper = parts[1]

                    if argument_wrapper.type == "argument_list":
                        args_nodes = argument_wrapper.named_children
                        args = [text(arg) for arg in args_nodes]

                        if (
                            len(args) == 5
                            and args[0] == "this"
                            and all(
                                arg.type == "string_literal"
                                for arg in args_nodes[1:]
                            )
                            and re.fullmatch(r"v\d+\.\d+", args[1].strip('"'))
                            and re.fullmatch(r"v\d+\.\d+", args[2].strip('"'))
                            ):
                                deprecated_fields.append({
                                    "attribute": attribute,
                                    "deprecated_since": args[1].strip('"'),
                                    "removal_version": args[2].strip('"'),
                                    "sofa_name": args[3].strip('"'),
                                    "replacement_message": args[4].strip('"'),
                                    "line": item.start_point.row + 1,
                                    "source_expression": text(item)
                                })

                    for call in argument_wrapper.named_children:
                        if call.type != "call_expression":
                            continue

                        function = call.child_by_field_name("function")
                        args_node = call.child_by_field_name("arguments")

                        if function is None or args_node is None:
                            continue

                        if text(function).split("::")[-1] == "initLink":
                            args = [
                                text(arg)
                                for arg in args_node.named_children
                            ]
                            if len(args) >= 2:
                                link_fields.append({
                                    "attribute": attribute,
                                    "sofa_name": args[0].strip('"'),
                                    "description": args[1].strip('"'),
                                    "line": item.start_point.row + 1,
                                    "source_expression": text(item)
                                })

                            continue

                        if text(function).split("::")[-1] != "initData":
                            continue

                        args = [
                            text(arg) for arg in args_node.named_children
                        ]

                        if len(args) == 4:
                            default_expression = args[1]
                            sofa_name = args[2].strip('"')
                            description = args[3].strip('"')

                        elif len(args) == 3:
                            default_expression = None
                            sofa_name = args[1].strip('"')
                            description = args[2].strip('"')

                        else:
                            continue

                        parameters.append({
                            "attribute": attribute,
                            "default_expression": default_expression,
                            "sofa_name": sofa_name,
                            "description": description,
                            "line": item.start_point.row + 1,
                            "source_expression": text(item)
                        })

            # 2. Inspect setRequired(...) calls in the body.
            body = node.child_by_field_name("body")

            def inspect_calls(current):
                if current.type == "call_expression":
                    function = current.child_by_field_name("function")
                    args_node = current.child_by_field_name("arguments")

                    if (
                        function is not None
                        and function.type == "field_expression"
                        and args_node is not None
                    ):
                        field = function.child_by_field_name("field")
                        receiver = function.child_by_field_name("argument")

                        if (
                            field is not None
                            and receiver is not None
                            and text(field) == "setRequired"
                        ):
                            args = args_node.named_children

                            if len(args) == 1:
                                required_fields.append({
                                    "attribute": text(receiver),
                                    "required_expression": text(args[0]),
                                    "line": current.start_point.row + 1
                                })

                for child in current.named_children:
                    inspect_calls(child)

            if body is not None:
                inspect_calls(body)

            results.append({
                "constructor": full_name,
                "sofa_parameters": parameters,
                "required_fields": required_fields,
                "deprecated_fields": deprecated_fields,
                "link_fields": link_fields
            })

        visit(tree.root_node)
        return results


    def extract_method_definitions(self, source_code):
        """Extract out-of-class C++ method definitions."""

        tree, source_bytes = self.cpp_parser.parse_source(source_code)
        definitions = []

        def get_text(node):
            return self.cpp_parser.get_node_text(node, source_bytes)

        def visit(node):
            if node.type == "function_definition":
                declarator = node.child_by_field_name("declarator")
                body_node = node.child_by_field_name("body")

                if (
                    declarator is not None
                    and body_node is not None
                    and declarator.type == "function_declarator"
                ):
                    name_node = declarator.child_by_field_name(
                        "declarator"
                    )

                    if (
                        name_node is not None
                        and name_node.type == "qualified_identifier"
                    ):
                        scope_node = name_node.child_by_field_name("scope")
                        method_node = name_node.child_by_field_name("name")

                        if scope_node is not None and method_node is not None:
                            owner = get_text(scope_node)
                            name = get_text(method_node)

                            owner_base = owner.split("::")[-1].split("<")[0]

                            # Constructors are handled separately.
                            if name != owner_base:
                                definitions.append({
                                    "name": name,
                                    "owner": owner,
                                    "signature": get_text(declarator),
                                    "body": get_text(body_node),
                                    "start_line": node.start_point.row + 1,
                                    "end_line": node.end_point.row + 1,
                                    "kind": "definition"
                                })

            for child in node.named_children:
                visit(child)

        visit(tree.root_node)
        return definitions



    def extract_method_calls(self, source_code):
        """Extract calls from C++ function bodies using Tree-sitter."""

        tree, source_bytes = self.cpp_parser.parse_source(source_code)
        results = []

        def get_text(node):
            return self.cpp_parser.get_node_text(node, source_bytes)

        def get_function_name(declarator):
            if declarator is None:
                return None

            if declarator.type == "function_declarator":
                name_node = declarator.child_by_field_name("declarator")

                if name_node is not None:
                    return get_text(name_node)

            return get_text(declarator)

        def collect_calls(node, calls):
            if node.type == "call_expression":
                function = node.child_by_field_name("function")
                arguments = node.child_by_field_name("arguments")

                if function is not None:
                    calls.append({
                        "expression": get_text(function),
                        "arguments": (
                            get_text(arguments)
                            if arguments is not None
                            else None
                        ),
                        "line": node.start_point.row + 1
                    })

            for child in node.named_children:
                collect_calls(child, calls)

        def visit(node):
            if node.type == "function_definition":
                declarator = node.child_by_field_name("declarator")
                body = node.child_by_field_name("body")

                if declarator is not None and body is not None:
                    calls = []
                    collect_calls(body, calls)

                    results.append({
                        "function": get_function_name(declarator),
                        "start_line": node.start_point.row + 1,
                        "end_line": node.end_point.row + 1,
                        "calls": calls
                    })

            for child in node.named_children:
                visit(child)

        visit(tree.root_node)
        return results


    
    def extract_inline_method_definitions(self, source_code):
        """Extract methods defined directly inside C++ classes."""

        tree, source_bytes = self.cpp_parser.parse_source(source_code)
        definitions = []

        def get_text(node):
            return self.cpp_parser.get_node_text(node, source_bytes)

        def visit(node, current_class=None):

            if node.type in ("class_specifier", "struct_specifier"):
                name_node = node.child_by_field_name("name")

                if name_node is not None:
                    current_class = get_text(name_node)

            # Method defined inside a class with a function body.
            if node.type == "function_definition" and current_class:
                declarator = node.child_by_field_name("declarator")
                body_node = node.child_by_field_name("body")

                function_declarator = self.unwrap_function_declarator(declarator)
                if function_declarator is not None and body_node is not None:
                    definitions.append({
                        "owner": current_class,
                        "signature": get_text(declarator),
                        "body": get_text(body_node),
                        "start_line": node.start_point.row + 1,
                        "end_line": node.end_point.row + 1,
                        "kind": "inline_definition"
                    })

            # Tree-sitter may represent an inline empty body as an
            # initializer_list attached to a field_declaration.
            if node.type == "field_declaration" and current_class:

                declarator = node.child_by_field_name("declarator")
                default_value = node.child_by_field_name("default_value")

                if (
                    declarator is not None
                    and declarator.type == "function_declarator"
                    and default_value is not None
                    and default_value.type == "initializer_list"
                ):
                    definitions.append({
                        "owner": current_class,
                        "signature": get_text(declarator),
                        "body": get_text(default_value),
                        "start_line": node.start_point.row + 1,
                        "end_line": node.end_point.row + 1,
                        "kind": "inline_definition"
                    })

            for child in node.named_children:
                visit(child, current_class)

        visit(tree.root_node)
        return definitions



    def resolve_parent_paths(self, classes, includes):
        """Match direct C++ parent classes to included header files."""
        resolved = []

        for cls in classes:
            for parent in cls["parents"]:

                # Remove template arguments, preserving the class name.
                parent_without_templates = parent.split("<", 1)[0]
                parent_name = parent_without_templates.split("::")[-1].strip()

                candidates = list(dict.fromkeys(
                    path for path in includes
                    if Path(path).name == f"{parent_name}.h"
                ))

                if len(candidates) == 1:
                    status = "resolved"
                    header_path = candidates[0]
                elif len(candidates) > 1:
                    status = "ambiguous"
                    header_path = None
                else:
                    status = "unresolved"
                    header_path = None

                resolved.append({
                    "class": cls["class"],
                    "parent": parent,
                    "parent_name": parent_name,
                    "status": status,
                    "header_path": header_path,
                    "candidates": candidates
                })

        return resolved


    def analyze_component(self, component_name):
        component_dir = RAW_CODE_DIR / component_name

        manifests = list(component_dir.glob("*/manifest.json"))

        if not manifests:
            raise FileNotFoundError(
                f"No downloaded sources for {component_name}"
            )

        # For this first test, choose the latest saved manifest.
        manifest_path = max(
            manifests,
            key=lambda p: p.stat().st_mtime
        )

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        source_root = manifest_path.parent

        result = {
            "component": component_name,
            "resolved_commit": manifest["resolved_commit"],
            "files": []
        }

        for file_info in manifest["files"]:
            source_path = source_root / file_info["local_path"]

            source_code = source_path.read_text(
                encoding="utf-8",
                errors="replace"
            )

            includes = self.extract_includes(source_code)
            classes = self.extract_inheritance(source_code)
            attributes = self.extract_attributes(source_code)
            methods = self.extract_method_declarations(source_code)
            constructors = self.extract_constructors(source_code)
            constructor_metadata = self.extract_constructor_metadata(source_code)
            method_definitions = self.extract_method_definitions(source_code)
            inline_definitions = self.extract_inline_method_definitions(source_code)
            method_calls = self.extract_method_calls(source_code)

            result["files"].append({
                "file": file_info["repository_path"],
                "includes": includes,
                "classes": classes,
                "attributes": attributes,
                "methods": methods, 
                "constructors": constructors,
                "constructor_metadata": constructor_metadata,
                "method_definitions": method_definitions,
                "inline_definitions": inline_definitions,
                "method_calls": method_calls,
            })

            print(f"\n[FILE] {source_path.name}")

            for include in includes:
                print(f"  [INCLUDE] {include}")

            for cls in classes:
                print(f"  [CLASS] {cls['class']}")
                for parent in cls["parents"]:
                    print(f"    [PARENT] {parent}")

            for attribute in attributes:
                print(
                    f"  [ATTRIBUTE] {attribute['name']} "
                    f"({attribute['type']}) "
                    f"- {attribute['category']} "
                    f"- {attribute['visibility']} "
                    f"- Initial: {attribute['initial_value']} "
                    f"- Owner: {attribute['owner_class']} "
                    f"- Line {attribute['line']}"
                )

            for method in methods:
                print(
                    f"  [METHOD] {method['name']} "
                    f"({method['return_type']}) "
                    f"- Line {method['line']}"
                )
            for constructor in constructors:
                print(
                    f"  [CONSTRUCTOR] {constructor['signature']} "
                    f"- Line {constructor['line']}"
                )

                for initializer in constructor["initializers"]:
                    print(
                        f"    [INIT] {initializer['attribute']} "
                        f"= {initializer['expression']}"
                    )

            for metadata in constructor_metadata:
                for param in metadata["sofa_parameters"]:
                    print(
                        f"  [SOFA PARAM] {param['attribute']} "
                        f"- Default: {param['default_expression']} "
                        f"- Name: {param['sofa_name']}"
                    )
            
                for field in metadata["required_fields"]:
                    print(
                        f"  [REQUIRED] {field['attribute']} "
                        f"= {field['required_expression']}"
                    )
            for method in method_definitions:
                print(
                    f"  [METHOD DEFINITION] {method['owner']}::{method['name']}"
                    f" - Lines {method['start_line']}-{method['end_line']}"
                )

            for method in inline_definitions:
                print(
                    f"  [INLINE DEFINITION] {method['owner']}::"
                    f"{method['signature']} "
                    f"- Lines {method['start_line']}-{method['end_line']}"
                )

            for function in method_calls:
                if function["function"] and function["function"].endswith("::solve"):
                    print(
                        f"  [CALL ANALYSIS] {function['function']}"
                    )

                    for call in function["calls"]:
                        print(
                            f"    [CALL] {call['expression']}"
                            f" - Line {call['line']}"
                        )
                    
        all_classes = []
        all_includes = []

        for file_result in result["files"]:
            all_classes.extend(file_result["classes"])
            all_includes.extend(file_result["includes"])

        parent_dependencies = self.resolve_parent_paths(
            all_classes,
            all_includes
        )

        result["parent_dependencies"] = parent_dependencies

        print("\n[PARENT DEPENDENCIES]")

        for dependency in parent_dependencies:
            print(
                f"  [{dependency['status'].upper()}] "
                f"{dependency['parent_name']} -> "
                f"{dependency['header_path']}"
            )


        output_dir = INTERMEDIATE_DIR / component_name
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "includes.json"

        output_path.write_text(
            json.dumps(result, indent=2),
            encoding="utf-8"
        )

        print(f"\n[SUCCESS] Results saved: {output_path}")

        return result


if __name__ == "__main__":
    extractor = SofaExtractor()
    extractor.analyze_component("CGLinearSolver")
