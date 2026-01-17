#------------------------------------------------------------------------------
# pycparser: c_lexer.py
#
# CLexer class: lexer for the C language
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#------------------------------------------------------------------------------
import re

##
## Reserved keywords
##
keywords = (
    'AUTO', 'BREAK', 'CASE', 'CHAR', 'CONST',
    'CONTINUE', 'DEFAULT', 'DO', 'DOUBLE', 'ELSE', 'ENUM', 'EXTERN',
    'FLOAT', 'FOR', 'GOTO', 'IF', 'INLINE', 'INT', 'LONG',
    'REGISTER', 'OFFSETOF',
    'RESTRICT', 'RETURN', 'SHORT', 'SIGNED', 'SIZEOF', 'STATIC', 'STRUCT',
    'SWITCH', 'TYPEDEF', 'UNION', 'UNSIGNED', 'VOID',
    'VOLATILE', 'WHILE', '__INT128',
)

keywords_new = (
    '_BOOL', '_COMPLEX',
    '_NORETURN', '_THREAD_LOCAL', '_STATIC_ASSERT',
    '_ATOMIC', '_ALIGNOF', '_ALIGNAS',
    '_PRAGMA',
)

keyword_map = {}

for keyword in keywords:
    keyword_map[keyword.lower()] = keyword

for keyword in keywords_new:
    keyword_map[keyword[:2].upper() + keyword[2:].lower()] = keyword

##
## All the tokens recognized by the lexer
##
tokens = keywords + keywords_new + (
    # Identifiers
    'ID',

    # Type identifiers (identifiers previously defined as
    # types with typedef)
    'TYPEID',

    # constants
    'INT_CONST_DEC', 'INT_CONST_OCT', 'INT_CONST_HEX', 'INT_CONST_BIN', 'INT_CONST_CHAR',
    'FLOAT_CONST', 'HEX_FLOAT_CONST',
    'CHAR_CONST',
    'WCHAR_CONST',
    'U8CHAR_CONST',
    'U16CHAR_CONST',
    'U32CHAR_CONST',

    # String literals
    'STRING_LITERAL',
    'WSTRING_LITERAL',
    'U8STRING_LITERAL',
    'U16STRING_LITERAL',
    'U32STRING_LITERAL',

    # Operators
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'OR', 'AND', 'NOT', 'XOR', 'LSHIFT', 'RSHIFT',
    'LOR', 'LAND', 'LNOT',
    'LT', 'LE', 'GT', 'GE', 'EQ', 'NE',

    # Assignment
    'EQUALS', 'TIMESEQUAL', 'DIVEQUAL', 'MODEQUAL',
    'PLUSEQUAL', 'MINUSEQUAL',
    'LSHIFTEQUAL','RSHIFTEQUAL', 'ANDEQUAL', 'XOREQUAL',
    'OREQUAL',

    # Increment/decrement
    'PLUSPLUS', 'MINUSMINUS',

    # Structure dereference (->)
    'ARROW',

    # Conditional operator (?)
    'CONDOP',

    # Delimiters
    'LPAREN', 'RPAREN',         # ( )
    'LBRACKET', 'RBRACKET',     # [ ]
    'LBRACE', 'RBRACE',         # { }
    'COMMA', 'PERIOD',          # . ,
    'SEMI', 'COLON',            # ; :

    # Ellipsis (...)
    'ELLIPSIS',

    # pre-processor
    'PPHASH',       # '#'
    'PPPRAGMA',     # 'pragma'
    'PPPRAGMASTR',
)

##
## Regexes for use in tokens
##
##

# valid C identifiers (K&R2: A.2.3), plus '$' (supported by some compilers)
identifier = r'[a-zA-Z_$][0-9a-zA-Z_$]*'

hex_prefix = '0[xX]'
hex_digits = '[0-9a-fA-F]+'
bin_prefix = '0[bB]'
bin_digits = '[01]+'

# integer constants (K&R2: A.2.5.1)
integer_suffix_opt = r'(([uU]ll)|([uU]LL)|(ll[uU]?)|(LL[uU]?)|([uU][lL])|([lL][uU]?)|[uU])?'
decimal_constant = '(0'+integer_suffix_opt+')|([1-9][0-9]*'+integer_suffix_opt+')'
octal_constant = '0[0-7]*'+integer_suffix_opt
hex_constant = hex_prefix+hex_digits+integer_suffix_opt
bin_constant = bin_prefix+bin_digits+integer_suffix_opt

bad_octal_constant = '0[0-7]*[89]'

# comments are not supported
unsupported_c_style_comment = r'\/\*'
unsupported_cxx_style_comment = r'\/\/'

# character constants (K&R2: A.2.5.2)
# Note: a-zA-Z and '.-~^_!=&;,' are allowed as escape chars to support #line
# directives with Windows paths as filenames (..\..\dir\file)
# For the same reason, decimal_escape allows all digit sequences. We want to
# parse all correct code, even if it means to sometimes parse incorrect
# code.
#
# The original regexes were taken verbatim from the C syntax definition,
# and were later modified to avoid worst-case exponential running time.
#
#   simple_escape = r"""([a-zA-Z._~!=&\^\-\\?'"])"""
#   decimal_escape = r"""(\d+)"""
#   hex_escape = r"""(x[0-9a-fA-F]+)"""
#   bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-7])"""
#
# The following modifications were made to avoid the ambiguity that allowed backtracking:
# (https://github.com/eliben/pycparser/issues/61)
#
# - \x was removed from simple_escape, unless it was not followed by a hex digit, to avoid ambiguity with hex_escape.
# - hex_escape allows one or more hex characters, but requires that the next character(if any) is not hex
# - decimal_escape allows one or more decimal characters, but requires that the next character(if any) is not a decimal
# - bad_escape does not allow any decimals (8-9), to avoid conflicting with the permissive decimal_escape.
#
# Without this change, python's `re` module would recursively try parsing each ambiguous escape sequence in multiple ways.
# e.g. `\123` could be parsed as `\1`+`23`, `\12`+`3`, and `\123`.

simple_escape = r"""([a-wyzA-Z._~!=&\^\-\\?'"]|x(?![0-9a-fA-F]))"""
decimal_escape = r"""(\d+)(?!\d)"""
hex_escape = r"""(x[0-9a-fA-F]+)(?![0-9a-fA-F])"""
bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-9])"""

escape_sequence = r"""(\\("""+simple_escape+'|'+decimal_escape+'|'+hex_escape+'))'

# This complicated regex with lookahead might be slow for strings, so because all of the valid escapes (including \x) allowed
# 0 or more non-escaped characters after the first character, simple_escape+decimal_escape+hex_escape got simplified to

escape_sequence_start_in_string = r"""(\\[0-9a-zA-Z._~!=&\^\-\\?'"])"""

cconst_char = r"""([^'\\\n]|"""+escape_sequence+')'
char_const = "'"+cconst_char+"'"
wchar_const = 'L'+char_const
u8char_const = 'u8'+char_const
u16char_const = 'u'+char_const
u32char_const = 'U'+char_const
multicharacter_constant = "'"+cconst_char+"{2,4}'"
unmatched_quote = "('"+cconst_char+"*\\n)|('"+cconst_char+"*$)"
bad_char_const = r"""('"""+cconst_char+"""[^'\n]+')|('')|('"""+bad_escape+r"""[^'\n]*')"""

# string literals (K&R2: A.2.6)
string_char = r"""([^"\\\n]|"""+escape_sequence_start_in_string+')'
string_literal = '"'+string_char+'*"'
wstring_literal = 'L'+string_literal
u8string_literal = 'u8'+string_literal
u16string_literal = 'u'+string_literal
u32string_literal = 'U'+string_literal
bad_string_literal = '"'+string_char+'*'+bad_escape+string_char+'*"'

# floating constants (K&R2: A.2.5.3)
exponent_part = r"""([eE][-+]?[0-9]+)"""
fractional_constant = r"""([0-9]*\.[0-9]+)|([0-9]+\.)"""
floating_constant = '(((('+fractional_constant+')'+exponent_part+'?)|([0-9]+'+exponent_part+'))[FfLl]?)'
binary_exponent_part = r'''([pP][+-]?[0-9]+)'''
hex_fractional_constant = '((('+hex_digits+r""")?\."""+hex_digits+')|('+hex_digits+r"""\.))"""
hex_floating_constant = '('+hex_prefix+'('+hex_digits+'|'+hex_fractional_constant+')'+binary_exponent_part+'[FfLl]?)'


class _Token(object):
    __slots__ = ('type', 'value', 'lineno', 'lexpos', 'lexer')

    def __init__(self, typ, value, lineno, lexpos):
        self.type = typ
        self.value = value
        self.lineno = lineno
        self.lexpos = lexpos
        self.lexer = None


class CLexer(object):
    """A standalone lexer for C that doesn't rely on PLY."""
    keywords = keywords
    keywords_new = keywords_new
    keyword_map = keyword_map
    tokens = tokens

    def __init__(self, error_func, on_lbrace_func, on_rbrace_func,
                 type_lookup_func):
        self.error_func = error_func
        self.on_lbrace_func = on_lbrace_func
        self.on_rbrace_func = on_rbrace_func
        self.type_lookup_func = type_lookup_func
        self.filename = ''
        self.last_token = None
        self.lineno = 1
        self.lexer = self
        self._lexdata = ''
        self._pos = 0
        self._state = 'INITIAL'
        self._pp_line = None
        self._pp_filename = None
        self._pppragma_seen = False

        self.line_pattern = re.compile(r'([ \t]*line\W)|([ \t]*\d+)')
        self.pragma_pattern = re.compile(r'[ \t]*pragma\W')

        self._regex_rules = []
        self._fixed_tokens = []

    def build(self, **kwargs):
        if self._regex_rules:
            return
        self._compile_rules()

    def reset_lineno(self):
        self.lineno = 1

    def input(self, text):
        self._lexdata = text
        self._pos = 0
        self._state = 'INITIAL'
        self._pp_line = None
        self._pp_filename = None
        self._pppragma_seen = False
        self.last_token = None

    def token(self):
        text = self._lexdata
        n = len(text)

        while self._pos < n:
            if self._state == 'ppline':
                if self._handle_ppline():
                    continue
            elif self._state == 'pppragma':
                tok = self._handle_pppragma()
                if tok is None:
                    continue
                self.last_token = tok
                return tok

            if self._pos >= n:
                break

            ch = text[self._pos]
            if ch == ' ' or ch == '\t':
                self._pos += 1
                continue
            if ch == '\n':
                self.lineno += 1
                self._pos += 1
                continue
            if ch == '#':
                if self.line_pattern.match(text, self._pos + 1):
                    self._state = 'ppline'
                    self._pp_line = None
                    self._pp_filename = None
                    self._pos += 1
                    continue
                if self.pragma_pattern.match(text, self._pos + 1):
                    self._state = 'pppragma'
                    self._pppragma_seen = False
                    self._pos += 1
                    continue
                tok = self._make_token('PPHASH', '#', self._pos)
                self._pos += 1
                self.last_token = tok
                return tok

            tok = self._match_token()
            if tok is None:
                msg = 'Illegal character %s' % repr(text[self._pos])
                self._error(msg, self._pos)
                self._pos += 1
                continue
            if tok is False:
                continue

            self.last_token = tok
            return tok

        self.last_token = None
        return None

    def find_tok_column(self, token):
        last_cr = self._lexdata.rfind('\n', 0, token.lexpos)
        return token.lexpos - last_cr

    @property
    def lexpos(self):
        return self._pos

    @lexpos.setter
    def lexpos(self, value):
        self._pos = value

    @property
    def lexdata(self):
        return self._lexdata

    @lexdata.setter
    def lexdata(self, value):
        self._lexdata = value

    def _compile_rules(self):
        def rx(pattern):
            return re.compile(pattern)

        self._regex_rules = [
            ('UNSUPPORTED_C_STYLE_COMMENT', rx(unsupported_c_style_comment),
             'error', "Comments are not supported, see https://github.com/eliben/pycparser#3using."),
            ('UNSUPPORTED_CXX_STYLE_COMMENT', rx(unsupported_cxx_style_comment),
             'error', "Comments are not supported, see https://github.com/eliben/pycparser#3using."),
            ('BAD_STRING_LITERAL', rx(bad_string_literal),
             'error', "String contains invalid escape code"),
            ('WSTRING_LITERAL', rx(wstring_literal), 'token', None),
            ('U8STRING_LITERAL', rx(u8string_literal), 'token', None),
            ('U16STRING_LITERAL', rx(u16string_literal), 'token', None),
            ('U32STRING_LITERAL', rx(u32string_literal), 'token', None),
            ('STRING_LITERAL', rx(string_literal), 'token', None),
            ('HEX_FLOAT_CONST', rx(hex_floating_constant), 'token', None),
            ('FLOAT_CONST', rx(floating_constant), 'token', None),
            ('INT_CONST_HEX', rx(hex_constant), 'token', None),
            ('INT_CONST_BIN', rx(bin_constant), 'token', None),
            ('BAD_CONST_OCT', rx(bad_octal_constant),
             'error', "Invalid octal constant"),
            ('INT_CONST_OCT', rx(octal_constant), 'token', None),
            ('INT_CONST_DEC', rx(decimal_constant), 'token', None),
            ('INT_CONST_CHAR', rx(multicharacter_constant), 'token', None),
            ('CHAR_CONST', rx(char_const), 'token', None),
            ('WCHAR_CONST', rx(wchar_const), 'token', None),
            ('U8CHAR_CONST', rx(u8char_const), 'token', None),
            ('U16CHAR_CONST', rx(u16char_const), 'token', None),
            ('U32CHAR_CONST', rx(u32char_const), 'token', None),
            ('UNMATCHED_QUOTE', rx(unmatched_quote),
             'error', "Unmatched '"),
            ('BAD_CHAR_CONST', rx(bad_char_const),
             'error', None),
            ('ID', rx(identifier), 'id', None),
        ]

        self._fixed_tokens = [
            ('ELLIPSIS', '...'),
            ('LSHIFTEQUAL', '<<='),
            ('RSHIFTEQUAL', '>>='),
            ('PLUSPLUS', '++'),
            ('MINUSMINUS', '--'),
            ('ARROW', '->'),
            ('LAND', '&&'),
            ('LOR', '||'),
            ('LSHIFT', '<<'),
            ('RSHIFT', '>>'),
            ('LE', '<='),
            ('GE', '>='),
            ('EQ', '=='),
            ('NE', '!='),
            ('TIMESEQUAL', '*='),
            ('DIVEQUAL', '/='),
            ('MODEQUAL', '%='),
            ('PLUSEQUAL', '+='),
            ('MINUSEQUAL', '-='),
            ('ANDEQUAL', '&='),
            ('OREQUAL', '|='),
            ('XOREQUAL', '^='),
            ('EQUALS', '='),
            ('PLUS', '+'),
            ('MINUS', '-'),
            ('TIMES', '*'),
            ('DIVIDE', '/'),
            ('MOD', '%'),
            ('OR', '|'),
            ('AND', '&'),
            ('NOT', '~'),
            ('XOR', '^'),
            ('LNOT', '!'),
            ('LT', '<'),
            ('GT', '>'),
            ('CONDOP', '?'),
            ('LPAREN', '('),
            ('RPAREN', ')'),
            ('LBRACKET', '['),
            ('RBRACKET', ']'),
            ('LBRACE', '{'),
            ('RBRACE', '}'),
            ('COMMA', ','),
            ('PERIOD', '.'),
            ('SEMI', ';'),
            ('COLON', ':'),
        ]

    def _match_token(self):
        text = self._lexdata
        pos = self._pos
        best = None

        for tok_type, regex, action, msg in self._regex_rules:
            m = regex.match(text, pos)
            if not m:
                continue
            value = m.group(0)
            length = len(value)
            if best is None or length > best[0]:
                best = (length, tok_type, value, action, msg)

        for tok_type, literal in self._fixed_tokens:
            if text.startswith(literal, pos):
                length = len(literal)
                if best is None or length > best[0]:
                    best = (length, tok_type, literal, 'token', None)

        if best is None:
            return None

        length, tok_type, value, action, msg = best
        if action == 'error':
            if tok_type == 'BAD_CHAR_CONST':
                msg = "Invalid char constant %s" % value
            self._error(msg, pos)
            self._pos += max(1, length)
            return False
        if action == 'id':
            tok_type = self.keyword_map.get(value, 'ID')
            if tok_type == 'ID' and self.type_lookup_func(value):
                tok_type = 'TYPEID'

        tok = self._make_token(tok_type, value, pos)
        self._pos += length

        if tok.type == 'LBRACE':
            self.on_lbrace_func()
        elif tok.type == 'RBRACE':
            self.on_rbrace_func()

        return tok

    def _make_token(self, tok_type, value, pos):
        tok = _Token(tok_type, value, self.lineno, pos)
        tok.lexer = self
        return tok

    def _error(self, msg, pos):
        line, column = self._make_tok_location(pos)
        self.error_func(msg, line, column)

    def _make_tok_location(self, pos):
        last_cr = self._lexdata.rfind('\n', 0, pos)
        column = pos - last_cr
        return (self.lineno, column)

    def _handle_ppline(self):
        text = self._lexdata
        n = len(text)
        if self._pos >= n:
            return True
        ch = text[self._pos]
        if ch == '\n':
            if self._pp_line is None:
                self._error('line number missing in #line', self._pos)
            else:
                self.lineno = int(self._pp_line)
                if self._pp_filename is not None:
                    self.filename = self._pp_filename
            self._pos += 1
            self._state = 'INITIAL'
            return True
        if ch == ' ' or ch == '\t':
            self._pos += 1
            return True
        if text.startswith('line', self._pos):
            self._pos += 4
            return True

        m = re.match(decimal_constant, text[self._pos:])
        if m:
            if self._pp_line is None:
                self._pp_line = m.group(0)
            self._pos += len(m.group(0))
            return True

        m = re.match(string_literal, text[self._pos:])
        if m:
            if self._pp_line is None:
                self._error('filename before line number in #line', self._pos)
            else:
                self._pp_filename = m.group(0).lstrip('"').rstrip('"')
            self._pos += len(m.group(0))
            return True

        self._error('invalid #line directive', self._pos)
        self._pos += 1
        return True

    def _handle_pppragma(self):
        text = self._lexdata
        n = len(text)
        if self._pos >= n:
            self._state = 'INITIAL'
            return None

        ch = text[self._pos]
        if ch == '\n':
            self.lineno += 1
            self._pos += 1
            self._state = 'INITIAL'
            return None
        if ch == ' ' or ch == '\t':
            self._pos += 1
            return None

        if not self._pppragma_seen:
            if text.startswith('pragma', self._pos):
                tok = self._make_token('PPPRAGMA', 'pragma', self._pos)
                self._pos += len('pragma')
                self._pppragma_seen = True
                return tok
            self._error('invalid #pragma directive', self._pos)
            self._pos += 1
            return None

        start = self._pos
        while self._pos < n and text[self._pos] != '\n':
            self._pos += 1
        if self._pos == start:
            return None
        return self._make_token('PPPRAGMASTR', text[start:self._pos], start)
