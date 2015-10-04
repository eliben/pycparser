#-----------------------------------------------------------------
# plyparser.py
#
# PLYParser class and other utilites for simplifying programming
# parsers with PLY
#
# Copyright (C) 2008-2015, Eli Bendersky
# License: BSD
#-----------------------------------------------------------------


class Coord(object):
    """ Coordinates of a syntactic element. Consists of:
            - File name
            - Line number
            - Column number, for the Lexer
            - End line number
            - End column number
    """
    __slots__ = ('file', 'line', 'column', 'end_line', 'end_column', '__weakref__')
    def __init__(self, file, line, column, end_line, end_column):
        self.file = file
        self.line = line
        self.column = column
        self.end_line = end_line
        self.end_column = end_column

    def __str__(self):
        str = "%s:%s:%s-%s:%s" % (self.file, self.line, self.column,
            self.end_line, self.end_column)
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

    def _coord(self, lineno, column=None, end_line=None, end_column=None):
        return Coord(
                file=self.clex.filename,
                line=lineno,
                column=column,
                end_line=end_line,
                end_column=end_column)

    def _parse_error(self, msg, coord):
        raise ParseError("%s: %s" % (coord, msg))
