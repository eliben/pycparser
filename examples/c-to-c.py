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
        
        # Statements start with indentation of self.indent_level spaces, using
        # the _make_indent method
        #
        self.indent_level = 0
    
    def _make_indent(self):
        return ' ' * self.indent_level
    
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

    def visit_ArrayRef(self, n):
        return self.visit(n.name) + '[' + self.visit(n.subscript) + ']'

    def visit_UnaryOp(self, n):
        if n.op == 'p++':
            return '%s++' % self.visit(n.expr)
        else:
            return '%s%s' % (n.op, self.visit(n.expr))

    def visit_BinaryOp(self, n):
        return '%s %s %s' % (self.visit(n.left), n.op, self.visit(n.right))
    
    def visit_Assignment(self, n):
        return '%s %s %s' % (self.visit(n.lvalue), n.op, self.visit(n.rvalue))
    
    def visit_IdentifierType(self, n):
        return ' '.join(n.names)
    
    def visit_Decl(self, n):
        s = self._generate_decl(n)
        if n.bitsize: s += ' : ' + self.visit(n.bitsize)
        if n.init: s += ' = ' + self.visit(n.init)
        return s
    
    def visit_Typedef(self, n):
        s = ''
        if n.storage: s += ' '.join(n.storage) + ' '
        s += self._generate_type(n.type)
        return s
    
    def visit_Cast(self, n):
        s = '(' + self.visit(n.to_type) + ')' 
        return s + ' ' + self.visit(n.expr)
    
    def visit_Enum(self, n):
        s = 'enum'
        if n.name: s += ' ' + n.name
        if n.values:
            s += ' {'
            for i, enumerator in enumerate(n.values.enumerators):
                s += enumerator.name
                if enumerator.value: 
                    s += ' = ' + self.visit(enumerator.value)
                if i != len(n.values.enumerators) - 1: 
                    s += ', '
            s += '}'
        return s
    
    def visit_Struct(self, n):
        s = 'struct'
        if n.name: s += ' ' + n.name
        if n.decls:
            s += ' { \n'
            for decl in n.decls:
                s += '  ' + self.visit(decl) + ';\n'
            s += '}'
        return s
        
    def visit_FuncDef(self, n):
        decl = self.visit(n.decl)
        self.indent_level = 0
        # The body is a Compound node
        body = self.visit(n.body)
        return decl + '\n' + body + '\n'

    def visit_FileAST(self, n):
        s = ''
        for ext in n.ext:
            if isinstance(ext, c_ast.FuncDef):
                s += self.visit(ext)
            else:
                s += self.visit(ext) + ';\n'
        return s

    def visit_Compound(self, n):
        s = self._make_indent() + '{\n'
        self.indent_level += 2
        s += ''.join(self._generate_stmt(stmt) for stmt in n.block_items)
        self.indent_level -= 2
        s += self._make_indent() + '}\n'
        return s
    
    def visit_ParamList(self, n):
        return ', '.join(self.visit(param) for param in n.params)

    def visit_Return(self, n):
        s = 'return'
        if n.expr: s += ' ' + self.visit(n.expr)
        return s + ';'

    def visit_Break(self, n):
        return 'break;'
        
    def visit_Continue(self, n):
        return 'continue;'
        
    def visit_For(self, n):
        s = 'for ('
        if n.init: s += self.visit(n.init)
        s += ';'
        if n.cond: s += ' ' + self.visit(n.cond)
        s += ';'
        if n.next: s += ' ' + self.visit(n.next)
        s += ')\n'
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def visit_While(self, n):
        s = 'while ('
        if n.cond: s += self.visit(n.cond)
        s += ')\n'
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def _generate_stmt(self, n, add_indent=False):
        """ Generation from a statement node. This method exists as a wrapper
            for individual visit_* methods to handle different treatment of 
            some statements in this context.
        """
        typ = type(n)
        if add_indent: self.indent_level += 2
        indent = self._make_indent()
        if add_indent: self.indent_level -= 2
        
        if typ in ( c_ast.Decl, c_ast.Assignment, c_ast.Cast, c_ast.UnaryOp,
                    c_ast.BinaryOp):
            # These can also appear in an expression context so no semicolon
            # is added to them automatically
            #
            return indent + self.visit(n) + ';\n'
        elif typ in (c_ast.Compound,):
            # No extra indentation required before the opening brace of a 
            # compound - because it consists of multiple lines it has to 
            # compute its own indentation.
            #
            return self.visit(n)
        else:
            return indent + self.visit(n) + '\n'

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
            # Resolve modifiers.
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
            s += ' ' + nstr
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
static unsigned int hash_func(const char* str, unsigned int table_size)
{
    unsigned int hash_value;
    unsigned int a = 127;
    a++;
    ++a;

    while (hash_value == 0) {
        hash_value = (a*hash_value + *str) % table_size;
        break;
    }

    return hash_value;
}

        '''
        parser = c_parser.CParser()
        ast = parser.parse(src)
        ast.show()
        generator = CGenerator()
        print(generator.visit(ast))
        
        print("Please provide a filename as argument")


# ZZZ: operator precedence in expressions - especially problematic in 
# assignments... - where to parenthesize? maybe just in BinaryOp?
# Other precedence-important operators (such as cast) need parens as well

# ZZZ: turn self.indent_level += 2 ... -= 2 into a context manager!

