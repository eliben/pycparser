#-----------------------------------------------------------------
# pycparser: _build_tables.py
#
# A dummy for generating the lexing/parsing tables and and 
# compiling them into .pyc for faster execution in optimized mode.
# Also generates AST code from the _c_ast.yaml configuration file.
#
# Copyright (C) 2008, Eli Bendersky
# License: LGPL
#-----------------------------------------------------------------

# Generate c_ast.py
#
from _ast_gen import ASTCodeGenerator
ast_gen = ASTCodeGenerator('_c_ast.yaml')
ast_gen.generate(open('c_ast.py', 'w'))

import c_parser

# Generates the tables
#
c_parser.CParser(
    lex_optimize=True, 
    yacc_debug=False, 
    yacc_optimize=True)

# Load to compile into .pyc
#
import lextab
import yacctab
import c_ast
