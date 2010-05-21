from pycparser.c_ast import *
from pycparser.c_parser import CParser, Coord, ParseError


def expand_decl(decl):
    """ Converts the declaration into a nested list.
    """
    typ = type(decl)
    
    if typ == TypeDecl:
        return ['TypeDecl', expand_decl(decl.type)]
    elif typ == IdentifierType:
        return ['IdentifierType', decl.names]
    elif typ == ID:
        return ['ID', decl.name]
    elif typ in [Struct, Union]:
        decls = [expand_decl(d) for d in decl.decls or []]
        return [typ.__name__, decl.name, decls]
    else:        
        nested = expand_decl(decl.type)
    
        if typ == Decl:
            if decl.quals:
                return ['Decl', decl.quals, decl.name, nested]
            else:
                return ['Decl', decl.name, nested]
        elif typ == Typename: # for function parameters
            if decl.quals:
                return ['Typename', decl.quals, nested]
            else:
                return ['Typename', nested]
        elif typ == ArrayDecl:
            dimval = decl.dim.value if decl.dim else ''
            return ['ArrayDecl', dimval, nested]
        elif typ == PtrDecl:
            return ['PtrDecl', nested]
        elif typ == Typedef:
            return ['Typedef', decl.name, nested]
        elif typ == FuncDecl:
            if decl.args:
                params = [expand_decl(param) for param in decl.args.params]
            else:
                params = []
            return ['FuncDecl', params, nested]

#-----------------------------------------------------------------

source_code = """
int main()
{
    int a;
    a = sizeof(int());
}
"""

parser = CParser()
ast = parser.parse(source_code)
function_body = ast.ext[0].body #hardcoded to the main() function

for stmt in function_body.stmts:
    print stmt.coord, expand_decl(stmt.rvalue.expr.type)
    
#~ class StructRefVisitor(c_ast.NodeVisitor):
    #~ def visit_StructRef(self, node):
        #~ print node.name.name, node.field.name


#~ parser = c_parser.CParser()
#~ ast = parser.parse(code)

#~ ast.show()

#~ v = StructRefVisitor()
#~ v.visit(ast)

