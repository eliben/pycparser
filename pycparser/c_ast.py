#-----------------------------------------------------------------
# ** ATTENTION **
# This code was automatically generated from the file:
# _c_ast.cfg
#
# Do not modify it directly. Modify the configuration file and
# run the generator again.
# ** ** *** ** **
#
# pycparser: c_ast.py
#
# AST Node classes.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------


import sys

def _repr(obj):
    """
    Get the representation of an object, with dedicated pprint-like format for lists.
    """
    if isinstance(obj, list):
        return '[' + (',\n '.join((_repr(e).replace('\n', '\n ') for e in obj))) + '\n]'
    else:
        return repr(obj)

class Node(object):
    __slots__ = ()
    """ Abstract base class for AST nodes.
    """
    def __repr__(self):
        """ Generates a python representation of the current node
        """
        result = self.__class__.__name__ + '('

        indent = ''
        separator = ''
        for name in self.__slots__[:-2]:
            result += separator
            result += indent
            result += name + '=' + (_repr(getattr(self, name)).replace('\n', '\n  ' + (' ' * (len(name) + len(self.__class__.__name__)))))

            separator = ','
            indent = '\n ' + (' ' * len(self.__class__.__name__))

        result += indent + ')'

        return result

    def children(self):
        """ A sequence of all children that are Nodes
        """
        pass

    def show(self, buf=sys.stdout, offset=0, attrnames=False, nodenames=False, showcoord=False, _my_node_name=None):
        """ Pretty print the Node and all its attributes and
            children (recursively) to a buffer.

            buf:
                Open IO buffer into which the Node is printed.

            offset:
                Initial offset (amount of leading spaces)

            attrnames:
                True if you want to see the attribute names in
                name=value pairs. False to only see the values.

            nodenames:
                True if you want to see the actual node names
                within their parents.

            showcoord:
                Do you want the coordinates of each Node to be
                displayed.
        """
        lead = ' ' * offset
        if nodenames and _my_node_name is not None:
            buf.write(lead + self.__class__.__name__+ ' <' + _my_node_name + '>: ')
        else:
            buf.write(lead + self.__class__.__name__+ ': ')

        if self.attr_names:
            if attrnames:
                nvlist = [(n, getattr(self,n)) for n in self.attr_names]
                attrstr = ', '.join('%s=%s' % nv for nv in nvlist)
            else:
                vlist = [getattr(self, n) for n in self.attr_names]
                attrstr = ', '.join('%s' % v for v in vlist)
            buf.write(attrstr)

        if showcoord:
            buf.write(' (at %s)' % self.coord)
        buf.write('\n')

        for (child_name, child) in self.children():
            child.show(
                buf,
                offset=offset + 2,
                attrnames=attrnames,
                nodenames=nodenames,
                showcoord=showcoord,
                _my_node_name=child_name)


class NodeVisitor(object):
    """ A base NodeVisitor class for visiting c_ast nodes.
        Subclass it and define your own visit_XXX methods, where
        XXX is the class name you want to visit with these
        methods.

        For example:

        class ConstantVisitor(NodeVisitor):
            def __init__(self):
                self.values = []

            def visit_Constant(self, node):
                self.values.append(node.value)

        Creates a list of values of all the constant nodes
        encountered below the given node. To use it:

        cv = ConstantVisitor()
        cv.visit(node)

        Notes:

        *   generic_visit() will be called for AST nodes for which
            no visit_XXX method was defined.
        *   The children of nodes for which a visit_XXX was
            defined will not be visited - if you need this, call
            generic_visit() on the node.
            You can use:
                NodeVisitor.generic_visit(self, node)
        *   Modeled after Python's own AST visiting facilities
            (the ast module of Python 3.0)
    """

    _method_cache = None

    def visit(self, node):
        """ Visit a node.
        """

        if self._method_cache is None:
            self._method_cache = {}

        visitor = self._method_cache.get(node.__class__.__name__, None)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        return visitor(node)

    def generic_visit(self, node):
        """ Called if no explicit visitor function exists for a
            node. Implements preorder visiting of the node.
        """
        for c in node:
            self.visit(c)

class ArrayDecl(Node):
    __slots__ = ('type', 'dim', 'dim_quals', 'coord', '__weakref__')
    def __init__(self, type, dim, dim_quals, coord=None):
        self.type = type
        self.dim = dim
        self.dim_quals = dim_quals
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        if self.dim is not None: nodelist.append(("dim", self.dim))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type
        if self.dim is not None:
            yield self.dim

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, ArrayDecl): return False
        if self.type != o.type: return False
        if self.dim != o.dim: return False
        if self.dim_quals != o.dim_quals: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('dim_quals', )

class ArrayRef(Node):
    __slots__ = ('name', 'subscript', 'coord', '__weakref__')
    def __init__(self, name, subscript, coord=None):
        self.name = name
        self.subscript = subscript
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.subscript is not None: nodelist.append(("subscript", self.subscript))
        return tuple(nodelist)

    def __iter__(self):
        if self.name is not None:
            yield self.name
        if self.subscript is not None:
            yield self.subscript

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, ArrayRef): return False
        if self.name != o.name: return False
        if self.subscript != o.subscript: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Assignment(Node):
    __slots__ = ('op', 'lvalue', 'rvalue', 'coord', '__weakref__')
    def __init__(self, op, lvalue, rvalue, coord=None):
        self.op = op
        self.lvalue = lvalue
        self.rvalue = rvalue
        self.coord = coord

    def children(self):
        nodelist = []
        if self.lvalue is not None: nodelist.append(("lvalue", self.lvalue))
        if self.rvalue is not None: nodelist.append(("rvalue", self.rvalue))
        return tuple(nodelist)

    def __iter__(self):
        if self.lvalue is not None:
            yield self.lvalue
        if self.rvalue is not None:
            yield self.rvalue

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Assignment): return False
        if self.op != o.op: return False
        if self.lvalue != o.lvalue: return False
        if self.rvalue != o.rvalue: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('op', )

class Alignas(Node):
    __slots__ = ('alignment', 'coord', '__weakref__')
    def __init__(self, alignment, coord=None):
        self.alignment = alignment
        self.coord = coord

    def children(self):
        nodelist = []
        if self.alignment is not None: nodelist.append(("alignment", self.alignment))
        return tuple(nodelist)

    def __iter__(self):
        if self.alignment is not None:
            yield self.alignment

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Alignas): return False
        if self.alignment != o.alignment: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Atomic(Node):
    __slots__ = ('subtype', 'coord', '__weakref__')
    def __init__(self, subtype, coord=None):
        self.subtype = subtype
        self.coord = coord

    def children(self):
        nodelist = []
        if self.subtype is not None: nodelist.append(("subtype", self.subtype))
        return tuple(nodelist)

    def __iter__(self):
        if self.subtype is not None:
            yield self.subtype

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Atomic): return False
        if self.subtype != o.subtype: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class BinaryOp(Node):
    __slots__ = ('op', 'left', 'right', 'coord', '__weakref__')
    def __init__(self, op, left, right, coord=None):
        self.op = op
        self.left = left
        self.right = right
        self.coord = coord

    def children(self):
        nodelist = []
        if self.left is not None: nodelist.append(("left", self.left))
        if self.right is not None: nodelist.append(("right", self.right))
        return tuple(nodelist)

    def __iter__(self):
        if self.left is not None:
            yield self.left
        if self.right is not None:
            yield self.right

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, BinaryOp): return False
        if self.op != o.op: return False
        if self.left != o.left: return False
        if self.right != o.right: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('op', )

class Break(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Break): return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Case(Node):
    __slots__ = ('expr', 'stmts', 'coord', '__weakref__')
    def __init__(self, expr, stmts, coord=None):
        self.expr = expr
        self.stmts = stmts
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        for i, child in enumerate(self.stmts or []):
            nodelist.append(("stmts[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr
        for child in (self.stmts or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Case): return False
        if self.expr != o.expr: return False
        if self.stmts != o.stmts: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Cast(Node):
    __slots__ = ('to_type', 'expr', 'coord', '__weakref__')
    def __init__(self, to_type, expr, coord=None):
        self.to_type = to_type
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.to_type is not None: nodelist.append(("to_type", self.to_type))
        if self.expr is not None: nodelist.append(("expr", self.expr))
        return tuple(nodelist)

    def __iter__(self):
        if self.to_type is not None:
            yield self.to_type
        if self.expr is not None:
            yield self.expr

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Cast): return False
        if self.to_type != o.to_type: return False
        if self.expr != o.expr: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Compound(Node):
    __slots__ = ('block_items', 'coord', '__weakref__')
    def __init__(self, block_items, coord=None):
        self.block_items = block_items
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.block_items or []):
            nodelist.append(("block_items[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.block_items or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Compound): return False
        if self.block_items != o.block_items: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class CompoundLiteral(Node):
    __slots__ = ('type', 'init', 'coord', '__weakref__')
    def __init__(self, type, init, coord=None):
        self.type = type
        self.init = init
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        if self.init is not None: nodelist.append(("init", self.init))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type
        if self.init is not None:
            yield self.init

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, CompoundLiteral): return False
        if self.type != o.type: return False
        if self.init != o.init: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Constant(Node):
    __slots__ = ('type', 'value', 'coord', '__weakref__')
    def __init__(self, type, value, coord=None):
        self.type = type
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Constant): return False
        if self.type != o.type: return False
        if self.value != o.value: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('type', 'value', )

class Continue(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Continue): return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Decl(Node):
    __slots__ = ('name', 'quals', 'align', 'storage', 'funcspec', 'type', 'init', 'bitsize', 'coord', '__weakref__')
    def __init__(self, name, quals, align, storage, funcspec, type, init, bitsize, coord=None):
        self.name = name
        self.quals = quals
        self.align = align
        self.storage = storage
        self.funcspec = funcspec
        self.type = type
        self.init = init
        self.bitsize = bitsize
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        if self.init is not None: nodelist.append(("init", self.init))
        if self.bitsize is not None: nodelist.append(("bitsize", self.bitsize))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type
        if self.init is not None:
            yield self.init
        if self.bitsize is not None:
            yield self.bitsize

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Decl): return False
        if self.name != o.name: return False
        if self.quals != o.quals: return False
        if self.align != o.align: return False
        if self.storage != o.storage: return False
        if self.funcspec != o.funcspec: return False
        if self.type != o.type: return False
        if self.init != o.init: return False
        if self.bitsize != o.bitsize: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', 'quals', 'align', 'storage', 'funcspec', )

class DeclList(Node):
    __slots__ = ('decls', 'coord', '__weakref__')
    def __init__(self, decls, coord=None):
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.decls or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, DeclList): return False
        if self.decls != o.decls: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Default(Node):
    __slots__ = ('stmts', 'coord', '__weakref__')
    def __init__(self, stmts, coord=None):
        self.stmts = stmts
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.stmts or []):
            nodelist.append(("stmts[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.stmts or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Default): return False
        if self.stmts != o.stmts: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class DoWhile(Node):
    __slots__ = ('cond', 'stmt', 'coord', '__weakref__')
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.stmt is not None:
            yield self.stmt

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, DoWhile): return False
        if self.cond != o.cond: return False
        if self.stmt != o.stmt: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class EllipsisParam(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, EllipsisParam): return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class EmptyStatement(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, EmptyStatement): return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Enum(Node):
    __slots__ = ('name', 'values', 'coord', '__weakref__')
    def __init__(self, name, values, coord=None):
        self.name = name
        self.values = values
        self.coord = coord

    def children(self):
        nodelist = []
        if self.values is not None: nodelist.append(("values", self.values))
        return tuple(nodelist)

    def __iter__(self):
        if self.values is not None:
            yield self.values

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Enum): return False
        if self.name != o.name: return False
        if self.values != o.values: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', )

class Enumerator(Node):
    __slots__ = ('name', 'value', 'coord', '__weakref__')
    def __init__(self, name, value, coord=None):
        self.name = name
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        if self.value is not None: nodelist.append(("value", self.value))
        return tuple(nodelist)

    def __iter__(self):
        if self.value is not None:
            yield self.value

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Enumerator): return False
        if self.name != o.name: return False
        if self.value != o.value: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', )

class EnumeratorList(Node):
    __slots__ = ('enumerators', 'coord', '__weakref__')
    def __init__(self, enumerators, coord=None):
        self.enumerators = enumerators
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.enumerators or []):
            nodelist.append(("enumerators[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.enumerators or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, EnumeratorList): return False
        if self.enumerators != o.enumerators: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class ExprList(Node):
    __slots__ = ('exprs', 'coord', '__weakref__')
    def __init__(self, exprs, coord=None):
        self.exprs = exprs
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.exprs or []):
            nodelist.append(("exprs[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.exprs or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, ExprList): return False
        if self.exprs != o.exprs: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class FileAST(Node):
    __slots__ = ('ext', 'coord', '__weakref__')
    def __init__(self, ext, coord=None):
        self.ext = ext
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.ext or []):
            nodelist.append(("ext[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.ext or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, FileAST): return False
        if self.ext != o.ext: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class For(Node):
    __slots__ = ('init', 'cond', 'next', 'stmt', 'coord', '__weakref__')
    def __init__(self, init, cond, next, stmt, coord=None):
        self.init = init
        self.cond = cond
        self.next = next
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.init is not None: nodelist.append(("init", self.init))
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.next is not None: nodelist.append(("next", self.next))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.init is not None:
            yield self.init
        if self.cond is not None:
            yield self.cond
        if self.next is not None:
            yield self.next
        if self.stmt is not None:
            yield self.stmt

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, For): return False
        if self.init != o.init: return False
        if self.cond != o.cond: return False
        if self.next != o.next: return False
        if self.stmt != o.stmt: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class FuncCall(Node):
    __slots__ = ('name', 'args', 'coord', '__weakref__')
    def __init__(self, name, args, coord=None):
        self.name = name
        self.args = args
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.args is not None: nodelist.append(("args", self.args))
        return tuple(nodelist)

    def __iter__(self):
        if self.name is not None:
            yield self.name
        if self.args is not None:
            yield self.args

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, FuncCall): return False
        if self.name != o.name: return False
        if self.args != o.args: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class FuncDecl(Node):
    __slots__ = ('args', 'type', 'coord', '__weakref__')
    def __init__(self, args, type, coord=None):
        self.args = args
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.args is not None: nodelist.append(("args", self.args))
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.args is not None:
            yield self.args
        if self.type is not None:
            yield self.type

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, FuncDecl): return False
        if self.args != o.args: return False
        if self.type != o.type: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class FuncDef(Node):
    __slots__ = ('decl', 'param_decls', 'body', 'coord', '__weakref__')
    def __init__(self, decl, param_decls, body, coord=None):
        self.decl = decl
        self.param_decls = param_decls
        self.body = body
        self.coord = coord

    def children(self):
        nodelist = []
        if self.decl is not None: nodelist.append(("decl", self.decl))
        if self.body is not None: nodelist.append(("body", self.body))
        for i, child in enumerate(self.param_decls or []):
            nodelist.append(("param_decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        if self.decl is not None:
            yield self.decl
        if self.body is not None:
            yield self.body
        for child in (self.param_decls or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, FuncDef): return False
        if self.decl != o.decl: return False
        if self.param_decls != o.param_decls: return False
        if self.body != o.body: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Goto(Node):
    __slots__ = ('name', 'coord', '__weakref__')
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Goto): return False
        if self.name != o.name: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', )

class ID(Node):
    __slots__ = ('name', 'coord', '__weakref__')
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, ID): return False
        if self.name != o.name: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', )

class IdentifierType(Node):
    __slots__ = ('names', 'coord', '__weakref__')
    def __init__(self, names, coord=None):
        self.names = names
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, IdentifierType): return False
        if self.names != o.names: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('names', )

class If(Node):
    __slots__ = ('cond', 'iftrue', 'iffalse', 'coord', '__weakref__')
    def __init__(self, cond, iftrue, iffalse, coord=None):
        self.cond = cond
        self.iftrue = iftrue
        self.iffalse = iffalse
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.iftrue is not None: nodelist.append(("iftrue", self.iftrue))
        if self.iffalse is not None: nodelist.append(("iffalse", self.iffalse))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.iftrue is not None:
            yield self.iftrue
        if self.iffalse is not None:
            yield self.iffalse

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, If): return False
        if self.cond != o.cond: return False
        if self.iftrue != o.iftrue: return False
        if self.iffalse != o.iffalse: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class InitList(Node):
    __slots__ = ('exprs', 'coord', '__weakref__')
    def __init__(self, exprs, coord=None):
        self.exprs = exprs
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.exprs or []):
            nodelist.append(("exprs[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.exprs or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, InitList): return False
        if self.exprs != o.exprs: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Label(Node):
    __slots__ = ('name', 'stmt', 'coord', '__weakref__')
    def __init__(self, name, stmt, coord=None):
        self.name = name
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.stmt is not None:
            yield self.stmt

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Label): return False
        if self.name != o.name: return False
        if self.stmt != o.stmt: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', )

class NamedInitializer(Node):
    __slots__ = ('name', 'expr', 'coord', '__weakref__')
    def __init__(self, name, expr, coord=None):
        self.name = name
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        for i, child in enumerate(self.name or []):
            nodelist.append(("name[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr
        for child in (self.name or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, NamedInitializer): return False
        if self.name != o.name: return False
        if self.expr != o.expr: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class ParamList(Node):
    __slots__ = ('params', 'coord', '__weakref__')
    def __init__(self, params, coord=None):
        self.params = params
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.params or []):
            nodelist.append(("params[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.params or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, ParamList): return False
        if self.params != o.params: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class PtrDecl(Node):
    __slots__ = ('quals', 'type', 'coord', '__weakref__')
    def __init__(self, quals, type, coord=None):
        self.quals = quals
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, PtrDecl): return False
        if self.quals != o.quals: return False
        if self.type != o.type: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('quals', )

class Return(Node):
    __slots__ = ('expr', 'coord', '__weakref__')
    def __init__(self, expr, coord=None):
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Return): return False
        if self.expr != o.expr: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class StaticAssert(Node):
    __slots__ = ('cond', 'message', 'coord', '__weakref__')
    def __init__(self, cond, message, coord=None):
        self.cond = cond
        self.message = message
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.message is not None: nodelist.append(("message", self.message))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.message is not None:
            yield self.message

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, StaticAssert): return False
        if self.cond != o.cond: return False
        if self.message != o.message: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class StaticAssert(Node):
    __slots__ = ('cond', 'message', 'coord', '__weakref__')
    def __init__(self, cond, message, coord=None):
        self.cond = cond
        self.message = message
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.message is not None: nodelist.append(("message", self.message))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.message is not None:
            yield self.message

    attr_names = ()

class Struct(Node):
    __slots__ = ('name', 'decls', 'coord', '__weakref__')
    def __init__(self, name, decls, coord=None):
        self.name = name
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.decls or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Struct): return False
        if self.name != o.name: return False
        if self.decls != o.decls: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', )

class StructRef(Node):
    __slots__ = ('name', 'type', 'field', 'coord', '__weakref__')
    def __init__(self, name, type, field, coord=None):
        self.name = name
        self.type = type
        self.field = field
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.field is not None: nodelist.append(("field", self.field))
        return tuple(nodelist)

    def __iter__(self):
        if self.name is not None:
            yield self.name
        if self.field is not None:
            yield self.field

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, StructRef): return False
        if self.name != o.name: return False
        if self.type != o.type: return False
        if self.field != o.field: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('type', )

class Switch(Node):
    __slots__ = ('cond', 'stmt', 'coord', '__weakref__')
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.stmt is not None:
            yield self.stmt

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Switch): return False
        if self.cond != o.cond: return False
        if self.stmt != o.stmt: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class TernaryOp(Node):
    __slots__ = ('cond', 'iftrue', 'iffalse', 'coord', '__weakref__')
    def __init__(self, cond, iftrue, iffalse, coord=None):
        self.cond = cond
        self.iftrue = iftrue
        self.iffalse = iffalse
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.iftrue is not None: nodelist.append(("iftrue", self.iftrue))
        if self.iffalse is not None: nodelist.append(("iffalse", self.iffalse))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.iftrue is not None:
            yield self.iftrue
        if self.iffalse is not None:
            yield self.iffalse

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, TernaryOp): return False
        if self.cond != o.cond: return False
        if self.iftrue != o.iftrue: return False
        if self.iffalse != o.iffalse: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class TypeDecl(Node):
    __slots__ = ('declname', 'quals', 'align', 'type', 'coord', '__weakref__')
    def __init__(self, declname, quals, align, type, coord=None):
        self.declname = declname
        self.quals = quals
        self.align = align
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, TypeDecl): return False
        if self.declname != o.declname: return False
        if self.quals != o.quals: return False
        if self.align != o.align: return False
        if self.type != o.type: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('declname', 'quals', 'align', )

class Typedef(Node):
    __slots__ = ('name', 'quals', 'align', 'storage', 'type', 'coord', '__weakref__')
    def __init__(self, name, quals, align, storage, type, coord=None):
        self.name = name
        self.quals = quals
        self.align = align
        self.storage = storage
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Typedef): return False
        if self.name != o.name: return False
        if self.quals != o.quals: return False
        if self.align != o.align: return False
        if self.storage != o.storage: return False
        if self.type != o.type: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', 'quals', 'align', 'storage', )

class Typename(Node):
    __slots__ = ('name', 'quals', 'align', 'type', 'coord', '__weakref__')
    def __init__(self, name, quals, align, type, coord=None):
        self.name = name
        self.quals = quals
        self.align = align
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Typename): return False
        if self.name != o.name: return False
        if self.quals != o.quals: return False
        if self.align != o.align: return False
        if self.type != o.type: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', 'quals', 'align', )

class UnaryOp(Node):
    __slots__ = ('op', 'expr', 'coord', '__weakref__')
    def __init__(self, op, expr, coord=None):
        self.op = op
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, UnaryOp): return False
        if self.op != o.op: return False
        if self.expr != o.expr: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('op', )

class Union(Node):
    __slots__ = ('name', 'decls', 'coord', '__weakref__')
    def __init__(self, name, decls, coord=None):
        self.name = name
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.decls or []):
            yield child

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Union): return False
        if self.name != o.name: return False
        if self.decls != o.decls: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('name', )

class While(Node):
    __slots__ = ('cond', 'stmt', 'coord', '__weakref__')
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.stmt is not None:
            yield self.stmt

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, While): return False
        if self.cond != o.cond: return False
        if self.stmt != o.stmt: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ()

class Pragma(Node):
    __slots__ = ('string', 'coord', '__weakref__')
    def __init__(self, string, coord=None):
        self.string = string
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    def __eq__(self, o):
        if not o: return False
        if not isinstance(o, Pragma): return False
        if self.string != o.string: return False
        return True

    def __ne__(self, o):
        return not self == o

    attr_names = ('string', )

