from sys import stdout

from pycparser.ply import cpp, lex
# for lexer
from pycparser.ply.cpp import *

p = cpp.Preprocessor(lex.lex())

f = open('c_files/concatenation.c', 'r')
code = f.read()
f.close()

p.parse(code)
while True:
    t = p.token()
    if not t:
        break
    stdout.write(t.value)

