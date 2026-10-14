import re
import sys
import unittest
from dataclasses import dataclass

sys.path.insert(0, "..")
from pycparser.c_lexer import CLexer, Token


def require_token(tok: Token | None) -> Token:
    # In tests we know token() should produce a token here; this helper asserts
    # that and narrows Optional[Token] to Token, avoiding repeated casts/guards.
    assert tok is not None
    return tok


def token_list(clex):
    return list(iter(clex.token, None))


def token_types(clex):
    return [i.type for i in token_list(clex)]


class TestCLexerNoErrors(unittest.TestCase):
    """Test lexing of strings that are not supposed to cause
    errors. Therefore, the error_func passed to the lexer
    raises an exception.
    """

    def error_func(self, msg, line, column):
        self.fail(msg)

    def on_lbrace_func(self):
        pass

    def on_rbrace_func(self):
        pass

    def type_lookup_func(self, typ):
        return typ.startswith("mytype")

    def setUp(self):
        self.clex = CLexer(
            self.error_func, lambda: None, lambda: None, self.type_lookup_func
        )

    def assertTokensTypes(self, str, types):
        self.clex.input(str)
        self.assertEqual(token_types(self.clex), types)

    def test_trivial_tokens(self):
        self.assertTokensTypes("1", ["INT_CONST_DEC"])
        self.assertTokensTypes("-", ["MINUS"])
        self.assertTokensTypes("volatile", ["VOLATILE"])
        self.assertTokensTypes("...", ["ELLIPSIS"])
        self.assertTokensTypes("++", ["PLUSPLUS"])
        self.assertTokensTypes("case int", ["CASE", "INT"])
        self.assertTokensTypes("caseint", ["ID"])
        self.assertTokensTypes("$dollar cent$", ["ID", "ID"])
        self.assertTokensTypes("i ^= 1;", ["ID", "XOREQUAL", "INT_CONST_DEC", "SEMI"])

    def test_token_filenames(self):
        self.clex.input(
            'first\n#line 7 "header.h"\n#pragma once\n#\n+ last\n# 1 "main.c" 2\n0\n',
            filename="initial.c",
        )
        tokens = token_list(self.clex)
        self.assertEqual(self.clex.filename, "main.c")
        self.assertEqual(
            [(t.type, t.filename, t.lineno, t.column) for t in tokens],
            [
                ("ID", "initial.c", 1, 1),
                ("PPPRAGMA", "header.h", 7, 2),
                ("PPPRAGMASTR", "header.h", 7, 9),
                ("PPHASH", "header.h", 8, 1),
                ("PLUS", "header.h", 9, 1),
                ("ID", "header.h", 9, 3),
                ("INT_CONST_OCT", "main.c", 1, 1),
            ],
        )

    def test_token_filename_reset(self):
        self.clex.input('one\n#line 10\ntwo\n#line 20 ""\nthree', "first.c")
        tokens = token_list(self.clex)
        self.assertEqual(
            [(t.filename, t.lineno, t.column) for t in tokens],
            [("first.c", 1, 1), ("first.c", 10, 1), ("", 20, 1)],
        )
        self.clex.input("four")
        self.assertEqual(require_token(self.clex.token()).filename, "")
        self.assertEqual(tokens[0].filename, "first.c")
        self.assertEqual(tokens[0], Token("ID", "one", 1, 1))
        self.assertEqual(
            repr(tokens[0]), "Token(type='ID', value='one', lineno=1, column=1)"
        )

    def test_token_subclass_required_field(self):
        @dataclass
        class LexerToken(Token):
            lexpos: int

        token = LexerToken("ID", "value", 1, 1, 0)
        self.assertEqual(token.lexpos, 0)
        self.assertIsNone(token.filename)
        named_token = LexerToken("ID", "value", 1, 1, 0, filename="header.h")
        self.assertEqual(named_token.lexpos, 0)
        self.assertEqual(named_token.filename, "header.h")

    def test_id_typeid(self):
        self.assertTokensTypes("myt", ["ID"])
        self.assertTokensTypes("mytype", ["TYPEID"])
        self.assertTokensTypes("mytype6 var", ["TYPEID", "ID"])

    def test_integer_constants(self):
        self.assertTokensTypes("12", ["INT_CONST_DEC"])
        self.assertTokensTypes("12u", ["INT_CONST_DEC"])
        self.assertTokensTypes("12l", ["INT_CONST_DEC"])
        self.assertTokensTypes("199872Ul", ["INT_CONST_DEC"])
        self.assertTokensTypes("199872lU", ["INT_CONST_DEC"])
        self.assertTokensTypes("199872LL", ["INT_CONST_DEC"])
        self.assertTokensTypes("199872ull", ["INT_CONST_DEC"])
        self.assertTokensTypes("199872llu", ["INT_CONST_DEC"])
        self.assertTokensTypes("1009843200000uLL", ["INT_CONST_DEC"])
        self.assertTokensTypes("1009843200000LLu", ["INT_CONST_DEC"])

        self.assertTokensTypes("077", ["INT_CONST_OCT"])
        self.assertTokensTypes("0123456L", ["INT_CONST_OCT"])

        self.assertTokensTypes("0xf7", ["INT_CONST_HEX"])
        self.assertTokensTypes("0b110", ["INT_CONST_BIN"])
        self.assertTokensTypes("0x01202AAbbf7Ul", ["INT_CONST_HEX"])
        self.assertTokensTypes("'12'", ["INT_CONST_CHAR"])
        self.assertTokensTypes("'123'", ["INT_CONST_CHAR"])
        self.assertTokensTypes("'1AB4'", ["INT_CONST_CHAR"])
        self.assertTokensTypes(r"'1A\n4'", ["INT_CONST_CHAR"])

        # no 0 before x, so ID catches it
        self.assertTokensTypes("xf7", ["ID"])

        # - is MINUS, the rest a constnant
        self.assertTokensTypes("-1", ["MINUS", "INT_CONST_DEC"])

    def test_integer_digit_separators(self):
        self.assertTokensTypes("1'000'000", ["INT_CONST_DEC"])
        self.assertTokensTypes("0'7'7", ["INT_CONST_OCT"])
        self.assertTokensTypes("0xAB'CD", ["INT_CONST_HEX"])
        self.assertTokensTypes("0B1010'0101", ["INT_CONST_BIN"])
        self.assertTokensTypes("1'000uLL", ["INT_CONST_DEC"])
        self.assertTokensTypes("0XFF'FFwbU", ["INT_CONST_HEX"])

        self.clex.input("1'000+2'000\n0xAB'CD")
        self.assertEqual(
            token_list(self.clex),
            [
                Token("INT_CONST_DEC", "1'000", 1, 1),
                Token("PLUS", "+", 1, 6),
                Token("INT_CONST_DEC", "2'000", 1, 7),
                Token("INT_CONST_HEX", "0xAB'CD", 2, 1),
            ],
        )

    def test_floating_digit_separators(self):
        self.assertTokensTypes("1'234.56'78", ["FLOAT_CONST"])
        self.assertTokensTypes(".1'25", ["FLOAT_CONST"])
        self.assertTokensTypes("1'000.", ["FLOAT_CONST"])
        self.assertTokensTypes("1'2e+3'4", ["FLOAT_CONST"])
        self.assertTokensTypes("0'8.0", ["FLOAT_CONST"])
        self.assertTokensTypes("0xAB'CD.EF'01p+1'0", ["HEX_FLOAT_CONST"])
        self.assertTokensTypes("0x.A'Bp-1'0", ["HEX_FLOAT_CONST"])
        self.assertTokensTypes("0xA'B.p1'0", ["HEX_FLOAT_CONST"])
        self.assertTokensTypes("0xA'Bp1'0", ["HEX_FLOAT_CONST"])

        self.clex.input("1'2.3'4e-5'6DF")
        self.assertEqual(
            token_list(self.clex),
            [
                Token("FLOAT_CONST", "1'2.3'4e-5'6DF", 1, 1),
            ],
        )

    def test_digit_separators_and_quotes(self):
        self.clex.input("'1'2 1'2 \"1'2\"")
        self.assertEqual(
            token_list(self.clex),
            [
                Token("CHAR_CONST", "'1'", 1, 1),
                Token("INT_CONST_DEC", "2", 1, 4),
                Token("INT_CONST_DEC", "1'2", 1, 6),
                Token("STRING_LITERAL", '"1\'2"', 1, 10),
            ],
        )

    def test_line_directive_digit_separators(self):
        self.clex.input('#line 1\'000 "file.c"\nvalue')
        self.assertEqual(token_list(self.clex), [Token("ID", "value", 1000, 1)])
        self.assertEqual(self.clex.filename, "file.c")

        self.clex.input("#line 0'010\nvalue")
        self.assertEqual(token_list(self.clex), [Token("ID", "value", 10, 1)])

    def test_bitint_constants(self):
        # Numeric regexes are shared, so even the legacy lexer recognizes
        # these suffixes. The parser enforces C23.
        self.assertTokensTypes("42wb", ["INT_CONST_DEC"])
        self.assertTokensTypes("42WB", ["INT_CONST_DEC"])
        self.assertTokensTypes("42uwb", ["INT_CONST_DEC"])
        self.assertTokensTypes("42uWB", ["INT_CONST_DEC"])
        self.assertTokensTypes("42Uwb", ["INT_CONST_DEC"])
        self.assertTokensTypes("42UWB", ["INT_CONST_DEC"])
        self.assertTokensTypes("42wbu", ["INT_CONST_DEC"])
        self.assertTokensTypes("42wbU", ["INT_CONST_DEC"])
        self.assertTokensTypes("42WBu", ["INT_CONST_DEC"])
        self.assertTokensTypes("42WBU", ["INT_CONST_DEC"])
        self.assertTokensTypes("0wb", ["INT_CONST_OCT"])
        self.assertTokensTypes("077uwb", ["INT_CONST_OCT"])
        self.assertTokensTypes("0XffWB", ["INT_CONST_HEX"])
        self.assertTokensTypes("0b101wbu", ["INT_CONST_BIN"])

        self.clex.input("42wb+0xffUWB")
        self.assertEqual(
            token_list(self.clex),
            [
                Token("INT_CONST_DEC", "42wb", 1, 1),
                Token("PLUS", "+", 1, 5),
                Token("INT_CONST_HEX", "0xffUWB", 1, 6),
            ],
        )

    def test_special_names(self):
        self.assertTokensTypes("sizeof offsetof", ["SIZEOF", "OFFSETOF"])

    def test_new_keywords(self):
        self.assertTokensTypes("_Bool", ["_BOOL"])
        self.assertTokensTypes("_Atomic", ["_ATOMIC"])
        self.assertTokensTypes("_Alignas _Alignof", ["_ALIGNAS", "_ALIGNOF"])
        self.assertTokensTypes("_Generic", ["_GENERIC"])
        self.assertTokensTypes("_Generic_value _generic", ["ID", "ID"])

    def test_c23_keywords_and_typedef_lookup(self):
        source = (
            "bool alignas alignof static_assert thread_local true false nullptr "
            "constexpr typeof typeof_unqual _BitInt _Decimal32 _Decimal64 "
            "_Decimal128 _Imaginary bool_value True nullptr_t"
        )
        c23 = CLexer(
            self.error_func,
            lambda: None,
            lambda: None,
            lambda name: True,
            dialect="c23",
        )
        expected = [
            "_BOOL",
            "_ALIGNAS",
            "_ALIGNOF",
            "_STATIC_ASSERT",
            "_THREAD_LOCAL",
            "BOOL_CONST",
            "BOOL_CONST",
            "NULLPTR",
            "CONSTEXPR",
            "TYPEOF",
            "TYPEOF_UNQUAL",
            "_BITINT",
            "_DECIMAL32",
            "_DECIMAL64",
            "_DECIMAL128",
            "_IMAGINARY",
            "TYPEID",
            "TYPEID",
            "TYPEID",
        ]
        # input() must preserve the dialect, and selecting it must not affect
        # another lexer's keyword map.
        for _ in range(2):
            self.assertTokensTypes(source, ["ID"] * len(source.split()))
            c23.input(source)
            tokens = token_list(c23)
            self.assertEqual([tok.type for tok in tokens], expected)
            self.assertEqual([tok.value for tok in tokens], source.split())

    def test_invalid_dialect(self):
        with self.assertRaisesRegex(ValueError, "Unknown dialect"):
            CLexer(
                self.error_func,
                lambda: None,
                lambda: None,
                self.type_lookup_func,
                dialect="c99",  # ty: ignore[invalid-argument-type]
            )

    def test_floating_constants(self):
        self.assertTokensTypes("1.5f", ["FLOAT_CONST"])
        self.assertTokensTypes("01.5", ["FLOAT_CONST"])
        self.assertTokensTypes(".15L", ["FLOAT_CONST"])
        self.assertTokensTypes("0.", ["FLOAT_CONST"])

        # but just a period is a period
        self.assertTokensTypes(".", ["PERIOD"])

        self.assertTokensTypes("3.3e-3", ["FLOAT_CONST"])
        self.assertTokensTypes(".7e25L", ["FLOAT_CONST"])
        self.assertTokensTypes("6.e+125f", ["FLOAT_CONST"])
        self.assertTokensTypes("666e666", ["FLOAT_CONST"])
        self.assertTokensTypes("00666e+3", ["FLOAT_CONST"])

        # but this is a hex integer + 3
        self.assertTokensTypes("0x0666e+3", ["INT_CONST_HEX", "PLUS", "INT_CONST_DEC"])

    def test_c23_decimal_floating_constants(self):
        c23 = CLexer(
            self.error_func,
            lambda: None,
            lambda: None,
            self.type_lookup_func,
            dialect="c23",
        )
        c23.input("1.25df\n2.50dd\n.3dl\n4e+2DF\n5e-1DD\n6.DL")
        self.assertEqual(
            token_list(c23),
            [
                Token("FLOAT_CONST", "1.25df", 1, 1),
                Token("FLOAT_CONST", "2.50dd", 2, 1),
                Token("FLOAT_CONST", ".3dl", 3, 1),
                Token("FLOAT_CONST", "4e+2DF", 4, 1),
                Token("FLOAT_CONST", "5e-1DD", 5, 1),
                Token("FLOAT_CONST", "6.DL", 6, 1),
            ],
        )

        c23.input("1.25df+2.50dd")
        self.assertEqual(
            token_list(c23),
            [
                Token("FLOAT_CONST", "1.25df", 1, 1),
                Token("PLUS", "+", 1, 7),
                Token("FLOAT_CONST", "2.50dd", 1, 8),
            ],
        )

    def test_decimal_literals_in_legacy_lexer(self):
        # Literal recognition is shared; the parser enforces the dialect.
        self.clex.input("1.25df 2.dd 3e1DL")
        self.assertEqual(
            token_list(self.clex),
            [
                Token("FLOAT_CONST", "1.25df", 1, 1),
                Token("FLOAT_CONST", "2.dd", 1, 8),
                Token("FLOAT_CONST", "3e1DL", 1, 13),
            ],
        )

        self.clex.input(".5DD")
        self.assertEqual(token_list(self.clex), [Token("FLOAT_CONST", ".5DD", 1, 1)])

    def test_c23_binary_floating_constants(self):
        c23 = CLexer(
            self.error_func,
            lambda: None,
            lambda: None,
            self.type_lookup_func,
            dialect="c23",
        )
        c23.input("1.5\n1.5f\n.5L\n0x1.fp+2F\n0x1p0dd")
        self.assertEqual(
            token_list(c23),
            [
                Token("FLOAT_CONST", "1.5", 1, 1),
                Token("FLOAT_CONST", "1.5f", 2, 1),
                Token("FLOAT_CONST", ".5L", 3, 1),
                Token("HEX_FLOAT_CONST", "0x1.fp+2F", 4, 1),
                Token("HEX_FLOAT_CONST", "0x1p0", 5, 1),
                Token("ID", "dd", 5, 6),
            ],
        )

    def test_hexadecimal_floating_constants(self):
        self.assertTokensTypes("0xDE.488641p0", ["HEX_FLOAT_CONST"])
        self.assertTokensTypes("0x.488641p0", ["HEX_FLOAT_CONST"])
        self.assertTokensTypes("0X12.P0", ["HEX_FLOAT_CONST"])

    def test_char_constants(self):
        self.assertTokensTypes(r"""'x'""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""L'x'""", ["WCHAR_CONST"])
        self.assertTokensTypes(r"""u8'x'""", ["U8CHAR_CONST"])
        self.assertTokensTypes(r"""u'x'""", ["U16CHAR_CONST"])
        self.assertTokensTypes(r"""U'x'""", ["U32CHAR_CONST"])
        self.assertTokensTypes(r"""'\t'""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""'\''""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""'\?'""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""'\0'""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""'\012'""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""'\x2f'""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""'\x2f12'""", ["CHAR_CONST"])
        self.assertTokensTypes(r"""L'\xaf'""", ["WCHAR_CONST"])

    def test_unicode_char_constants(self):
        for prefix, token_type in (
            ("", "CHAR_CONST"),
            ("L", "WCHAR_CONST"),
            ("u8", "U8CHAR_CONST"),
            ("u", "U16CHAR_CONST"),
            ("U", "U32CHAR_CONST"),
        ):
            for escape in (r"\u00e9", r"\u03A9", r"\U000000E9", r"\U0001F600"):
                literal = f"{prefix}'{escape}'"
                with self.subTest(literal=literal):
                    self.clex.input(f"\n  {literal};")
                    self.assertEqual(
                        token_list(self.clex),
                        [
                            Token(token_type, literal, 2, 3),
                            Token("SEMI", ";", 2, 3 + len(literal)),
                        ],
                    )

    def test_unicode_multicharacter_constants(self):
        # Unicode escapes have fixed width: a following hex digit is a separate
        # character, unlike the variable-width hexadecimal escape \x.
        for literal in (
            r"'\u00e9a'",
            r"'\U0001F6000'",
            r"'a\u00e9'",
            r"'\u00e9\U0001F600'",
            r"'\u00e9\u00f1\u03a9\u03b1'",
        ):
            with self.subTest(literal=literal):
                self.assertTokensTypes(literal, ["INT_CONST_CHAR"])
        # Keep the lexer's existing permissiveness for other escape spellings.
        self.assertTokensTypes(
            r"'\u' '\U' '\u123'", ["CHAR_CONST", "CHAR_CONST", "INT_CONST_CHAR"]
        )

    def test_on_rbrace_lbrace(self):
        braces = []

        def on_lbrace():
            braces.append("{")

        def on_rbrace():
            braces.append("}")

        clex = CLexer(self.error_func, on_lbrace, on_rbrace, self.type_lookup_func)
        clex.input("hello { there } } and again }}{")
        token_list(clex)
        self.assertEqual(braces, ["{", "}", "}", "}", "}", "{"])

    def test_string_literal(self):
        self.assertTokensTypes('"a string"', ["STRING_LITERAL"])
        self.assertTokensTypes('L"ing"', ["WSTRING_LITERAL"])
        self.assertTokensTypes('u8"ing"', ["U8STRING_LITERAL"])
        self.assertTokensTypes('u"ing"', ["U16STRING_LITERAL"])
        self.assertTokensTypes('U"ing"', ["U32STRING_LITERAL"])
        self.assertTokensTypes('"i am a string too \t"', ["STRING_LITERAL"])
        self.assertTokensTypes(
            r'''"esc\ape \"\'\? \0234 chars \rule"''', ["STRING_LITERAL"]
        )
        self.assertTokensTypes(
            r'''"hello 'joe' wanna give it a \"go\"?"''', ["STRING_LITERAL"]
        )
        self.assertTokensTypes(
            '"\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123"',
            ["STRING_LITERAL"],
        )
        # Note: a-zA-Z and '.-~^_!=&;,' are allowed as escape chars to support #line
        # directives with Windows paths as filenames (..\..\dir\file)
        self.assertTokensTypes(r'"\x"', ["STRING_LITERAL"])
        self.assertTokensTypes(
            r'"\a\b\c\d\e\f\g\h\i\j\k\l\m\n\o\p\q\r\s\t\u\v\w\x\y\z\A\B\C\D\E\F\G\H\I\J\K\L\M\N\O\P\Q\R\S\T\U\V\W\X\Y\Z"',
            ["STRING_LITERAL"],
        )
        self.assertTokensTypes(r'"C:\x\fa\x1e\xited"', ["STRING_LITERAL"])
        # The lexer is permissive and allows decimal escapes (not just octal)
        self.assertTokensTypes(r'"jx\9"', ["STRING_LITERAL"])
        self.assertTokensTypes(r'"fo\9999999"', ["STRING_LITERAL"])

    def test_mess(self):
        self.assertTokensTypes(
            r"[{}]()", ["LBRACKET", "LBRACE", "RBRACE", "RBRACKET", "LPAREN", "RPAREN"]
        )

        self.assertTokensTypes(
            r"()||!C&~Z?J",
            [
                "LPAREN",
                "RPAREN",
                "LOR",
                "LNOT",
                "ID",
                "AND",
                "NOT",
                "ID",
                "CONDOP",
                "ID",
            ],
        )

        self.assertTokensTypes(
            r"+-*/%|||&&&^><>=<===!=",
            [
                "PLUS",
                "MINUS",
                "TIMES",
                "DIVIDE",
                "MOD",
                "LOR",
                "OR",
                "LAND",
                "AND",
                "XOR",
                "GT",
                "LT",
                "GE",
                "LE",
                "EQ",
                "NE",
            ],
        )

        self.assertTokensTypes(
            r"++--->?.,;:",
            [
                "PLUSPLUS",
                "MINUSMINUS",
                "ARROW",
                "CONDOP",
                "PERIOD",
                "COMMA",
                "SEMI",
                "COLON",
            ],
        )

    def test_exprs(self):
        self.assertTokensTypes("bb-cc", ["ID", "MINUS", "ID"])

        self.assertTokensTypes("foo & 0xFF", ["ID", "AND", "INT_CONST_HEX"])

        self.assertTokensTypes(
            "(2+k) * 62",
            [
                "LPAREN",
                "INT_CONST_DEC",
                "PLUS",
                "ID",
                "RPAREN",
                "TIMES",
                "INT_CONST_DEC",
            ],
        )

        self.assertTokensTypes("x | y >> z", ["ID", "OR", "ID", "RSHIFT", "ID"])

        self.assertTokensTypes(
            "x <<= z << 5", ["ID", "LSHIFTEQUAL", "ID", "LSHIFT", "INT_CONST_DEC"]
        )

        self.assertTokensTypes(
            "x = y > 0 ? y : -6",
            [
                "ID",
                "EQUALS",
                "ID",
                "GT",
                "INT_CONST_OCT",
                "CONDOP",
                "ID",
                "COLON",
                "MINUS",
                "INT_CONST_DEC",
            ],
        )

        self.assertTokensTypes("a+++b", ["ID", "PLUSPLUS", "PLUS", "ID"])

    def test_statements(self):
        self.assertTokensTypes(
            "for (int i = 0; i < n; ++i)",
            [
                "FOR",
                "LPAREN",
                "INT",
                "ID",
                "EQUALS",
                "INT_CONST_OCT",
                "SEMI",
                "ID",
                "LT",
                "ID",
                "SEMI",
                "PLUSPLUS",
                "ID",
                "RPAREN",
            ],
        )

        self.assertTokensTypes(
            "self: goto self;", ["ID", "COLON", "GOTO", "ID", "SEMI"]
        )

        self.assertTokensTypes(
            """ switch (typ)
                {
                    case TYPE_ID:
                        m = 5;
                        break;
                    default:
                        m = 8;
                }""",
            [
                "SWITCH",
                "LPAREN",
                "ID",
                "RPAREN",
                "LBRACE",
                "CASE",
                "ID",
                "COLON",
                "ID",
                "EQUALS",
                "INT_CONST_DEC",
                "SEMI",
                "BREAK",
                "SEMI",
                "DEFAULT",
                "COLON",
                "ID",
                "EQUALS",
                "INT_CONST_DEC",
                "SEMI",
                "RBRACE",
            ],
        )

    def test_preprocessor_line(self):
        self.assertTokensTypes("#abracadabra", ["PPHASH", "ID"])

        str = r"""
        546
        #line 66 "kwas\df.h"
        id 4
        dsf
        # 9
        armo
        #line 10 "..\~..\test.h"
        tok1
        #line 99999 "include/me.h"
        tok2
        """

        # ~ self.clex.filename
        self.clex.input(str)

        t1 = require_token(self.clex.token())
        self.assertEqual(t1.type, "INT_CONST_DEC")
        self.assertEqual(t1.lineno, 2)

        t2 = require_token(self.clex.token())
        self.assertEqual(t2.type, "ID")
        self.assertEqual(t2.value, "id")
        self.assertEqual(t2.lineno, 66)
        self.assertEqual(self.clex.filename, r"kwas\df.h")

        for i in range(3):
            t = require_token(self.clex.token())

        self.assertEqual(t.type, "ID")
        self.assertEqual(t.value, "armo")
        self.assertEqual(t.lineno, 9)
        self.assertEqual(self.clex.filename, r"kwas\df.h")

        t4 = require_token(self.clex.token())
        self.assertEqual(t4.type, "ID")
        self.assertEqual(t4.value, "tok1")
        self.assertEqual(t4.lineno, 10)
        self.assertEqual(self.clex.filename, r"..\~..\test.h")

        t5 = require_token(self.clex.token())
        self.assertEqual(t5.type, "ID")
        self.assertEqual(t5.value, "tok2")
        self.assertEqual(t5.lineno, 99999)
        self.assertEqual(self.clex.filename, r"include/me.h")

    def test_preprocessor_line_funny(self):
        str = r"""
        #line 10 "..\6\joe.h"
        10
        """
        self.clex.input(str)

        t1 = require_token(self.clex.token())
        self.assertEqual(t1.type, "INT_CONST_DEC")
        self.assertEqual(t1.lineno, 10)
        self.assertEqual(self.clex.filename, r"..\6\joe.h")

    def test_preprocessor_pragma(self):
        str = """
        42
        #pragma
        #pragma helo me
        #pragma once
        # pragma omp parallel private(th_id)
        #\tpragma {pack: 2, smack: 3}
        #pragma <includeme.h> "nowit.h"
        #pragma "string"
        #pragma somestring="some_other_string"
        #pragma id 124124 and numbers 0235495
        _Pragma("something else")
        59
        """
        # Check that pragmas are tokenized, including trailing string
        self.clex.input(str)

        t1 = require_token(self.clex.token())
        self.assertEqual(t1.type, "INT_CONST_DEC")

        t2 = require_token(self.clex.token())
        self.assertEqual(t2.type, "PPPRAGMA")

        t3 = require_token(self.clex.token())
        self.assertEqual(t3.type, "PPPRAGMA")

        t4 = require_token(self.clex.token())
        self.assertEqual(t4.type, "PPPRAGMASTR")
        self.assertEqual(t4.value, "helo me")

        for i in range(3):
            self.clex.token()

        t5 = require_token(self.clex.token())
        self.assertEqual(t5.type, "PPPRAGMASTR")
        self.assertEqual(t5.value, "omp parallel private(th_id)")

        for i in range(5):
            ta = require_token(self.clex.token())
            self.assertEqual(ta.type, "PPPRAGMA")
            tb = require_token(self.clex.token())
            self.assertEqual(tb.type, "PPPRAGMASTR")

        t6a = require_token(self.clex.token())
        t6l = require_token(self.clex.token())
        t6b = require_token(self.clex.token())
        t6r = require_token(self.clex.token())
        self.assertEqual(t6a.type, "_PRAGMA")
        self.assertEqual(t6l.type, "LPAREN")
        self.assertEqual(t6b.type, "STRING_LITERAL")
        self.assertEqual(t6b.value, '"something else"')
        self.assertEqual(t6r.type, "RPAREN")

        t7 = require_token(self.clex.token())
        self.assertEqual(t7.type, "INT_CONST_DEC")
        self.assertEqual(t7.lineno, 13)


# Keeps all the errors the lexer spits in one place, to allow
# easier modification if the error syntax changes.
#
ERR_ILLEGAL_CHAR = "Illegal character"
ERR_OCTAL = "Invalid octal constant"
ERR_UNMATCHED_QUOTE = "Unmatched '"
ERR_INVALID_CCONST = "Invalid char constant"
ERR_STRING_ESCAPE = "String contains invalid escape"

ERR_FILENAME_BEFORE_LINE = "filename before line"
ERR_LINENUM_MISSING = "line number missing"
ERR_INVALID_LINE_DIRECTIVE = "invalid #line directive"
ERR_COMMENT = "Comments are not supported"


class TestCLexerErrors(unittest.TestCase):
    """Test lexing of erroneous strings.
    Works by passing an error function that saves the error
    in an attribute for later perusal.
    """

    def error_func(self, msg, line, column):
        self.error = msg

    def on_lbrace_func(self):
        pass

    def on_rbrace_func(self):
        pass

    def type_lookup_func(self, typ):
        return False

    def setUp(self):
        self.clex = CLexer(
            self.error_func,
            self.on_lbrace_func,
            self.on_rbrace_func,
            self.type_lookup_func,
        )
        self.error = ""

    def assertLexerError(self, str, error_like):
        # feed the string to the lexer
        self.clex.input(str)

        # Pulls all tokens from the string. Errors will
        # be written into self.error by the error_func
        # callback
        #
        token_types(self.clex)

        # compare the error to the expected
        self.assertTrue(
            re.search(error_like, self.error),
            f"\nExpected error matching: {error_like}\nGot: {self.error}",
        )

        # clear last error, for the sake of subsequent invocations
        self.error = ""

    def test_trivial_tokens(self):
        self.assertLexerError("@", ERR_ILLEGAL_CHAR)
        self.assertLexerError("`", ERR_ILLEGAL_CHAR)
        self.assertLexerError("\\", ERR_ILLEGAL_CHAR)

    def test_integer_constants(self):
        self.assertLexerError("029", ERR_OCTAL)
        self.assertLexerError("012345678", ERR_OCTAL)
        self.assertLexerError("0'8", ERR_OCTAL)
        self.assertLexerError("0'7'9", ERR_OCTAL)

    def test_char_constants(self):
        self.assertLexerError("'", ERR_UNMATCHED_QUOTE)
        self.assertLexerError("'b\n", ERR_UNMATCHED_QUOTE)
        self.assertLexerError("'\\xaa\n'", ERR_UNMATCHED_QUOTE)

        self.assertLexerError(r"'123\12a'", ERR_INVALID_CCONST)
        self.assertLexerError(r"'123\xabg'", ERR_INVALID_CCONST)
        self.assertLexerError("''", ERR_INVALID_CCONST)
        self.assertLexerError("'abcjx'", ERR_INVALID_CCONST)
        self.assertLexerError(r"'\*'", ERR_INVALID_CCONST)

    def test_unicode_escape_backtracking(self):
        # Long malformed constants must not permit exponential backtracking
        # between Unicode escapes and the permissive simple-escape pattern.
        escapes = r"\u00e9\U0001F600" * 30
        self.assertLexerError("'" + escapes, ERR_UNMATCHED_QUOTE)
        self.assertLexerError("'" + escapes + "\n", ERR_UNMATCHED_QUOTE)
        self.assertLexerError("'" + escapes + "'", ERR_INVALID_CCONST)

    def test_string_literals(self):
        self.assertLexerError(r'"jx\`"', ERR_STRING_ESCAPE)
        self.assertLexerError(r'"hekllo\* on ix"', ERR_STRING_ESCAPE)
        self.assertLexerError(r'L"hekllo\* on ix"', ERR_STRING_ESCAPE)
        # Should not suffer from slow backtracking
        self.assertLexerError(
            r'"\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\`\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123"',
            ERR_STRING_ESCAPE,
        )
        self.assertLexerError(
            r'"\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\x23\`\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23\xf1\x23"',
            ERR_STRING_ESCAPE,
        )
        # Should not suffer from slow backtracking when there's no end quote
        self.assertLexerError(
            r'"\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\`\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\123\12\123456',
            ERR_ILLEGAL_CHAR,
        )
        self.assertLexerError(
            r'"\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\`\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x23\x2\x23456',
            ERR_ILLEGAL_CHAR,
        )

    def test_preprocessor(self):
        self.assertLexerError('#line "ka"', ERR_FILENAME_BEFORE_LINE)
        self.assertLexerError("#line df", ERR_INVALID_LINE_DIRECTIVE)
        self.assertLexerError("#line \n", ERR_LINENUM_MISSING)
        # Integer suffixes are not valid in #line directives (issue #587).
        self.assertLexerError("#line 0u", ERR_INVALID_LINE_DIRECTIVE)
        self.assertLexerError("#line 1U", ERR_INVALID_LINE_DIRECTIVE)
        self.assertLexerError("#line 10uLL", ERR_INVALID_LINE_DIRECTIVE)
        self.assertLexerError("#line 1'000u", ERR_INVALID_LINE_DIRECTIVE)
        self.assertLexerError("#line 1''000", ERR_INVALID_LINE_DIRECTIVE)
        # a compatible preprocessor must remove comments.
        self.assertLexerError("//", ERR_COMMENT)
        self.assertLexerError("/*", ERR_COMMENT)


if __name__ == "__main__":
    unittest.main()
