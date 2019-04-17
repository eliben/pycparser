# -----------------------------------------------------------------
# pycparser: rewrite_ast_assignment.py
#
# Tiny example of rewriting a AST node
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
# -----------------------------------------------------------------
from __future__ import print_function

from copy import deepcopy

from pycparser import c_ast
from pycparser import c_parser


class RewriteVisitor(c_ast.NodeVisitor):

    def visit_Assignment(self, pyc_assign: c_ast.Assignment):
        if len(pyc_assign.op) > 1:
            lvalue = deepcopy(pyc_assign.lvalue)

            # Coordinate of node may be wrong
            new_op = c_ast.BinaryOp(pyc_assign.op[:-1], lvalue, pyc_assign.rvalue, pyc_assign.coord)

            pyc_assign.op = '='
            pyc_assign.rvalue = new_op


if __name__ == "__main__":
    text = r"""
    void func(void)
    {
        w += 1;
        x -= 2;
        y *= 3;
        z /= 4;
    }
    """

    parser = c_parser.CParser()
    ast = parser.parse(text)
    print("Before:")
    ast.show(offset=2)

    RewriteVisitor().visit(ast)
    assign = ast.ext[0].body.block_items[0]

    print("After:")
    ast.show(offset=2)
