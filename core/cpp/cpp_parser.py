from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_cpp

import re

class SofaCppParser:
    """
    Parse C++ source code using Tree-sitter.

    Responsibilities:
    - Initialize the C++ grammar.
    - Parse C++ source code into a Concrete Syntax Tree (CST).
    - Parse local C++ files.
    - Retrieve the original text associated with a syntax node.
    - Report syntax errors detected by Tree-sitter.
    """

    def __init__(self):
        self.language = Language(tree_sitter_cpp.language())
        self.parser = Parser(self.language)

    
    
    def parse_source(self, source_code):
        """
        Parse C++ while masking SOFA export macros
        only in class/struct declarations.

        Original source bytes and positions are preserved.
        """

        source_bytes = source_code.encode("utf-8")
        normalized = bytearray(source_bytes)

        pattern = rb"\b(?:class|struct)\s+(SOFA_[A-Z0-9_]*_API)\s+"

        for match in re.finditer(pattern, source_bytes):
            start, end = match.span(1)

            # Mask only the export macro, preserving positions.
            normalized[start:end] = b" " * (end - start)

        tree = self.parser.parse(bytes(normalized))

        return tree, source_bytes



    def parse_file(self, file_path):
        """
        Read a local C++ file and parse its contents.
        """
        file_path = Path(file_path)

        if not file_path.is_file():
            raise FileNotFoundError(
                f"C++ source file not found: {file_path}"
            )

        source_code = file_path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        return self.parse_source(source_code)

    @staticmethod
    def get_node_text(node, source_bytes):
        """
        Extract the original source text corresponding
        to a Tree-sitter syntax node.
        """
        return source_bytes[
            node.start_byte:node.end_byte
        ].decode("utf-8")

    @staticmethod
    def has_syntax_errors(tree):
        """
        Report whether Tree-sitter detected syntax errors.
        """
        return tree.root_node.has_error
