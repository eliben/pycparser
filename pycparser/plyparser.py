#-----------------------------------------------------------------
# plyparser.py
#
# PLYParser class and other utilites for simplifying programming
# parsers with PLY
#
# Eli Bendersky [http://eli.thegreenplace.net]
# License: BSD
#-----------------------------------------------------------------


class Coord(object):
    """ Coordinates of a syntactic element. Consists of:
            - File name
            - Line number
            - (optional) column number, for the Lexer
    """
    __slots__ = ('file', 'line', 'column', '__weakref__')
    def __init__(self, file, line, column=None):
        self.file = file
        self.line = line
        self.column = column

    def __str__(self):
        str = "%s:%s" % (self.file, self.line)
        if self.column: str += ":%s" % self.column
        return str


class ParseError(Exception): pass


class PLYParser(object):
    def _create_opt_rule(self, rulename):
        """ Given a rule name, creates an optional ply.yacc rule
            for it. The name of the optional rule is
            <rulename>_opt
        """
        optname = rulename + '_opt'

        def optrule(self, p):
            p[0] = p[1]

        optrule.__doc__ = '%s : empty\n| %s' % (optname, rulename)
        optrule.__name__ = 'p_%s' % optname
        setattr(self.__class__, optrule.__name__, optrule)

    def _coord(self, lineno, column=None):
        return Coord(
                file=self.clex.filename,
                line=lineno,
                column=column)

    def _parse_error(self, msg, coord):
        raise ParseError("%s: %s" % (coord, msg))


def parameterized(*params):
    """ Decorator to create parameterized rules.

    Parameterized rule methods must be named starting with '_p_' and contain
    'XXX', and their docstrings may contain 'XXX' and 'YYY'. These will be
    replaced by the given parameter tuples. For example, ``_p_XXX_rule()`` with
    docstring 'XXX_rule  : YYY' when decorated with
    ``@parameterized(('id', 'ID'))`` produces ``p_id_rule()`` with the docstring
    'id_rule  : ID'. Using multiple tuples produces multiple rules.
    """
    def decorate(rule_func):
        rule_func._params = params
        return rule_func
    return decorate


def template(cls):
    for attr_name in dir(cls):
        if attr_name.startswith('_p_'):
            method = getattr(cls, attr_name)
            if hasattr(method, '_params'):
                _create_param_rules(cls, method)
    return cls


def _create_param_rules(cls, func):
    """ Creates ply.yacc rules based on a parameterized rule function """
    for xxx, yyy in func._params:
        def param_rule(self, p):
            func(self, p)

        param_rule.__doc__ = func.__doc__.replace('XXX', xxx).replace('YYY', yyy)
        param_rule.__name__ = func.__name__.replace('XXX', xxx)[1:]
        setattr(cls, param_rule.__name__, param_rule)
