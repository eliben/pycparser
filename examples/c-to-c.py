#-----------------------------------------------------------------
# pycparser: c-to-c.py
#
# Example of 
#
# Copyright (C) 2008-2011, Eli Bendersky
# License: LGPL
#-----------------------------------------------------------------
from __future__ import print_function
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
#
sys.path.insert(0, '..')

from pycparser import c_parser, c_ast, parse_file


class CGenerator(c_ast.NodeVisitor):
    def __init__(self):
        self.output = ''
        
    def out(self, s):
        self.output += s
    
    def visit_Constant(self, n):
        self.out(n.value)

    def visit_ID(self, n):
        self.out(n.name)
    
    def visit_IdentifierType(self, n):
        self.out(' '.join(n.names) + ' ')
    
    def visit_TypeDecl(self, n):
        self.generic_visit(n)
        if n.declname: self.out(n.declname)
    
    def visit_PtrDecl(self, n):
        self.out('*')
        self.visit(n.type)
    
    def _generate_decl(self, n):
        """ Generation from a Decl node.
        """
        if n.funcspec: self.out(' '.join(n.funcspec) + ' ')
        if n.storage: self.out(' '.join(n.storage) + ' ')
        self._generate_type(n.type)
    
    def _generate_type(self, n, modifiers=[]):
        """ Recursive generation from a type node. n is the type node. 
            modifiers collects the PtrDecl and ArrayDecl modifiers encountered
            on the way down to a TypeDecl, to allow proper generation from it.
        """
        typ = type(n)
        #~ print(n, modifiers)
        
        if typ == c_ast.TypeDecl:
            self.out(' '.join(n.quals) + ' ')
            self.generic_visit(n)
            
            nstr = n.declname if n.declname else ''
            # Resolve pointer & array modifiers.
            # Wrap in parens to distinguish pointer to array syntax
            #
            for i, modifier in enumerate(modifiers):
                if isinstance(modifier, c_ast.ArrayDecl):
                    if (i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl)):
                        nstr = '(' + nstr + ')'
                    nstr += '[' + modifier.dim.value + ']'
                elif isinstance(modifier, c_ast.PtrDecl):
                    nstr = '*' + nstr
            self.out(nstr)
        elif typ in (c_ast.Typename, c_ast.Decl):
            self._generate_decl(n.type)
        elif typ == c_ast.IdentifierType:
            self.out(' '.join(n.names) + ' ')
        elif typ in (c_ast.ArrayDecl, c_ast.PtrDecl):
            self._generate_type(n.type, modifiers + [n])
        
        
    def visit_Decl(self, n):
        self._generate_decl(n)
        self.out(';\n')


def translate_to_c(filename):
    ast = parse_file(filename, use_cpp=True)
    generator = CGenerator()
    generator.visit(ast)
    print(generator.output)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        translate_to_c(sys.argv[1])
    else:
        src = r'''
        static const int (**c[9])[2] = t;
        '''
        parser = c_parser.CParser()
        ast = parser.parse(src)
        ast.show()
        generator = CGenerator()
        generator.visit(ast)
        print(generator.output)
        
        
        print("Please provide a filename as argument")
