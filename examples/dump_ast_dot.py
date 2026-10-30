# -----------------------------------------------------------------
# pycparser: dump_ast_dot.py
#
# Export a parsed AST as Graphviz DOT without a Graphviz dependency.
# License: BSD
# -----------------------------------------------------------------
import argparse
import io
import sys

sys.path.extend([".", ".."])

from pycparser import c_ast, parse_file
from pycparser.c_parser import ParseError


def _quote(text: str) -> str:
    """Quote a DOT string, preserving backslashes and nonprinting characters."""
    parts = []
    for char in text:
        if char in ('"', "\\"):
            parts.append("\\" + char)
        elif char == "\n":
            parts.append("\\n")
        elif not char.isprintable():
            # Escape the backslash too: DOT labels should display the escape,
            # rather than interpreting it as a Graphviz substitution.
            parts.append("\\" + repr(char)[1:-1])
        else:
            parts.append(char)
    return '"' + "".join(parts) + '"'


def ast_to_dot(ast: c_ast.Node, showcoord: bool = False) -> str:
    """Render an AST with deterministic preorder IDs and named child edges."""
    lines = ["digraph AST {", "  node [shape=box];"]
    pending = [(ast, None, "")]
    next_id = 0
    while pending:
        node, parent_id, child_name = pending.pop()
        node_id = next_id
        next_id += 1
        label = [type(node).__name__]
        label.extend(f"{name}: {getattr(node, name)!r}" for name in node.attr_names)
        if showcoord and node.coord is not None:
            label.append(f"coord: {node.coord}")
        lines.append(f"  n{node_id} [label={_quote(chr(10).join(label))}];")
        if parent_id is not None:
            lines.append(f"  n{parent_id} -> n{node_id} [label={_quote(child_name)}];")
        pending.extend(
            (child, node_id, name) for name, child in reversed(node.children())
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    argparser = argparse.ArgumentParser(
        description="Dump a parsed C AST as Graphviz DOT"
    )
    argparser.add_argument(
        "filename",
        default="examples/c_files/basic.c",
        nargs="?",
        help="C file to parse (preprocess it first if needed)",
    )
    argparser.add_argument(
        "--coord", action="store_true", help="include node coordinates"
    )
    argparser.add_argument(
        "--encoding", default="utf-8", help="input file encoding (default: utf-8)"
    )
    args = argparser.parse_args()
    try:
        ast = parse_file(args.filename, use_cpp=False, encoding=args.encoding)
    except (OSError, UnicodeError, LookupError, ParseError) as exc:
        print(f"{argparser.prog}: {exc}", file=sys.stderr)
        return 1
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(ast_to_dot(ast, showcoord=args.coord))
    return 0


if __name__ == "__main__":
    sys.exit(main())
