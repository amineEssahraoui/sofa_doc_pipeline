import json
import hashlib
from pathlib import Path

import tree_sitter_cpp
from tree_sitter import Language, Parser

from config.settings import INTERMEDIATE_DIR, RAW_CODE_DIR

def extract_code_snippets(component, selected_items):
    """Extract exact C++ snippets with source and commit evidence."""

    folder = Path(INTERMEDIATE_DIR) / component

    links_data = json.loads(
        (folder / "method_links.json").read_text(encoding="utf-8")
    )

    sha = links_data["resolved_commit"]

    manifest_path = (
        Path(RAW_CODE_DIR) / component / sha / "manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if manifest["resolved_commit"] != sha:
        raise ValueError("Commit mismatch between manifest and method links")

    source_root = manifest_path.parent
    files_by_repository_path = {
        item["repository_path"]: item
        for item in manifest["files"]
    }

    selected_keys = {
        (
            item["file"],
            item["start_line"],
            item["end_line"],
            item["signature"]
        )
        for item in selected_items
    }

    snippets = []

    for link in links_data["method_links"]:

        for impl in link["implementations"]:

            key = (
                impl["file"],
                impl["start_line"],
                impl["end_line"],
                impl["signature"]
            )

            if key not in selected_keys:
                continue

            repo_path = impl["file"]
            file_info = files_by_repository_path.get(repo_path)

            if file_info is None:
                raise FileNotFoundError(
                    f"Source not found in manifest: {repo_path}"
                )

            source_path = (
                source_root / file_info["local_path"]
            ).resolve()

            if not source_path.is_relative_to(source_root.resolve()):
                raise ValueError("Source path outside component directory")

            raw_content = source_path.read_bytes()

            actual_hash = hashlib.sha256(raw_content).hexdigest()

            if actual_hash != file_info["sha256"]:
                raise ValueError(
                    f"Source checksum mismatch: {repo_path}"
                )

            lines = raw_content.decode(
                "utf-8", errors="replace"
            ).splitlines(keepends=True)

            start = impl["start_line"]
            end = impl["end_line"]

            if not (1 <= start <= end <= len(lines)):
                raise ValueError(
                    f"Invalid source line range: {repo_path}:{start}-{end}"
                )

            code = "".join(lines[start - 1:end])

            snippets.append({
                "component": component,
                "method": link["method"],
                "source_file": repo_path,
                "resolved_commit": sha,
                "start_line": start,
                "end_line": end,
                "kind": impl["kind"],
                "source_sha256": actual_hash,
                "code": code,
                "signature": impl["signature"],
                "declaration": link["declaration"],
            })

    output = folder / "code_snippets.json"

    output.write_text(
        json.dumps(snippets, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"[SNIPPETS] {len(snippets)} extracted")
    print(f"[SAVED] {output}")

    return snippets

def select_methods_for_snippets(links_data, max_lines=80):
    """Classify each C++ implementation independently."""

    selected = {
        "short": [],
        "long": []
    }

    for link in links_data["method_links"]:
        if link["status"] != "matched":
            continue

        for impl in link["implementations"]:
            length = impl["end_line"] - impl["start_line"] + 1

            item = {
                "method": link["method"],
                "declaration": link["declaration"],
                "signature": impl["signature"],
                "owner": impl["owner"],
                "file": impl["file"],
                "start_line": impl["start_line"],
                "end_line": impl["end_line"],
                "kind": impl["kind"],
                "length": length
            }

            category = "short" if length <= max_lines else "long"
            selected[category].append(item)

    return selected

def inspect_cpp_ast(snippet):
    """Inspect the C++ syntax tree of an extracted method."""

    parser = Parser(Language(tree_sitter_cpp.language()))

    code = snippet["code"].encode("utf-8")
    tree = parser.parse(code)

    root = tree.root_node

    print("[AST] Root:", root.type)
    print("[AST] Has errors:", root.has_error)

    print("\n[AST] Top-level nodes:")
    for node in root.named_children:
        start_line = snippet["start_line"] + node.start_point.row
        end_line = snippet["start_line"] + node.end_point.row

        print(
            f"  {node.type}: "
            f"lines {start_line}-{end_line}"
        )

    return root

def inspect_method_blocks(snippet):
    """Inspect top-level statements inside a C++ method."""

    parser = Parser(Language(tree_sitter_cpp.language()))
    tree = parser.parse(snippet["code"].encode("utf-8"))

    if tree.root_node.has_error:
        raise ValueError("Invalid C++ syntax tree")

    function = next(
        (
            node for node in tree.root_node.named_children
            if node.type == "function_definition"
        ),
        None
    )

    if function is None:
        raise ValueError("No C++ function definition found")

    body = function.child_by_field_name("body")

    if body is None or body.type != "compound_statement":
        raise ValueError("No compound function body found")

    print("\n[METHOD BODY]")
    print("Type:", body.type)

    print("\n[TOP-LEVEL STATEMENTS]")

    for index, node in enumerate(body.named_children, start=1):
        start_line = snippet["start_line"] + node.start_point.row
        end_line = snippet["start_line"] + node.end_point.row

        print(
            f"{index:02d}. {node.type:<28} "
            f"lines {start_line}-{end_line} "
            f"({end_line - start_line + 1} lines)"
        )

    return body

def inspect_large_ast_blocks(snippet, min_lines=80):
    """Inspect nested C++ AST nodes exceeding the line threshold."""

    parser = Parser(Language(tree_sitter_cpp.language()))
    tree = parser.parse(snippet["code"].encode("utf-8"))

    if tree.root_node.has_error:
        raise ValueError("Invalid C++ syntax tree")

    def walk(node, depth=0):
        start = snippet["start_line"] + node.start_point.row
        end = snippet["start_line"] + node.end_point.row
        length = end - start + 1

        if length <= min_lines:
            return

        if node.type in {
            "function_definition",
            "compound_statement",
            "if_statement",
            "for_statement",
            "while_statement",
            "do_statement",
            "switch_statement",
        }:
            print(
                f"{'  ' * depth}{node.type:<24} "
                f"{start}-{end} ({length} lines)"
            )

        for child in node.named_children:
            walk(child, depth + 1)

    walk(tree.root_node)

def inspect_loop_statements(snippet):
    """Inspect statements inside large C++ for loops."""

    parser = Parser(Language(tree_sitter_cpp.language()))
    tree = parser.parse(snippet["code"].encode("utf-8"))

    if tree.root_node.has_error:
        raise ValueError("Invalid C++ syntax tree")

    def walk(node):
        if node.type == "for_statement":
            start = snippet["start_line"] + node.start_point.row
            end = snippet["start_line"] + node.end_point.row
            length = end - start + 1

            if length > 80:
                print(f"\n[FOR LOOP] lines {start}-{end}")

                body = node.child_by_field_name("body")

                if body is None:
                    raise ValueError("For loop body not found")

                for index, child in enumerate(body.named_children, 1):
                    child_start = (
                        snippet["start_line"] + child.start_point.row
                    )
                    child_end = (
                        snippet["start_line"] + child.end_point.row
                    )

                    print(
                        f"{index:02d}. {child.type:<28} "
                        f"{child_start}-{child_end} "
                        f"({child_end - child_start + 1} lines)"
                    )

        for child in node.named_children:
            walk(child)

    walk(tree.root_node)


def split_long_method(snippet, max_lines=80):
    """
    Split a long C++ method at AST statement boundaries.

    Every original source line is preserved in exactly one chunk.
    """

    if max_lines < 1:
        raise ValueError("max_lines must be positive")

    original_code = snippet["code"]
    lines = original_code.splitlines(keepends=True)

    if not lines:
        raise ValueError("Empty C++ snippet")

    parser = Parser(Language(tree_sitter_cpp.language()))
    tree = parser.parse(original_code.encode("utf-8"))

    if tree.root_node.has_error:
        raise ValueError("Cannot split a C++ method with AST errors")

    total_lines = len(lines)
    boundaries = set()

    # Collect statement and declaration boundaries, including nested ones.
    def collect_boundaries(node):
        if (
            node.type.endswith("_statement")
            or node.type in {"declaration", "comment"}
        ):
            # Tree-sitter end positions are exclusive.
            end_line = (
                node.end_point.row
                if node.end_point.column == 0
                else node.end_point.row + 1
            )

            if 0 < end_line < total_lines:
                boundaries.add(end_line)

        for child in node.named_children:
            collect_boundaries(child)

    collect_boundaries(tree.root_node)

    sorted_boundaries = sorted(boundaries)
    chunks = []
    start = 0

    while start < total_lines:
        limit = min(start + max_lines, total_lines)

        # Prefer the farthest AST boundary within the limit.
        candidates = [
            boundary
            for boundary in sorted_boundaries
            if start < boundary <= limit
        ]

        if limit == total_lines:
            end = total_lines

        elif candidates:
            end = max(candidates)

        else:
            # No suitable boundary: preserve the next complete statement.
            future = [
                boundary
                for boundary in sorted_boundaries
                if boundary > start
            ]
            end = future[0] if future else total_lines

        chunk_code = "".join(lines[start:end])

        chunks.append({
            "chunk_index": len(chunks) + 1,
            "component": snippet["component"],
            "method": snippet["method"],
            "signature": snippet["signature"],
            "source_file": snippet["source_file"],
            "resolved_commit": snippet["resolved_commit"],
            "source_sha256": snippet["source_sha256"],
            "start_line": snippet["start_line"] + start,
            "end_line": snippet["start_line"] + end - 1,
            "line_count": end - start,
            "code": chunk_code,
        })

        start = end

    # Lossless reconstruction verification.
    reconstructed = "".join(chunk["code"] for chunk in chunks)

    if reconstructed != original_code:
        raise ValueError("AST splitting lost or modified source code")

    print(f"[AST SPLIT] {len(chunks)} chunks created")
    print(f"[VERIFIED] All {total_lines} original lines preserved")

    return chunks


def add_ast_context(snippet, chunks):
    """Attach intersecting C++ control-flow scopes to chunks."""

    parser = Parser(Language(tree_sitter_cpp.language()))
    tree = parser.parse(snippet["code"].encode("utf-8"))

    if tree.root_node.has_error:
        raise ValueError("Invalid C++ AST")

    control_types = {
        "if_statement",
        "for_statement",
        "while_statement",
        "do_statement",
        "switch_statement",
        "try_statement",
        "catch_clause",
    }

    scopes = []

    def walk(node, depth=0):
        if node.type in control_types:
            start = snippet["start_line"] + node.start_point.row
            end = (
                snippet["start_line"]
                + node.end_point.row
                - (1 if node.end_point.column == 0 else 0)
            )

            scopes.append({
                "type": node.type,
                "start_line": start,
                "end_line": end,
                "depth": depth,
            })

        for child in node.named_children:
            walk(child, depth + 1)

    walk(tree.root_node)

    for chunk in chunks:
        first = chunk["start_line"]
        last = chunk["end_line"]

        contexts = []

        for scope in scopes:
            # Scope intersects this chunk.
            if scope["start_line"] > last:
                continue
            if scope["end_line"] < first:
                continue

            contexts.append({
                **scope,
                "fully_contained": (
                    scope["start_line"] <= first
                    and last <= scope["end_line"]
                ),
            })

        chunk["ast_context"] = contexts

    return chunks



def add_active_scope_headers(snippet, chunks):
    """Add branch-aware control-flow context to C++ chunks."""

    source = snippet["code"].encode("utf-8")
    parser = Parser(Language(tree_sitter_cpp.language()))
    tree = parser.parse(source)

    if tree.root_node.has_error:
        raise ValueError("Invalid C++ AST")

    base_line = snippet["start_line"]
    scopes = []

    def line_range(node):
        start = base_line + node.start_point.row
        end = base_line + node.end_point.row

        if node.end_point.column == 0:
            end -= 1

        return start, end

    def walk(node):
        if node.type == "if_statement":
            consequence = node.child_by_field_name("consequence")
            alternative = node.child_by_field_name("alternative")

            if consequence is not None:
                start, end = line_range(node)

                condition_header = source[
                    node.start_byte:consequence.start_byte
                ].decode("utf-8").strip()

                scopes.append({
                    "type": "if_statement",
                    "start_line": start,
                    "end_line": end,
                    "condition_header": condition_header,
                    "alternative": (
                        line_range(alternative)
                        if alternative is not None
                        else None
                    ),
                })

        elif node.type in {
            "for_statement",
            "while_statement",
            "switch_statement",
        }:
            body = node.child_by_field_name("body")

            if body is not None:
                start, end = line_range(node)

                header = source[
                    node.start_byte:body.start_byte
                ].decode("utf-8").strip()

                scopes.append({
                    "type": node.type,
                    "start_line": start,
                    "end_line": end,
                    "header": header,
                })

        for child in node.named_children:
            walk(child)

    walk(tree.root_node)

    for chunk in chunks:
        first = chunk["start_line"]
        active = []

        for scope in scopes:
            if not (scope["start_line"] < first <= scope["end_line"]):
                continue

            entry = {
                "type": scope["type"],
                "start_line": scope["start_line"],
                "end_line": scope["end_line"],
            }

            if scope["type"] == "if_statement":
                alternative = scope["alternative"]

                in_else = (
                    alternative is not None
                    and alternative[0] <= first <= alternative[1]
                )

                entry["branch"] = "else" if in_else else "then"
                entry["condition_header"] = scope["condition_header"]
                entry["header"] = (
                    "else" if in_else
                    else scope["condition_header"]
                )
            else:
                entry["header"] = scope["header"]

            active.append(entry)

        chunk["active_scope_headers"] = active

    return chunks



def save_code_chunks(component, snippet, chunks):
    """Validate and save AST chunks without modifying original snippets."""

    if not chunks:
        raise ValueError("No chunks to save")

    original_code = snippet["code"]
    reconstructed = "".join(chunk["code"] for chunk in chunks)

    if reconstructed != original_code:
        raise ValueError("Chunk reconstruction mismatch")

    expected_line = snippet["start_line"]

    for chunk in chunks:
        if chunk["start_line"] != expected_line:
            raise ValueError("Gap or overlap between chunks")

        actual_lines = len(chunk["code"].splitlines())

        if actual_lines != chunk["line_count"]:
            raise ValueError("Incorrect chunk line count")

        if chunk["end_line"] - chunk["start_line"] + 1 != actual_lines:
            raise ValueError("Incorrect chunk source range")

        if chunk["resolved_commit"] != snippet["resolved_commit"]:
            raise ValueError("Commit mismatch")

        if chunk["source_sha256"] != snippet["source_sha256"]:
            raise ValueError("Source hash mismatch")

        expected_line = chunk["end_line"] + 1

    if expected_line != snippet["end_line"] + 1:
        raise ValueError("Incomplete source coverage")

    output_dir = Path(INTERMEDIATE_DIR) / component
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "code_chunks.json"

    output_path.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"[CHUNKS] {len(chunks)} saved")
    print(f"[VERIFIED] Full source coverage")
    print(f"[SAVED] {output_path}")

    return output_path


def validate_chunk_boundaries(snippet, chunks):
    """Identify AST constructs crossing chunk boundaries."""

    parser = Parser(Language(tree_sitter_cpp.language()))
    tree = parser.parse(snippet["code"].encode("utf-8"))

    if tree.root_node.has_error:
        raise ValueError("Invalid C++ AST")

    control_types = {
        "if_statement",
        "for_statement",
        "while_statement",
        "do_statement",
        "switch_statement",
        "try_statement",
        "catch_clause",
    }

    nodes = []

    def walk(node):
        if node.type in control_types:
            start = snippet["start_line"] + node.start_point.row

            end = (
                snippet["start_line"]
                + node.end_point.row
                - (1 if node.end_point.column == 0 else 0)
            )

            nodes.append({
                "type": node.type,
                "start_line": start,
                "end_line": end,
            })

        for child in node.named_children:
            walk(child)

    walk(tree.root_node)

    diagnostics = []

    for chunk in chunks[:-1]:
        boundary = chunk["end_line"]

        crossing = [
            node
            for node in nodes
            if node["start_line"] <= boundary < node["end_line"]
        ]

        diagnostics.append({
            "boundary_after_line": boundary,
            "crossing_scopes": crossing,
        })

    for diagnostic in diagnostics:
        print(
            f"\n[BOUNDARY] After line "
            f"{diagnostic['boundary_after_line']}"
        )

        if not diagnostic["crossing_scopes"]:
            print("  No crossing control-flow scopes")

        for scope in diagnostic["crossing_scopes"]:
            print(
                f"  {scope['type']}: "
                f"{scope['start_line']}-{scope['end_line']}"
            )

    return diagnostics


def annotate_chunk_continuity(chunks):
    """Describe control-flow scopes crossing chunk boundaries."""

    for chunk in chunks:
        first = chunk["start_line"]
        last = chunk["end_line"]

        continuity = []

        for scope in chunk.get("ast_context", []):
            start = scope["start_line"]
            end = scope["end_line"]

            continuity.append({
                "type": scope["type"],
                "scope_start_line": start,
                "scope_end_line": end,
                "continues_from_previous": start < first <= end,
                "continues_to_next": start <= last < end,
                "spans_entire_chunk": start < first and end > last,
            })

        chunk["scope_continuity"] = continuity

    return chunks


def build_code_chunks(component, max_lines=80):
    """
    Build AST-enriched chunks for every long C++ implementation
    already stored in code_snippets.json.
    """

    folder = Path(INTERMEDIATE_DIR) / component
    source_path = folder / "code_snippets.json"

    snippets = json.loads(
        source_path.read_text(encoding="utf-8")
    )

    all_chunks = []

    for snippet in snippets:
        line_count = len(snippet["code"].splitlines())

        if line_count <= max_lines:
            continue

        chunks = split_long_method(
            snippet,
            max_lines=max_lines
        )

        chunks = add_ast_context(snippet, chunks)
        chunks = add_active_scope_headers(snippet, chunks)
        chunks = annotate_chunk_continuity(chunks)

        if "".join(c["code"] for c in chunks) != snippet["code"]:
            raise ValueError(
                f"Incomplete chunks for {snippet['method']}"
            )

        all_chunks.extend(chunks)

    output_path = folder / "code_chunks.json"

    output_path.write_text(
        json.dumps(
            all_chunks,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(f"[CHUNKS] {len(all_chunks)} chunks saved")
    print(f"[SAVED] {output_path}")

    return all_chunks


def build_component_code(component, max_lines=80):
    """
    Automatically extract all matched C++ implementations
    and build AST chunks for long methods.
    """

    folder = Path(INTERMEDIATE_DIR) / component
    links_path = folder / "method_links.json"

    links_data = json.loads(
        links_path.read_text(encoding="utf-8")
    )

    selected = select_methods_for_snippets(
        links_data,
        max_lines=max_lines
    )

    # Both short and long implementations.
    all_items = selected["short"] + selected["long"]

    # Deduplicate by exact implementation identity.
    unique_items = []
    seen = set()

    for item in all_items:
        key = (
            item["file"],
            item["start_line"],
            item["end_line"],
            item["signature"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique_items.append(item)

    # Save all complete methods.
    snippets = extract_code_snippets(
        component,
        unique_items
    )

    # Build AST chunks for long methods.
    chunks = build_code_chunks(
        component,
        max_lines=max_lines
    )

    print(
        f"[COMPONENT COMPLETE] {component}: "
        f"{len(snippets)} snippets, "
        f"{len(chunks)} chunks"
    )

    return {
        "component": component,
        "snippets": snippets,
        "chunks": chunks,
    }
