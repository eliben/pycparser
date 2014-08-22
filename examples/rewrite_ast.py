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

from pycparser import c_parser

text = r"""
void func(void)
{
  x = 1;
}
"""

parser = c_parser.CParser()
ast = parser.parse(text)
print("Before:")
ast.show(offset=2)

assign = ast.ext[0].body.block_items[0]
assign.lvalue.name = "y"
assign.rvalue.value = 2

print("After:")
ast.show(offset=2)
