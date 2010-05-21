#-----------------------------------------------------------------
# pycparser: func_defs.py
#
# Using pycparser for printing out all the calls of some function
# in a C file.
#
# Copyright (C) 2008, Eli Bendersky
# License: LGPL
#-----------------------------------------------------------------
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
#
sys.path.insert(0, '..')

from pycparser import c_parser, c_ast, parse_file
from pycparser.portability import printme


# A visitor with some state information (the funcname it's 
# looking for)
#
class FuncCallVisitor(c_ast.NodeVisitor):
    def __init__(self, funcname):
        self.funcname = funcname

    def visit_FuncCall(self, node):
        if node.name.name == self.funcname:
            printme('%s called at %s\n' % (
                    self.funcname, node.name.coord))


def show_func_calls(filename, funcname):
    ast = parse_file(filename, use_cpp=True)        
    v = FuncCallVisitor(funcname)
    v.visit(ast)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        filename  = sys.argv[1]
        func = sys.argv[2]
    else:
        filename = 'c_files/hash.c'
        func = 'malloc'

    show_func_calls(filename, func)



