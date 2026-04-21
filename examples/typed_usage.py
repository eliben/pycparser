# ------------------------------------------------------------------------------
# pycparser: typed_usage.py
#
# A minimal example of how static type checking helps use pycparser correctly.
#
# The important parts are the narrowings:
# - ast.ext[...] entries start out as generic AST nodes
# - Decl.coord is optional and must be checked before use
# - Decl.type must be narrowed before accessing node-specific attributes
#
# Run it from the root directory of pycparser.
# ------------------------------------------------------------------------------
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend([".", ".."])

from pycparser import c_ast, c_parser


SAMPLE_DECL = "const unsigned int *value;"


def parse_single_decl(source: str) -> c_ast.Decl:
    ast = c_parser.CParser().parse(source, filename="<stdin>")
    node = ast.ext[-1]

    # Without this guard, type checkers only know that ext entries are Nodes.
    if not isinstance(node, c_ast.Decl):
        raise TypeError("expected a declaration")

    return node


def require_coord(node: c_ast.Node) -> c_parser.Coord:
    coord = node.coord

    # Without this guard, `coord.line` is a type error because coord may be None.
    if coord is None:
        raise ValueError("node has no source coordinate")

    return coord


def describe_type(type_node: c_ast.Node) -> str:
    # Without these isinstance checks, attributes such as `.type`, `.quals`,
    # and `.names` are not safe to access.
    if isinstance(type_node, c_ast.TypeDecl):
        quals = " ".join(type_node.quals)
        base = describe_type(type_node.type)
        return f"{quals} {base}".strip()

    if isinstance(type_node, c_ast.PtrDecl):
        quals = " ".join(type_node.quals)
        pointer = "pointer"
        if quals:
            pointer = f"{quals} {pointer}"
        return f"{pointer} to {describe_type(type_node.type)}"

    if isinstance(type_node, c_ast.IdentifierType):
        return " ".join(type_node.names)

    raise TypeError(f"unsupported declaration type: {type_node.__class__.__name__}")


def show_decl(source: str) -> None:
    decl = parse_single_decl(source)
    coord = require_coord(decl)
    print(f"{decl.name}: {describe_type(decl.type)} at {coord}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show_decl(sys.argv[1])
    else:
        show_decl(SAMPLE_DECL)
