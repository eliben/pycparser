import sys
import re

def SubNodeClass(name, attributes=[], children=[]):
    def init(self, *args, **kargs):
        coord = None
        if 'coord' in kargs.keys() :
            coord = kargs['coord']
        elif len(args) == (len(attributes) + 
                           len(children) + 
                           1):
            coord = args[-1]
        _attributes = {}
        for attribute in attributes :
            try :
                _attributes[attribute] = kargs[attribute]
            except KeyError:
                _attributes[attribute] = args[attributes.index(attribute)]
        _children = {}
        for child in children :
            try :
                _children[child] = kargs[child]
            except KeyError:
                _children[child] = args[len(attributes)+children.index(child)]
        Node.__init__(self,
                      coord,
                      attributes=_attributes,
                      children=_children)
    
    init.func_doc = ('The arguements of the function can be path through the keywords ' +
                     'name or the order of appearance of them :\n' + ' ' * 4 +
                     ('\n' + ' ' * 4).join(attributes+children+['coord']))
    
    return type(name,
                (Node,),
                {'__init__':init})

class Node(object):
    """ Abstract base class for AST nodes.
    """
    __offset = 4
    __show_coord = True
    
    def __init__(self, coord, attributes={}, children={}, with_value=True):
        self.coord = coord
        self.with_value = with_value

        if (not isinstance(attributes, dict) or
            not isinstance(children, dict)):
            raise TypeError('attributes and children have to be '+repr(type(dict)))
        self.attributes = attributes
        self.children = children

    def __getattr__(self, name):
        if name in self.attributes.keys():
            return self.attributes[name]
        elif name in self.children.keys():
            return self.children[name]
        else:
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if not (name in ['attributes',
                         'children',
                         'coord',
                         'with_value']) :
            try  :
                self.attributes[name] = value
            except KeyError, e:
                try :
                    self.children[name] = value
                except KeyError, e:
                    pass
        object.__setattr__(self, name, value)

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        buf.write(repr(self))
    
    def __repr_header(self):
        s = type(self).__name__ 
        if type(self).__show_coord:
            s += ' (' + self.__repr_coord() + ')'
        return s
    
    def __repr_attributes(self):
        s = ''
        entries = []
        reporter = lambda k,v : '%s' % (k)
        line_prefix = '\n' + len(self.__repr_header() + ' : (') * ' '
        if self.with_value :
            reporter = lambda k,v : '%s = %s' % (k,repr(v))
        for k, v in self.attributes.items():
            entries += [reporter(k,v)]
        return line_prefix.join(entries)
    
    def __repr_coord(self):
        return 'at %s' % self.coord
    
    def __repr_children(self):
        children_keys = self.children.keys()
        children_keys.sort()
        reprs = []
        for name in children_keys:
            s = ''
            value = self.children[name]
            child_head = type(self).__offset * ' ' + '* '+ name + ' : '
            s += child_head
            line_prefix = '\n' + ' ' * len(child_head)
            repr_value = repr(value)
            if isinstance(value, list) :
                repr_value = '['+'\n'.join('- %s' % repr(v) for v in value)+']'
            s += re.sub('\n', line_prefix, repr_value)
            reprs += [s]
        return '\n'.join(['']+reprs+[''])
    
    def __repr__(self):
        s = self.__repr_header()
        if len(self.attributes):
            s += ' : (' + self.__repr_attributes() + ')' 
        if len(self.children):
            s += self.__repr_children()
        return s

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
        for k in node.children:
            self.visit(node.children[k])


