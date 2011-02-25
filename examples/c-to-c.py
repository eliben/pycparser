#-----------------------------------------------------------------
# pycparser: c-to-c.py
#
# Example of a C code generator from pycparser AST nodes, serving 
# as a simplistic translator from C to AST and back to C.
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


class CGenerator(object):
    """ Uses the same visitor pattern as c_ast.NodeVisitor, but modified to
        return a value from each visit method, using string accumulation in 
        generic_visit.
    """
    def __init__(self):
        self.output = ''
        
        # Statements start with indentation of self.indent_level spaces
        #
        self.indent_level = 0
    
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        return getattr(self, method, self.generic_visit)(node)
    
    def generic_visit(self, node):
        #~ print('generic:', type(node))
        if node is None:
            return ''
        else:
            return ''.join(self.visit(c) for c in node.children())
    
    def visit_Constant(self, n):
        return n.value
        
    def visit_ID(self, n):
        return n.name
    
    def visit_IdentifierType(self, n):
        return ' '.join(n.names) + ' '
    
    def visit_Decl(self, n):
        s = self._generate_decl(n)
        if n.bitsize: s += ' : ' + self.visit(n.bitsize)
        if n.init: s += ' = ' + self.visit(n.init)
        return s
    
    def visit_FuncDef(self, n):
        decl = self.visit(n.decl)
        self.indent_level = 0
        body = self.visit(n.body)
        return decl + '\n' + body

    def _generate_decl(self, n):
        """ Generation from a Decl node.
        """
        s = ''
        if n.funcspec: s = ' '.join(n.funcspec) + ' '
        if n.storage: s += ' '.join(n.storage) + ' '
        s += self._generate_type(n.type)
        return s
    
    def _generate_type(self, n, modifiers=[]):
        """ Recursive generation from a type node. n is the type node. 
            modifiers collects the PtrDecl, ArrayDecl and FuncDecl modifiers 
            encountered on the way down to a TypeDecl, to allow proper
            generation from it.
        """
        typ = type(n)
        #~ print(n, modifiers)
        
        if typ == c_ast.TypeDecl:
            s = ''
            if n.quals: s += ' '.join(n.quals) + ' '
            s += self.visit(n.type)
            
            nstr = n.declname if n.declname else ''
            # Resolve odifiers.
            # Wrap in parens to distinguish pointer to array and pointer to
            # function syntax.
            #
            for i, modifier in enumerate(modifiers):
                if isinstance(modifier, c_ast.ArrayDecl):
                    if (i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl)):
                        nstr = '(' + nstr + ')'
                    nstr += '[' + self.visit(modifier.dim) + ']'
                elif isinstance(modifier, c_ast.FuncDecl):
                    if (i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl)):
                        nstr = '(' + nstr + ')'
                    nstr += '(' + self.visit(modifier.args) + ')'
                elif isinstance(modifier, c_ast.PtrDecl):
                    nstr = '*' + nstr
            s += nstr
            return s
        elif typ in (c_ast.Typename, c_ast.Decl):
            return self._generate_decl(n.type)
        elif typ == c_ast.IdentifierType:
            return ' '.join(n.names) + ' '
        elif typ in (c_ast.ArrayDecl, c_ast.PtrDecl, c_ast.FuncDecl):
            return self._generate_type(n.type, modifiers + [n])


def translate_to_c(filename):
    ast = parse_file(filename, use_cpp=True)
    generator = CGenerator()
    print(generator.visit(ast))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        translate_to_c(sys.argv[1])
    else:
        src = r'''
        static const int (**c[chevo])[2] = t;
        int (*joe)();
        
        int main() {
            int kk;
        }
        '''
        parser = c_parser.CParser()
        ast = parser.parse(src)
        ast.show()
        generator = CGenerator()
        print(generator.visit(ast))
        
        print("Please provide a filename as argument")
