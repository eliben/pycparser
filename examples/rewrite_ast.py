#-----------------------------------------------------------------
# pycparser: func_write.py
#
# Tiny example of rewriting a AST node
#
# Copyright (C) 2014, Akira Hayakawa
# License: BSD
#-----------------------------------------------------------------
from __future__ import print_function
import sys

from pycparser import c_parser, c_ast, c_generator

text = r"""
void func(void)
{
  x = 1;
}
"""

generator = c_generator.CGenerator()

parser = c_parser.CParser()
ast = parser.parse(text)
print("Before:")
ast.show(offset=2)
print("\n%s" % generator.visit(ast))

assign = ast.ext[0].body.block_items[0]
assign.lvalue.name = "y"
assign.rvalue.value = 2

ast.ext.insert(0, c_ast.Any("#define f(a) ((a) * 2)"))
ast.ext.insert(1, c_ast.Any("/* rewrited function */"))

print("After:")
ast.show(offset=2)
print("\n%s" % generator.visit(ast))
