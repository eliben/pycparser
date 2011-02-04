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
# Copyright (C) 2008-2010, Eli Bendersky
# License: LGPL
#-----------------------------------------------------------------


import sys


class Node(object):
    """ Abstract base class for AST nodes.
    """
    def children(self):
        """ A sequence of all children that are Nodes
        """
        pass

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        """ Pretty print the Node and all its attributes and
            children (recursively) to a buffer.
            
            file:   
                Open IO buffer into which the Node is printed.
            
            offset: 
                Initial offset (amount of leading spaces) 
            
            attrnames:
                True if you want to see the attribute names in
                name=value pairs. False to only see the values.
            
            showcoord:
                Do you want the coordinates of each Node to be
                displayed.
        """
        lead = ' ' * offset
        buf.write(lead + self.__class__.__name__+': ')

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

        for c in self.children():
            c.show(buf, offset + 2, attrnames, showcoord)


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
    def visit(self, node):
        """ Visit a node. 
        """
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)
        
    def generic_visit(self, node):
        """ Called if no explicit visitor function exists for a 
            node. Implements preorder visiting of the node.
        """
        for c in node.children():
            self.visit(c)


class ArrayDecl(Node):
    def __init__(self, type, dim, coord=None):
        self.type = type
        self.dim = dim
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(self.type)
        if self.dim is not None: nodelist.append(self.dim)
        return tuple(nodelist)

    attr_names = ()

class ArrayRef(Node):
    def __init__(self, name, subscript, coord=None):
        self.name = name
        self.subscript = subscript
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(self.name)
        if self.subscript is not None: nodelist.append(self.subscript)
        return tuple(nodelist)

    attr_names = ()

class Assignment(Node):
    def __init__(self, op, lvalue, rvalue, coord=None):
        self.op = op
        self.lvalue = lvalue
        self.rvalue = rvalue
        self.coord = coord

    def children(self):
        nodelist = []
        if self.lvalue is not None: nodelist.append(self.lvalue)
        if self.rvalue is not None: nodelist.append(self.rvalue)
        return tuple(nodelist)

    attr_names = ('op',)

class BinaryOp(Node):
    def __init__(self, op, left, right, coord=None):
        self.op = op
        self.left = left
        self.right = right
        self.coord = coord

    def children(self):
        nodelist = []
        if self.left is not None: nodelist.append(self.left)
        if self.right is not None: nodelist.append(self.right)
        return tuple(nodelist)

    attr_names = ('op',)

class Break(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class Case(Node):
    def __init__(self, expr, stmt, coord=None):
        self.expr = expr
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(self.expr)
        if self.stmt is not None: nodelist.append(self.stmt)
        return tuple(nodelist)

    attr_names = ()

class Cast(Node):
    def __init__(self, to_type, expr, coord=None):
        self.to_type = to_type
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.to_type is not None: nodelist.append(self.to_type)
        if self.expr is not None: nodelist.append(self.expr)
        return tuple(nodelist)

    attr_names = ()

class Compound(Node):
    def __init__(self, block_items, coord=None):
        self.block_items = block_items
        self.coord = coord

    def children(self):
        nodelist = []
        if self.block_items is not None: nodelist.extend(self.block_items)
        return tuple(nodelist)

    attr_names = ()

class CompoundLiteral(Node):
    def __init__(self, type, init, coord=None):
        self.type = type
        self.init = init
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(self.type)
        if self.init is not None: nodelist.append(self.init)
        return tuple(nodelist)

    attr_names = ()

class Constant(Node):
    def __init__(self, type, value, coord=None):
        self.type = type
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('type','value',)

class Continue(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class Decl(Node):
    def __init__(self, name, quals, storage, funcspec, type, init, bitsize, coord=None):
        self.name = name
        self.quals = quals
        self.storage = storage
        self.funcspec = funcspec
        self.type = type
        self.init = init
        self.bitsize = bitsize
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(self.type)
        if self.init is not None: nodelist.append(self.init)
        if self.bitsize is not None: nodelist.append(self.bitsize)
        return tuple(nodelist)

    attr_names = ('name','quals','storage','funcspec',)

class DeclList(Node):
    def __init__(self, decls, coord=None):
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        if self.decls is not None: nodelist.extend(self.decls)
        return tuple(nodelist)

    attr_names = ()

class Default(Node):
    def __init__(self, stmt, coord=None):
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.stmt is not None: nodelist.append(self.stmt)
        return tuple(nodelist)

    attr_names = ()

class DoWhile(Node):
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(self.cond)
        if self.stmt is not None: nodelist.append(self.stmt)
        return tuple(nodelist)

    attr_names = ()

class EllipsisParam(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class Enum(Node):
    def __init__(self, name, values, coord=None):
        self.name = name
        self.values = values
        self.coord = coord

    def children(self):
        nodelist = []
        if self.values is not None: nodelist.append(self.values)
        return tuple(nodelist)

    attr_names = ('name',)

class Enumerator(Node):
    def __init__(self, name, value, coord=None):
        self.name = name
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        if self.value is not None: nodelist.append(self.value)
        return tuple(nodelist)

    attr_names = ('name',)

class EnumeratorList(Node):
    def __init__(self, enumerators, coord=None):
        self.enumerators = enumerators
        self.coord = coord

    def children(self):
        nodelist = []
        if self.enumerators is not None: nodelist.extend(self.enumerators)
        return tuple(nodelist)

    attr_names = ()

class ExprList(Node):
    def __init__(self, exprs, coord=None):
        self.exprs = exprs
        self.coord = coord

    def children(self):
        nodelist = []
        if self.exprs is not None: nodelist.extend(self.exprs)
        return tuple(nodelist)

    attr_names = ()

class FileAST(Node):
    def __init__(self, ext, coord=None):
        self.ext = ext
        self.coord = coord

    def children(self):
        nodelist = []
        if self.ext is not None: nodelist.extend(self.ext)
        return tuple(nodelist)

    attr_names = ()

class For(Node):
    def __init__(self, init, cond, next, stmt, coord=None):
        self.init = init
        self.cond = cond
        self.next = next
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.init is not None: nodelist.append(self.init)
        if self.cond is not None: nodelist.append(self.cond)
        if self.next is not None: nodelist.append(self.next)
        if self.stmt is not None: nodelist.append(self.stmt)
        return tuple(nodelist)

    attr_names = ()

class FuncCall(Node):
    def __init__(self, name, args, coord=None):
        self.name = name
        self.args = args
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(self.name)
        if self.args is not None: nodelist.append(self.args)
        return tuple(nodelist)

    attr_names = ()

class FuncDecl(Node):
    def __init__(self, args, type, coord=None):
        self.args = args
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.args is not None: nodelist.append(self.args)
        if self.type is not None: nodelist.append(self.type)
        return tuple(nodelist)

    attr_names = ()

class FuncDef(Node):
    def __init__(self, decl, param_decls, body, coord=None):
        self.decl = decl
        self.param_decls = param_decls
        self.body = body
        self.coord = coord

    def children(self):
        nodelist = []
        if self.decl is not None: nodelist.append(self.decl)
        if self.body is not None: nodelist.append(self.body)
        if self.param_decls is not None: nodelist.extend(self.param_decls)
        return tuple(nodelist)

    attr_names = ()

class Goto(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('name',)

class ID(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('name',)

class IdentifierType(Node):
    def __init__(self, names, coord=None):
        self.names = names
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('names',)

class If(Node):
    def __init__(self, cond, iftrue, iffalse, coord=None):
        self.cond = cond
        self.iftrue = iftrue
        self.iffalse = iffalse
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(self.cond)
        if self.iftrue is not None: nodelist.append(self.iftrue)
        if self.iffalse is not None: nodelist.append(self.iffalse)
        return tuple(nodelist)

    attr_names = ()

class Label(Node):
    def __init__(self, name, stmt, coord=None):
        self.name = name
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.stmt is not None: nodelist.append(self.stmt)
        return tuple(nodelist)

    attr_names = ('name',)

class NamedInitializer(Node):
    def __init__(self, name, expr, coord=None):
        self.name = name
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(self.expr)
        if self.name is not None: nodelist.extend(self.name)
        return tuple(nodelist)

    attr_names = ()

class ParamList(Node):
    def __init__(self, params, coord=None):
        self.params = params
        self.coord = coord

    def children(self):
        nodelist = []
        if self.params is not None: nodelist.extend(self.params)
        return tuple(nodelist)

    attr_names = ()

class PtrDecl(Node):
    def __init__(self, quals, type, coord=None):
        self.quals = quals
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(self.type)
        return tuple(nodelist)

    attr_names = ('quals',)

class Return(Node):
    def __init__(self, expr, coord=None):
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(self.expr)
        return tuple(nodelist)

    attr_names = ()

class Struct(Node):
    def __init__(self, name, decls, coord=None):
        self.name = name
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        if self.decls is not None: nodelist.extend(self.decls)
        return tuple(nodelist)

    attr_names = ('name',)

class StructRef(Node):
    def __init__(self, name, type, field, coord=None):
        self.name = name
        self.type = type
        self.field = field
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(self.name)
        if self.field is not None: nodelist.append(self.field)
        return tuple(nodelist)

    attr_names = ('type',)

class Switch(Node):
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(self.cond)
        if self.stmt is not None: nodelist.append(self.stmt)
        return tuple(nodelist)

    attr_names = ()

class TernaryOp(Node):
    def __init__(self, cond, iftrue, iffalse, coord=None):
        self.cond = cond
        self.iftrue = iftrue
        self.iffalse = iffalse
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(self.cond)
        if self.iftrue is not None: nodelist.append(self.iftrue)
        if self.iffalse is not None: nodelist.append(self.iffalse)
        return tuple(nodelist)

    attr_names = ()

class TypeDecl(Node):
    def __init__(self, declname, quals, type, coord=None):
        self.declname = declname
        self.quals = quals
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(self.type)
        return tuple(nodelist)

    attr_names = ('declname','quals',)

class Typedef(Node):
    def __init__(self, name, quals, storage, type, coord=None):
        self.name = name
        self.quals = quals
        self.storage = storage
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(self.type)
        return tuple(nodelist)

    attr_names = ('name','quals','storage',)

class Typename(Node):
    def __init__(self, quals, type, coord=None):
        self.quals = quals
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(self.type)
        return tuple(nodelist)

    attr_names = ('quals',)

class UnaryOp(Node):
    def __init__(self, op, expr, coord=None):
        self.op = op
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(self.expr)
        return tuple(nodelist)

    attr_names = ('op',)

class Union(Node):
    def __init__(self, name, decls, coord=None):
        self.name = name
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        if self.decls is not None: nodelist.extend(self.decls)
        return tuple(nodelist)

    attr_names = ('name',)

class While(Node):
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(self.cond)
        if self.stmt is not None: nodelist.append(self.stmt)
        return tuple(nodelist)

    attr_names = ()

