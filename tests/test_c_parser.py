import os
import unittest

from pycparser import c_parser
from pycparser.c_ast import *

ParseError = c_parser.ParseError

_c_parser = c_parser.CParser()


def expand_decl(decl):
    """Converts the declaration into a nested list."""
    typ = type(decl)

    if typ == TypeDecl:
        return ["TypeDecl", expand_decl(decl.type)]
    elif typ == IdentifierType:
        return ["IdentifierType", decl.names]
    elif typ == ID:
        return ["ID", decl.name]
    elif typ in [Struct, Union]:
        decls = [expand_decl(d) for d in decl.decls or []]
        return [typ.__name__, decl.name, decls]
    elif typ == Enum:
        if decl.values is None:
            values = None
        else:
            assert isinstance(decl.values, EnumeratorList)
            values = [enum.name for enum in decl.values.enumerators]
        return ["Enum", decl.name, values]
    elif typ == Alignas:
        return ["Alignas", expand_init(decl.alignment)]
    elif typ == StaticAssert:
        if decl.message:
            return ["StaticAssert", decl.cond.value, decl.message.value]
        else:
            return ["StaticAssert", decl.cond.value]
    else:
        nested = expand_decl(decl.type)

        if typ == Decl:
            r = ["Decl"]
            if decl.quals:
                r.append(decl.quals)
            if decl.align:
                r.append(expand_decl(decl.align[0]))
            r.extend([decl.name, nested])
            return r
        elif typ == Typename:  # for function parameters
            if decl.quals:
                return ["Typename", decl.quals, nested]
            else:
                return ["Typename", nested]
        elif typ == ArrayDecl:
            dimval = decl.dim.value if decl.dim else ""
            return ["ArrayDecl", dimval, decl.dim_quals, nested]
        elif typ == PtrDecl:
            if decl.quals:
                return ["PtrDecl", decl.quals, nested]
            else:
                return ["PtrDecl", nested]
        elif typ == Typedef:
            return ["Typedef", decl.name, nested]
        elif typ == FuncDecl:
            if decl.args:
                params = [expand_decl(param) for param in decl.args.params]
            else:
                params = []
            return ["FuncDecl", params, nested]


def expand_init(init):
    """Converts an initialization into a nested list"""
    typ = type(init)

    if typ == NamedInitializer:
        des = [expand_init(dp) for dp in init.name]
        return (des, expand_init(init.expr))
    elif typ in (InitList, ExprList):
        return [expand_init(expr) for expr in init.exprs]
    elif typ == Constant:
        return ["Constant", init.type, init.value]
    elif typ == ID:
        return ["ID", init.name]
    elif typ == Decl:
        return ["Decl", init.name]
    elif typ == UnaryOp:
        return ["UnaryOp", init.op, expand_decl(init.expr)]
    elif typ == BinaryOp:
        return ["BinaryOp", expand_init(init.left), init.op, expand_init(init.right)]
    elif typ == Compound:
        blocks = []
        if init.block_items:
            blocks = [expand_init(i) for i in init.block_items]
        return ["Compound", blocks]
    elif typ == Typename:
        return expand_decl(init)
    else:
        # Fallback to type name
        return [typ.__name__]


class TestCParser_base(unittest.TestCase):
    def parse(self, txt, filename=""):
        return self.cparser.parse(txt, filename)

    def setUp(self):
        self.cparser = _c_parser

    def assert_coord(self, node, line, column=None, file=None):
        self.assertEqual(node.coord.line, line)
        if column is not None:
            self.assertEqual(node.coord.column, column)
        if file is not None:
            self.assertEqual(node.coord.file, file)


class TestCParser_fundamentals(TestCParser_base):
    def get_decl(self, txt, index=0):
        """Given a source and an index returns the expanded
        declaration at that index.

        FileAST holds a list of 'external declarations'.
        index is the offset of the desired declaration in that
        list.
        """
        t = self.parse(txt).ext[index]
        return expand_decl(t)

    def get_decl_init(self, txt, index=0):
        """Returns the expanded initializer of the declaration
        at index.
        """
        t = self.parse(txt).ext[index]
        return expand_init(t.init)

    def test_FileAST(self):
        t = self.parse("int a; char c;")
        self.assertIsInstance(t, FileAST)
        self.assertEqual(len(t.ext), 2)

        # empty file
        t2 = self.parse("")
        self.assertIsInstance(t2, FileAST)
        self.assertEqual(len(t2.ext), 0)

    def test_empty_toplevel_decl(self):
        code = "int foo;;"
        t = self.parse(code)
        self.assertIsInstance(t, FileAST)
        self.assertEqual(len(t.ext), 1)
        self.assertEqual(
            self.get_decl(code),
            ["Decl", "foo", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

    def test_initial_semi(self):
        t = self.parse(";")
        self.assertEqual(len(t.ext), 0)
        t = self.parse(";int foo;")
        self.assertEqual(len(t.ext), 1)
        self.assertEqual(
            expand_decl(t.ext[0]),
            ["Decl", "foo", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

    def test_line_directive_update_in_errors(self):
        s1 = """
        \t # \t line \t 8 \t "baz.c" \t

        some syntax error here
        """
        self.assertRaisesRegex(ParseError, "baz.c:9", self.parse, s1)

        s2 = """
        \t # \t 8 \t "baz.c" \t


        some syntax error here
        """
        self.assertRaisesRegex(ParseError, "baz.c:10", self.parse, s2)

        s3 = """ #line 5 "foo.c"
        extern int xx;
        #line 6 "bar.c"
        extern int yy;
        #line 7 "baz.c"
        some syntax error here
        #line 8 "yadda.c"
        extern int zz;
        """
        self.assertRaisesRegex(ParseError, "baz.c:7", self.parse, s3)

    def test_coords(self):
        # Tests the "coordinates" of parsed elements - file name, line and
        # column numbers, with modification inserted by #line directives.
        self.assert_coord(self.parse("int a;").ext[0], 1, 5)

        t1 = """
        int a;
        int b;\n\n
        int c;
        """
        f1 = self.parse(t1, filename="test.c")
        self.assert_coord(f1.ext[0], 2, 13, "test.c")
        self.assert_coord(f1.ext[1], 3, 13, "test.c")
        self.assert_coord(f1.ext[2], 6, 13, "test.c")

        t1_1 = """
        int main() {
            k = p;
            printf("%d", b);
            return 0;
        }"""
        f1_1 = self.parse(t1_1, filename="test.c")
        self.assert_coord(f1_1.ext[0].body.block_items[0], 3, 13, "test.c")
        self.assert_coord(f1_1.ext[0].body.block_items[1], 4, 13, "test.c")

        t1_2 = """
        int main () {
            int p = (int) k;
        }"""
        f1_2 = self.parse(t1_2, filename="test.c")
        # make sure that the Cast has a coord (issue 23)
        self.assert_coord(f1_2.ext[0].body.block_items[0].init, 3, 21, file="test.c")

        t2 = """
        #line 99
        int c;
        """
        self.assert_coord(self.parse(t2).ext[0], 99, 13)

        t3 = """
        int dsf;
        char p;
        #line 3000 "in.h"
        char d;
        """
        f3 = self.parse(t3, filename="test.c")
        self.assert_coord(f3.ext[0], 2, 13, "test.c")
        self.assert_coord(f3.ext[1], 3, 14, "test.c")
        self.assert_coord(f3.ext[2], 3000, 14, "in.h")

        t4 = """
        #line 20 "restore.h"
        int maydler(char);

        #line 30 "includes/daween.ph"
        long j, k;

        #line 50000
        char* ro;
        """
        f4 = self.parse(t4, filename="myb.c")
        self.assert_coord(f4.ext[0], 20, 13, "restore.h")
        self.assert_coord(f4.ext[1], 30, 14, "includes/daween.ph")
        self.assert_coord(f4.ext[2], 30, 17, "includes/daween.ph")
        self.assert_coord(f4.ext[3], 50000, 13, "includes/daween.ph")

        t5 = """
        int
        #line 99
        c;
        """
        self.assert_coord(self.parse(t5).ext[0], 99, 9)

        # coord for ellipsis
        t6 = """
        int foo(int j,
                ...) {
        }"""
        self.assert_coord(self.parse(t6).ext[0].decl.type.args.params[1], 3, 17)

        # Coord for _Atomic type decls
        t7 = """
        typedef _Atomic(char) atomic_char;
        """
        self.assert_coord(self.parse(t7).ext[0], 2, 31)
        self.assert_coord(self.parse(t7).ext[0].type, 2, 31)

    def test_coords_included_initializers(self):
        for value in ("1", '"value"', 'L"value"', 'u8"value"', 'u"value"', 'U"value"'):
            with self.subTest(value=value):
                declaration = "int a" if value == "1" else "char *a"
                text = (
                    f'# 1 "main.c"\n{declaration} =\n'
                    '# 7 "value.h" 1\n'
                    f"  {value}\n"
                    '# 3 "main.c" 2\n;\n'
                )
                ast = self.parse(text)
                self.assert_coord(ast.ext[0].init, 7, 3, "value.h")
                self.assert_coord(ast.ext[0], 1, 5 if value == "1" else 6, "main.c")

    def test_coords_adjacent_strings_across_files(self):
        for filename in ("first.h", "", "main.c"):
            with self.subTest(filename=filename):
                text = (
                    "char *a =\n"
                    f'#line 7 "{filename}"\n  "first"\n'
                    '#line 12 "second.h"\n    "second"\n'
                    '#line 3 "main.c"\n;\n'
                )
                ast = self.parse(text, filename="main.c")
                self.assertEqual(ast.ext[0].init.value, '"firstsecond"')
                self.assert_coord(ast.ext[0].init, 7, 3, filename)

    def test_coords_declarator_lookahead(self):
        text = 'int (\n#line 7 "name.h"\n  value\n#line 3 "main.c"\n);\n'
        ast = self.parse(text, filename="main.c")
        self.assert_coord(ast.ext[0], 7, 3, "name.h")
        self.assert_coord(ast.ext[0].type, 7, 3, "name.h")

    def test_coords_error_after_declarator_lookahead(self):
        text = 'int (\n#line 7 "name.h"\n  value unexpected\n#line 3 "main.c"\n);\n'
        with self.assertRaises(ParseError) as error:
            self.parse(text, filename="main.c")
        self.assertEqual(str(error.exception), "name.h:7:9: before: unexpected")

    def test_coords_compound_across_files(self):
        text = 'void f(void) {\n#line 7 "body.h"\n  return;\n}\n'
        ast = self.parse(text, filename="main.c")
        self.assert_coord(ast.ext[0].body, 1, 14, "main.c")
        self.assert_coord(ast.ext[0].body.block_items[0], 7, 3, "body.h")
        ast = self.parse("int other;", filename="next.c")
        self.assert_coord(ast.ext[0], 1, 5, "next.c")

    def test_forloop_coord(self):
        t = """\
        void foo() {
            for(int z=0; z<4;
                z++){}
        }
        """
        s = self.parse(t, filename="f.c")
        forloop = s.ext[0].body.block_items[0]
        self.assert_coord(forloop.init, 2, 13, "f.c")
        self.assert_coord(forloop.cond, 2, 26, "f.c")
        self.assert_coord(forloop.next, 3, 17, "f.c")

    def test_simple_decls(self):
        self.assertEqual(
            self.get_decl("int a;"),
            ["Decl", "a", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        self.assertEqual(
            self.get_decl("unsigned int a;"),
            ["Decl", "a", ["TypeDecl", ["IdentifierType", ["unsigned", "int"]]]],
        )

        self.assertEqual(
            self.get_decl("_Bool a;"),
            ["Decl", "a", ["TypeDecl", ["IdentifierType", ["_Bool"]]]],
        )

        self.assertEqual(
            self.get_decl("float _Complex fcc;"),
            ["Decl", "fcc", ["TypeDecl", ["IdentifierType", ["float", "_Complex"]]]],
        )

        self.assertEqual(
            self.get_decl("char* string;"),
            ["Decl", "string", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]]],
        )

        self.assertEqual(
            self.get_decl("long ar[15];"),
            [
                "Decl",
                "ar",
                ["ArrayDecl", "15", [], ["TypeDecl", ["IdentifierType", ["long"]]]],
            ],
        )

        self.assertEqual(
            self.get_decl("long long ar[15];"),
            [
                "Decl",
                "ar",
                [
                    "ArrayDecl",
                    "15",
                    [],
                    ["TypeDecl", ["IdentifierType", ["long", "long"]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("unsigned ar[];"),
            [
                "Decl",
                "ar",
                ["ArrayDecl", "", [], ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
            ],
        )

        self.assertEqual(
            self.get_decl("int strlen(char* s);"),
            [
                "Decl",
                "strlen",
                [
                    "FuncDecl",
                    [
                        [
                            "Decl",
                            "s",
                            ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int strcmp(char* s1, char* s2);"),
            [
                "Decl",
                "strcmp",
                [
                    "FuncDecl",
                    [
                        [
                            "Decl",
                            "s1",
                            ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                        ],
                        [
                            "Decl",
                            "s2",
                            ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                        ],
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        # function return values and parameters may not have type information
        self.assertEqual(
            self.get_decl("extern foobar(foo, bar);"),
            [
                "Decl",
                "foobar",
                [
                    "FuncDecl",
                    [["ID", "foo"], ["ID", "bar"]],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

    def test_int128(self):
        self.assertEqual(
            self.get_decl("__int128 a;"),
            ["Decl", "a", ["TypeDecl", ["IdentifierType", ["__int128"]]]],
        )

    def test_nested_decls(self):  # the fun begins
        self.assertEqual(
            self.get_decl("char** ar2D;"),
            [
                "Decl",
                "ar2D",
                ["PtrDecl", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]]],
            ],
        )

        self.assertEqual(
            self.get_decl("int (*a)[1][2];"),
            [
                "Decl",
                "a",
                [
                    "PtrDecl",
                    [
                        "ArrayDecl",
                        "1",
                        [],
                        [
                            "ArrayDecl",
                            "2",
                            [],
                            ["TypeDecl", ["IdentifierType", ["int"]]],
                        ],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int *a[1][2];"),
            [
                "Decl",
                "a",
                [
                    "ArrayDecl",
                    "1",
                    [],
                    [
                        "ArrayDecl",
                        "2",
                        [],
                        ["PtrDecl", ["TypeDecl", ["IdentifierType", ["int"]]]],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("char* const* p;"),
            [
                "Decl",
                "p",
                [
                    "PtrDecl",
                    ["PtrDecl", ["const"], ["TypeDecl", ["IdentifierType", ["char"]]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("const char* const* p;"),
            [
                "Decl",
                ["const"],
                "p",
                [
                    "PtrDecl",
                    ["PtrDecl", ["const"], ["TypeDecl", ["IdentifierType", ["char"]]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("char* * const p;"),
            [
                "Decl",
                "p",
                [
                    "PtrDecl",
                    ["const"],
                    ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("char ***ar3D[40];"),
            [
                "Decl",
                "ar3D",
                [
                    "ArrayDecl",
                    "40",
                    [],
                    [
                        "PtrDecl",
                        [
                            "PtrDecl",
                            ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                        ],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("char (***ar3D)[40];"),
            [
                "Decl",
                "ar3D",
                [
                    "PtrDecl",
                    [
                        "PtrDecl",
                        [
                            "PtrDecl",
                            [
                                "ArrayDecl",
                                "40",
                                [],
                                ["TypeDecl", ["IdentifierType", ["char"]]],
                            ],
                        ],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int (*const*const x)(char, int);"),
            [
                "Decl",
                "x",
                [
                    "PtrDecl",
                    ["const"],
                    [
                        "PtrDecl",
                        ["const"],
                        [
                            "FuncDecl",
                            [
                                [
                                    "Typename",
                                    ["TypeDecl", ["IdentifierType", ["char"]]],
                                ],
                                ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            ],
                            ["TypeDecl", ["IdentifierType", ["int"]]],
                        ],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int (*x[4])(char, int);"),
            [
                "Decl",
                "x",
                [
                    "ArrayDecl",
                    "4",
                    [],
                    [
                        "PtrDecl",
                        [
                            "FuncDecl",
                            [
                                [
                                    "Typename",
                                    ["TypeDecl", ["IdentifierType", ["char"]]],
                                ],
                                ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            ],
                            ["TypeDecl", ["IdentifierType", ["int"]]],
                        ],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("char *(*(**foo [][8])())[];"),
            [
                "Decl",
                "foo",
                [
                    "ArrayDecl",
                    "",
                    [],
                    [
                        "ArrayDecl",
                        "8",
                        [],
                        [
                            "PtrDecl",
                            [
                                "PtrDecl",
                                [
                                    "FuncDecl",
                                    [],
                                    [
                                        "PtrDecl",
                                        [
                                            "ArrayDecl",
                                            "",
                                            [],
                                            [
                                                "PtrDecl",
                                                [
                                                    "TypeDecl",
                                                    ["IdentifierType", ["char"]],
                                                ],
                                            ],
                                        ],
                                    ],
                                ],
                            ],
                        ],
                    ],
                ],
            ],
        )

        # explore named and unnamed function pointer parameters,
        # with and without qualifiers

        # unnamed w/o quals
        self.assertEqual(
            self.get_decl("int (*k)(int);"),
            [
                "Decl",
                "k",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

        # unnamed w/ quals
        self.assertEqual(
            self.get_decl("int (*k)(const int);"),
            [
                "Decl",
                "k",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [
                            [
                                "Typename",
                                ["const"],
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ]
                        ],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

        # named w/o quals
        self.assertEqual(
            self.get_decl("int (*k)(int q);"),
            [
                "Decl",
                "k",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [["Decl", "q", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

        # named w/ quals
        self.assertEqual(
            self.get_decl("int (*k)(const volatile int q);"),
            [
                "Decl",
                "k",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [
                            [
                                "Decl",
                                ["const", "volatile"],
                                "q",
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ]
                        ],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int (*k)(_Atomic volatile int q);"),
            [
                "Decl",
                "k",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [
                            [
                                "Decl",
                                ["_Atomic", "volatile"],
                                "q",
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ]
                        ],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int (*k)(const volatile int* q);"),
            [
                "Decl",
                "k",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [
                            [
                                "Decl",
                                ["const", "volatile"],
                                "q",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            ]
                        ],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

        # restrict qualifier
        self.assertEqual(
            self.get_decl("int (*k)(restrict int* q);"),
            [
                "Decl",
                "k",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [
                            [
                                "Decl",
                                ["restrict"],
                                "q",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            ]
                        ],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

    def test_func_decls_with_array_dim_qualifiers(self):
        # named function parameter
        self.assertEqual(
            self.get_decl("int zz(int p[static 10]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Decl",
                            "p",
                            [
                                "ArrayDecl",
                                "10",
                                ["static"],
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )
        # anonymous function parameter
        self.assertEqual(
            self.get_decl("int zz(int [static 10]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Typename",
                            [
                                "ArrayDecl",
                                "10",
                                ["static"],
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )
        self.assertEqual(
            self.get_decl("int zz(int [static const restrict 10]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Typename",
                            [
                                "ArrayDecl",
                                "10",
                                ["static", "const", "restrict"],
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int zz(int p[const 10]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Decl",
                            "p",
                            [
                                "ArrayDecl",
                                "10",
                                ["const"],
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int zz(int p[restrict][5]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Decl",
                            "p",
                            [
                                "ArrayDecl",
                                "",
                                ["restrict"],
                                [
                                    "ArrayDecl",
                                    "5",
                                    [],
                                    ["TypeDecl", ["IdentifierType", ["int"]]],
                                ],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int zz(int p[const restrict static 10][5]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Decl",
                            "p",
                            [
                                "ArrayDecl",
                                "10",
                                ["const", "restrict", "static"],
                                [
                                    "ArrayDecl",
                                    "5",
                                    [],
                                    ["TypeDecl", ["IdentifierType", ["int"]]],
                                ],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        # unnamed function parameter
        self.assertEqual(
            self.get_decl("int zz(int [const 10]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Typename",
                            [
                                "ArrayDecl",
                                "10",
                                ["const"],
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int zz(int [restrict][5]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Typename",
                            [
                                "ArrayDecl",
                                "",
                                ["restrict"],
                                [
                                    "ArrayDecl",
                                    "5",
                                    [],
                                    ["TypeDecl", ["IdentifierType", ["int"]]],
                                ],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        self.assertEqual(
            self.get_decl("int zz(int [const restrict volatile 10][5]);"),
            [
                "Decl",
                "zz",
                [
                    "FuncDecl",
                    [
                        [
                            "Typename",
                            [
                                "ArrayDecl",
                                "10",
                                ["const", "restrict", "volatile"],
                                [
                                    "ArrayDecl",
                                    "5",
                                    [],
                                    ["TypeDecl", ["IdentifierType", ["int"]]],
                                ],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

    def test_qualifiers_storage_specifiers(self):
        def assert_qs(txt, index, quals, storage):
            d = self.parse(txt).ext[index]
            self.assertEqual(d.quals, quals)
            self.assertEqual(d.storage, storage)

        assert_qs("extern int p;", 0, [], ["extern"])
        assert_qs("_Thread_local int p;", 0, [], ["_Thread_local"])
        assert_qs("const long p = 6;", 0, ["const"], [])
        assert_qs("_Atomic int p;", 0, ["_Atomic"], [])
        assert_qs("_Atomic restrict int* p;", 0, ["_Atomic", "restrict"], [])

        d1 = "static const int p, q, r;"
        for i in range(3):
            assert_qs(d1, i, ["const"], ["static"])

        d2 = "static char * const p;"
        assert_qs(d2, 0, [], ["static"])
        pdecl = self.parse(d2).ext[0].type
        self.assertIsInstance(pdecl, PtrDecl)
        self.assertEqual(pdecl.quals, ["const"])

    def test_restricted_specifier_lists(self):
        # Sharing specifier parsing must not admit storage classes or function
        # specifiers in member declarations and type names.
        with self.assertRaisesRegex(ParseError, "Invalid specifier list"):
            self.parse("struct S { static int x; };")
        with self.assertRaisesRegex(ParseError, "Invalid specifier list"):
            self.parse("struct S { inline int x; };")
        with self.assertRaisesRegex(ParseError, "Invalid specifier list"):
            self.parse("int n = sizeof(inline int);")

    def test_specifier_list_missing_type(self):
        # Qualifiers alone do not supply a type; report the first qualifier's
        # position in both member declarations and type names.
        with self.assertRaisesRegex(
            ParseError, r"^types.c:1:12: Missing type in declaration$"
        ):
            self.parse("struct S { const x; };", filename="types.c")
        with self.assertRaisesRegex(
            ParseError, r"^types.c:1:16: Missing type in declaration$"
        ):
            self.parse("int n = sizeof(const);", filename="types.c")

    def test_atomic_specifier(self):
        self.assertEqual(
            self.get_decl("_Atomic(int) ai;"),
            ["Decl", ["_Atomic"], "ai", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        self.assertEqual(
            self.get_decl("_Atomic(int*) ai;"),
            [
                "Decl",
                "ai",
                ["PtrDecl", ["_Atomic"], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

        self.assertEqual(
            self.get_decl("_Atomic(_Atomic(int)*) aai;"),
            [
                "Decl",
                ["_Atomic"],
                "aai",
                ["PtrDecl", ["_Atomic"], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

        # Multiple declarations with _Atomic(...)
        s = "_Atomic(int) foo, bar;"
        self.assertEqual(
            self.get_decl(s, 0),
            ["Decl", ["_Atomic"], "foo", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(
            self.get_decl(s, 1),
            ["Decl", ["_Atomic"], "bar", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        # typedefs with _Atomic specifiers.
        s = "typedef _Atomic(int) atomic_int;"
        self.assertEqual(
            self.get_decl(s, 0),
            ["Typedef", "atomic_int", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        s = "typedef _Atomic(_Bool) atomic_bool;"
        self.assertEqual(
            self.get_decl(s, 0),
            ["Typedef", "atomic_bool", ["TypeDecl", ["IdentifierType", ["_Bool"]]]],
        )

        s = "typedef _Atomic(_Atomic(_Atomic(int (*)(void)) *) *) t;"
        self.assertEqual(
            self.get_decl(s, 0),
            [
                "Typedef",
                "t",
                [
                    "PtrDecl",
                    ["_Atomic"],
                    [
                        "PtrDecl",
                        ["_Atomic"],
                        [
                            "PtrDecl",
                            ["_Atomic"],
                            [
                                "FuncDecl",
                                [
                                    [
                                        "Typename",
                                        ["TypeDecl", ["IdentifierType", ["void"]]],
                                    ]
                                ],
                                ["TypeDecl", ["IdentifierType", ["int"]]],
                            ],
                        ],
                    ],
                ],
            ],
        )

    def test_atomic_specifier_rejects_array_and_function(self):
        # _Atomic cannot wrap an array or function type (C11 6.7.2.4p3). These
        # must raise ParseError rather than crash with AttributeError.
        for s in (
            "_Atomic(char[3]) a;",
            "_Atomic(int[]) a;",
            "_Atomic(char*[3]) a;",
            "_Atomic(void(int)) f;",
            "typedef _Atomic(char[3]) t;",
            "void g(_Atomic(char[3]));",
        ):
            with self.assertRaises(ParseError):
                self.parse(s)

    def test_atomic_specifier_rejects_array_in_sizeof(self):
        with self.assertRaisesRegex(
            ParseError, "_Atomic cannot be applied to array or function type"
        ):
            self.parse("int n = sizeof(_Atomic(char[3]));")

    def test_atomic_specifier_rejects_function_in_sizeof(self):
        with self.assertRaisesRegex(
            ParseError, "_Atomic cannot be applied to array or function type"
        ):
            self.parse("int n = sizeof(_Atomic(void(int)));")

    def test_atomic_specifier_rejects_array_in_cast(self):
        with self.assertRaisesRegex(
            ParseError, "_Atomic cannot be applied to array or function type"
        ):
            self.parse("void f(void) { (_Atomic(char[3]))0; }")

    def test_atomic_specifier_rejects_function_in_cast(self):
        with self.assertRaisesRegex(
            ParseError, "_Atomic cannot be applied to array or function type"
        ):
            self.parse("void f(void) { (_Atomic(void(int)))0; }")

    def test_typedef_parameter_declaration(self):
        self.assertRaises(ParseError, self.parse, "void f(typedef int x);")
        self.assertRaises(ParseError, self.parse, "void f(typedef int);")
        self.assertRaises(ParseError, self.parse, "void f(int a, typedef int *p);")

    def test_atomic_specifier_qualifiers(self):
        decl = self.parse("const _Atomic(volatile int *) p;").ext[0]
        # The outer const qualifies the atomic pointer, while volatile stays
        # on the pointed-to int and in the declaration's base qualifiers.
        self.assertEqual(decl.quals, ["volatile"])
        self.assertIsInstance(decl.type, PtrDecl)
        self.assertEqual(decl.type.quals, ["const", "_Atomic"])
        self.assertIsInstance(decl.type.type, TypeDecl)
        self.assertEqual(decl.type.type.quals, ["volatile"])
        self.assertEqual(decl.type.type.declname, "p")

        typ = self.parse("int n = sizeof(const _Atomic(int *));").ext[0].init.expr
        self.assertIsInstance(typ, Typename)
        self.assertEqual(typ.quals, [])
        self.assertIsInstance(typ.type, PtrDecl)
        self.assertEqual(typ.type.quals, ["const", "_Atomic"])
        self.assertEqual(typ.type.type.quals, [])
        self.assertIsNone(typ.type.type.declname)

    def test_atomic_specifier_multiple_declarators(self):
        decls = self.parse("const _Atomic(int) a, b;").ext
        for decl, name, column in zip(decls, ("a", "b"), (20, 23)):
            self.assertEqual(decl.name, name)
            self.assertEqual(decl.type.declname, name)
            self.assertEqual(decl.quals, ["const", "_Atomic"])
            self.assertEqual(decl.type.quals, ["const", "_Atomic"])
            self.assert_coord(decl.type, 1, column)
        self.assertIsNot(decls[0].type, decls[1].type)

    def test_sizeof(self):
        e = """
            void foo()
            {
                int a = sizeof k;
                int b = sizeof(int);
                int c = sizeof(int**);;

                char* p = "just to make sure this parses w/o error...";
                int d = sizeof(int());
            }
        """
        compound = self.parse(e).ext[0].body

        s1 = compound.block_items[0].init
        self.assertIsInstance(s1, UnaryOp)
        self.assertEqual(s1.op, "sizeof")
        self.assertIsInstance(s1.expr, ID)
        self.assertEqual(s1.expr.name, "k")

        s2 = compound.block_items[1].init
        self.assertEqual(
            expand_decl(s2.expr),
            ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        s3 = compound.block_items[2].init
        self.assertEqual(
            expand_decl(s3.expr),
            [
                "Typename",
                ["PtrDecl", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["int"]]]]],
            ],
        )

    def test_alignof(self):
        r = self.parse("int a = _Alignof(int);")
        self.assertEqual(
            expand_decl(r.ext[0]),
            ["Decl", "a", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(
            expand_init(r.ext[0].init),
            [
                "UnaryOp",
                "_Alignof",
                ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

        self.assertEqual(
            expand_decl(self.parse("_Alignas(_Alignof(int)) char a;").ext[0]),
            [
                "Decl",
                [
                    "Alignas",
                    [
                        "UnaryOp",
                        "_Alignof",
                        ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
                    ],
                ],
                "a",
                ["TypeDecl", ["IdentifierType", ["char"]]],
            ],
        )

        self.assertEqual(
            expand_decl(self.parse("_Alignas(4) char a;").ext[0]),
            [
                "Decl",
                ["Alignas", ["Constant", "int", "4"]],
                "a",
                ["TypeDecl", ["IdentifierType", ["char"]]],
            ],
        )

        self.assertEqual(
            expand_decl(self.parse("_Alignas(int) char a;").ext[0]),
            [
                "Decl",
                ["Alignas", ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                "a",
                ["TypeDecl", ["IdentifierType", ["char"]]],
            ],
        )

    def test_alignas_with_typedef_in_struct(self):
        # Issue #472
        s = """
            typedef int test_int;
            typedef struct {
                _Alignas(int) test_int a1;
            } test_struct;
        """
        ast = self.parse(s)
        field = ast.ext[1].type.type.decls[0]
        self.assertEqual(field.name, "a1")
        self.assertTrue(hasattr(field, "align") and field.align is not None)
        self.assertEqual(
            expand_decl(field),
            [
                "Decl",
                ["Alignas", ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                "a1",
                ["TypeDecl", ["IdentifierType", ["test_int"]]],
            ],
        )

    def test_offsetof(self):
        def expand_ref(n):
            if isinstance(n, StructRef):
                return ["StructRef", expand_ref(n.name), expand_ref(n.field)]
            elif isinstance(n, ArrayRef):
                return ["ArrayRef", expand_ref(n.name), expand_ref(n.subscript)]
            elif isinstance(n, ID):
                return ["ID", n.name]
            elif isinstance(n, Constant):
                return ["Constant", n.type, n.value]
            else:
                raise TypeError("Unexpected type " + n.__class__.__name__)

        e = """
            void foo() {
                int a = offsetof(struct S, p);
                a.b = offsetof(struct sockaddr, sp) + strlen(bar);
                int a = offsetof(struct S, p.q.r);
                int a = offsetof(struct S, p[5].q[4][5]);
            }
            """
        compound = self.parse(e).ext[0].body
        s1 = compound.block_items[0].init
        self.assertIsInstance(s1, FuncCall)
        self.assertIsInstance(s1.name, ID)
        self.assertEqual(s1.name.name, "offsetof")
        self.assertIsInstance(s1.args.exprs[0], Typename)
        self.assertIsInstance(s1.args.exprs[1], ID)
        s3 = compound.block_items[2].init
        self.assertIsInstance(s3.args.exprs[1], StructRef)
        self.assertEqual(
            expand_ref(s3.args.exprs[1]),
            ["StructRef", ["StructRef", ["ID", "p"], ["ID", "q"]], ["ID", "r"]],
        )
        s4 = compound.block_items[3].init
        self.assertIsInstance(s4.args.exprs[1], ArrayRef)
        self.assertEqual(
            expand_ref(s4.args.exprs[1]),
            [
                "ArrayRef",
                [
                    "ArrayRef",
                    [
                        "StructRef",
                        ["ArrayRef", ["ID", "p"], ["Constant", "int", "5"]],
                        ["ID", "q"],
                    ],
                    ["Constant", "int", "4"],
                ],
                ["Constant", "int", "5"],
            ],
        )

    def test_compound_statement(self):
        e = """
            void foo() {
            }
            """
        compound = self.parse(e).ext[0].body
        self.assertIsInstance(compound, Compound)
        self.assert_coord(compound, 2)

    # The C99 compound literal feature
    #
    def test_compound_literals(self):
        ps1 = self.parse(r"""
            void foo() {
                p = (long long){k};
                tc = (struct jk){.a = {1, 2}, .b[0] = t};
            }""")

        compound = ps1.ext[0].body.block_items[0].rvalue
        self.assertEqual(
            expand_decl(compound.type),
            ["Typename", ["TypeDecl", ["IdentifierType", ["long", "long"]]]],
        )
        self.assertEqual(expand_init(compound.init), [["ID", "k"]])

        compound = ps1.ext[0].body.block_items[1].rvalue
        self.assertEqual(
            expand_decl(compound.type), ["Typename", ["TypeDecl", ["Struct", "jk", []]]]
        )
        self.assertEqual(
            expand_init(compound.init),
            [
                ([["ID", "a"]], [["Constant", "int", "1"], ["Constant", "int", "2"]]),
                ([["ID", "b"], ["Constant", "int", "0"]], ["ID", "t"]),
            ],
        )

    def test_empty_compound_literal(self):
        # C23 allows empty initializer braces in compound literals, e.g. (int){}.
        # Also accepted in legacy mode. Regression test for #503.
        ps = self.parse(r"""
            void foo() {
                x = (int){};
                y = (struct jk){};
            }""")
        compound = ps.ext[0].body.block_items[0].rvalue
        self.assertIsInstance(compound, CompoundLiteral)
        self.assertEqual(
            expand_decl(compound.type),
            ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(expand_init(compound.init), [])

        compound = ps.ext[0].body.block_items[1].rvalue
        self.assertIsInstance(compound, CompoundLiteral)
        self.assertEqual(
            expand_decl(compound.type),
            ["Typename", ["TypeDecl", ["Struct", "jk", []]]],
        )
        self.assertEqual(expand_init(compound.init), [])

    def test_parenthesized_compounds(self):
        e = self.parse(r"""
        void foo() {
            int a;
            ({});
            ({ 1; });
            ({ 1; 2; });
            int b = ({ 1; });
            int c, d = ({ int x = 1; x + 2; });
            a = ({ int x = 1; 2 * x; });
        }""")
        body = e.ext[0].body.block_items

        self.assertIsInstance(body[1], Compound)
        self.assertEqual(body[1].block_items, None)

        self.assertIsInstance(body[2], Compound)
        self.assertEqual(len(body[2].block_items), 1)
        self.assertIsInstance(body[2].block_items[0], Constant)

        self.assertIsInstance(body[3], Compound)
        self.assertEqual(len(body[3].block_items), 2)
        self.assertIsInstance(body[3].block_items[0], Constant)
        self.assertIsInstance(body[3].block_items[1], Constant)

        self.assertIsInstance(body[4], Decl)
        self.assertEqual(
            expand_init(body[4].init), ["Compound", [["Constant", "int", "1"]]]
        )

        self.assertIsInstance(body[5], Decl)
        self.assertEqual(body[5].init, None)

        self.assertIsInstance(body[6], Decl)
        self.assertEqual(
            expand_init(body[6].init),
            [
                "Compound",
                [
                    ["Decl", "x"],
                    ["BinaryOp", ["ID", "x"], "+", ["Constant", "int", "2"]],
                ],
            ],
        )

        self.assertIsInstance(body[7], Assignment)
        self.assertIsInstance(body[7].rvalue, Compound)
        self.assertEqual(
            expand_init(body[7].rvalue),
            [
                "Compound",
                [
                    ["Decl", "x"],
                    ["BinaryOp", ["Constant", "int", "2"], "*", ["ID", "x"]],
                ],
            ],
        )

    def test_parenthesized_compounds_binary_operands(self):
        # Regression for #538: the compound is a binary operand, rather than
        # the entire right-hand side of an assignment.
        e = self.parse("""
            float f(float z) {
                return z / ({ float a = 1.0; a * 2; });
            }
        """)
        expr = e.ext[0].body.block_items[0].expr
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "/")
        self.assertEqual(expr.left.name, "z")
        self.assertIsInstance(expr.right, Compound)
        decl, value = expr.right.block_items
        self.assertEqual(decl.name, "a")
        self.assertEqual(decl.init.value, "1.0")
        self.assertEqual(
            expand_init(value),
            ["BinaryOp", ["ID", "a"], "*", ["Constant", "int", "2"]],
        )

    def test_parenthesized_compounds_precedence(self):
        # Multiplication still binds tighter than addition when statement
        # expressions appear as operands on either side.
        e = self.parse("void f() { ({ 1; }) + 2 * ({ 3; }); }")
        expr = e.ext[0].body.block_items[0]
        self.assertEqual(expr.op, "+")
        self.assertIsInstance(expr.left, Compound)
        self.assertEqual(expr.left.block_items[0].value, "1")
        self.assertEqual(expr.right.op, "*")
        self.assertEqual(expr.right.left.value, "2")
        self.assertIsInstance(expr.right.right, Compound)
        self.assertEqual(expr.right.right.block_items[0].value, "3")

    def test_parenthesized_compounds_unary_and_cast(self):
        # Unary minus applies to the statement expression before the cast.
        e = self.parse("void f() { (int) -({ 1.0; }); }")
        expr = e.ext[0].body.block_items[0]
        self.assertIsInstance(expr, Cast)
        self.assertIsInstance(expr.expr, UnaryOp)
        self.assertEqual(expr.expr.op, "-")
        self.assertIsInstance(expr.expr.expr, Compound)
        self.assertEqual(expr.expr.expr.block_items[0].value, "1.0")

    def test_parenthesized_compounds_postfix(self):
        # A statement expression can be the base of an array subscript.
        e = self.parse("void f(int *p) { ({ p; })[0]; }")
        expr = e.ext[0].body.block_items[0]
        self.assertIsInstance(expr, ArrayRef)
        self.assertIsInstance(expr.name, Compound)
        self.assertEqual(expr.name.block_items[0].name, "p")
        self.assertEqual(expr.subscript.value, "0")

    def test_parenthesized_compounds_nested_scope(self):
        # The inner expression sees T as a variable; after the outer
        # expression, T is again a typedef.
        e = self.parse("""
            typedef int T;
            void f() {
                int x = 1 + ({ int T = 2; ({ T + 3; }); });
                T y;
            }
        """)
        decl, after = e.ext[1].body.block_items
        outer = decl.init.right
        self.assertIsInstance(outer, Compound)
        self.assertEqual(outer.block_items[0].name, "T")
        # The final nested statement expression retains its Compound node.
        inner = outer.block_items[1]
        self.assertIsInstance(inner, Compound)
        self.assertEqual(inner.block_items[0].left.name, "T")
        self.assertEqual(inner.block_items[0].op, "+")
        self.assertEqual(inner.block_items[0].right.value, "3")
        self.assertEqual(after.type.type.names, ["T"])

    def test_parenthesized_compounds_invalid_syntax(self):
        # Missing closing parenthesis.
        with self.assertRaises(ParseError):
            self.parse("int f() { return 1 + ({ 2; }; }")
        # Missing expression-statement semicolon.
        with self.assertRaises(ParseError):
            self.parse("int f() { return 1 + ({ 2 }); }")

    def test_enums(self):
        e1 = "enum mycolor op;"
        e1_type = self.parse(e1).ext[0].type.type

        self.assertIsInstance(e1_type, Enum)
        self.assertEqual(e1_type.name, "mycolor")
        self.assertEqual(e1_type.values, None)

        e2 = "enum mysize {large=20, small, medium} shoes;"
        e2_type = self.parse(e2).ext[0].type.type

        self.assertIsInstance(e2_type, Enum)
        self.assertEqual(e2_type.name, "mysize")

        e2_elist = e2_type.values
        self.assertIsInstance(e2_elist, EnumeratorList)

        for e2_eval in e2_elist.enumerators:
            self.assertIsInstance(e2_eval, Enumerator)

        self.assertEqual(e2_elist.enumerators[0].name, "large")
        self.assertEqual(e2_elist.enumerators[0].value.value, "20")
        self.assertEqual(e2_elist.enumerators[2].name, "medium")
        self.assertEqual(e2_elist.enumerators[2].value, None)

        # enum with trailing comma (C99 feature)
        e3 = """
            enum
            {
                red,
                blue,
                green,
            } color;
            """

        e3_type = self.parse(e3).ext[0].type.type
        self.assertIsInstance(e3_type, Enum)
        e3_elist = e3_type.values
        self.assertIsInstance(e3_elist, EnumeratorList)

        for e3_eval in e3_elist.enumerators:
            self.assertIsInstance(e3_eval, Enumerator)

        self.assertEqual(e3_elist.enumerators[0].name, "red")
        self.assertEqual(e3_elist.enumerators[0].value, None)
        self.assertEqual(e3_elist.enumerators[1].name, "blue")
        self.assertEqual(e3_elist.enumerators[2].name, "green")

    def test_enum_leading_pragma(self):
        enum = self.parse("enum E {\n#pragma before\nA, B };", "enum.c").ext[0].type
        pragma, a, b = enum.values.enumerators
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string, "before")
        self.assertEqual(pragma.coord.file, "enum.c")
        self.assertEqual(pragma.coord.line, 2)
        self.assertEqual(a.name, "A")
        self.assertEqual(b.name, "B")
        self.assertEqual(enum.values.coord, a.coord)

    def test_enum_intervening_pragma(self):
        enum = self.parse("enum E { A,\n#pragma between\nB = A + 1 };").ext[0].type
        a, pragma, b = enum.values.enumerators
        self.assertEqual(a.name, "A")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string, "between")
        self.assertEqual(b.name, "B")
        self.assertIsInstance(b.value, BinaryOp)
        self.assertEqual(b.value.left.name, "A")

    def test_enum_pragma_before_comma(self):
        enum = self.parse("enum E { A\n#pragma between\n, B };").ext[0].type
        a, pragma, b = enum.values.enumerators
        self.assertEqual(a.name, "A")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string, "between")
        self.assertEqual(b.name, "B")

    def test_enum_trailing_pragma(self):
        enum = self.parse("enum E { A\n#pragma after\n};").ext[0].type
        a, pragma = enum.values.enumerators
        self.assertEqual(a.name, "A")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string, "after")

    def test_enum_pragma_after_trailing_comma(self):
        enum = self.parse("enum E { A,\n#pragma after\n};").ext[0].type
        a, pragma = enum.values.enumerators
        self.assertEqual(a.name, "A")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string, "after")

    def test_enum_pragma_operator(self):
        enum = (
            self.parse('enum E { _Pragma("before") A _Pragma("after") };').ext[0].type
        )
        before, a, after = enum.values.enumerators
        self.assertIsInstance(before, Pragma)
        self.assertIsInstance(before.string, Constant)
        self.assertEqual(before.string.value, '"before"')
        self.assertEqual(a.name, "A")
        self.assertIsInstance(after, Pragma)
        self.assertEqual(after.string.value, '"after"')

    def test_enum_pragmas_require_enumerator(self):
        with self.assertRaises(ParseError):
            self.parse('enum E {\n#pragma foo\n_Pragma("bar") };')

    def test_enum_pragma_does_not_replace_comma(self):
        with self.assertRaises(ParseError):
            self.parse("enum E { A\n#pragma between\nB };")

    def test_enum_pragma_does_not_allow_duplicate_comma(self):
        with self.assertRaises(ParseError):
            self.parse("enum E { A,\n#pragma between\n, B };")

    def test_enum_pragma_does_not_allow_leading_comma(self):
        with self.assertRaises(ParseError):
            self.parse("enum E {\n#pragma before\n, A };")

    def test_typedef(self):
        # without typedef, error
        s1 = """
            node k;
        """
        self.assertRaises(ParseError, self.parse, s1)

        # now with typedef, works
        s2 = """
            typedef void* node;
            node k;
        """
        ps2 = self.parse(s2)
        self.assertEqual(
            expand_decl(ps2.ext[0]),
            [
                "Typedef",
                "node",
                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["void"]]]],
            ],
        )

        self.assertEqual(
            expand_decl(ps2.ext[1]),
            ["Decl", "k", ["TypeDecl", ["IdentifierType", ["node"]]]],
        )

        s3 = """
            typedef int T;
            typedef T *pT;

            pT aa, bb;
        """
        ps3 = self.parse(s3)
        self.assertEqual(
            expand_decl(ps3.ext[3]),
            ["Decl", "bb", ["TypeDecl", ["IdentifierType", ["pT"]]]],
        )

        s4 = """
            typedef char* __builtin_va_list;
            typedef __builtin_va_list __gnuc_va_list;
        """
        ps4 = self.parse(s4)
        self.assertEqual(
            expand_decl(ps4.ext[1]),
            [
                "Typedef",
                "__gnuc_va_list",
                ["TypeDecl", ["IdentifierType", ["__builtin_va_list"]]],
            ],
        )

        s5 = """typedef struct tagHash Hash;"""
        ps5 = self.parse(s5)
        self.assertEqual(
            expand_decl(ps5.ext[0]),
            ["Typedef", "Hash", ["TypeDecl", ["Struct", "tagHash", []]]],
        )

        s6 = """typedef int (* const * const T)(void);"""
        ps6 = self.parse(s6)
        self.assertEqual(
            expand_decl(ps6.ext[0]),
            [
                "Typedef",
                "T",
                [
                    "PtrDecl",
                    ["const"],
                    [
                        "PtrDecl",
                        ["const"],
                        [
                            "FuncDecl",
                            [["Typename", ["TypeDecl", ["IdentifierType", ["void"]]]]],
                            ["TypeDecl", ["IdentifierType", ["int"]]],
                        ],
                    ],
                ],
            ],
        )

    def test_struct_union(self):
        s1 = """
            struct {
                int id;
                char* name;
            } joe;
            """

        self.assertEqual(
            expand_decl(self.parse(s1).ext[0]),
            [
                "Decl",
                "joe",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        None,
                        [
                            ["Decl", "id", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            [
                                "Decl",
                                "name",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                            ],
                        ],
                    ],
                ],
            ],
        )

        s2 = """
            struct node p;
        """
        self.assertEqual(
            expand_decl(self.parse(s2).ext[0]),
            ["Decl", "p", ["TypeDecl", ["Struct", "node", []]]],
        )

        s21 = """
            union pri ra;
        """
        self.assertEqual(
            expand_decl(self.parse(s21).ext[0]),
            ["Decl", "ra", ["TypeDecl", ["Union", "pri", []]]],
        )

        s3 = """
            struct node* p;
        """
        self.assertEqual(
            expand_decl(self.parse(s3).ext[0]),
            ["Decl", "p", ["PtrDecl", ["TypeDecl", ["Struct", "node", []]]]],
        )

        s4 = """
            struct node;
        """
        self.assertEqual(
            expand_decl(self.parse(s4).ext[0]), ["Decl", None, ["Struct", "node", []]]
        )

        s5 = """
            union
            {
                struct
                {
                    int type;
                } n;

                struct
                {
                    int type;
                    int intnode;
                } ni;
            } u;
        """
        self.assertEqual(
            expand_decl(self.parse(s5).ext[0]),
            [
                "Decl",
                "u",
                [
                    "TypeDecl",
                    [
                        "Union",
                        None,
                        [
                            [
                                "Decl",
                                "n",
                                [
                                    "TypeDecl",
                                    [
                                        "Struct",
                                        None,
                                        [
                                            [
                                                "Decl",
                                                "type",
                                                [
                                                    "TypeDecl",
                                                    ["IdentifierType", ["int"]],
                                                ],
                                            ]
                                        ],
                                    ],
                                ],
                            ],
                            [
                                "Decl",
                                "ni",
                                [
                                    "TypeDecl",
                                    [
                                        "Struct",
                                        None,
                                        [
                                            [
                                                "Decl",
                                                "type",
                                                [
                                                    "TypeDecl",
                                                    ["IdentifierType", ["int"]],
                                                ],
                                            ],
                                            [
                                                "Decl",
                                                "intnode",
                                                [
                                                    "TypeDecl",
                                                    ["IdentifierType", ["int"]],
                                                ],
                                            ],
                                        ],
                                    ],
                                ],
                            ],
                        ],
                    ],
                ],
            ],
        )

        s6 = """
            typedef struct foo_tag
            {
                void* data;
            } foo, *pfoo;
        """
        s6_ast = self.parse(s6)

        self.assertEqual(
            expand_decl(s6_ast.ext[0]),
            [
                "Typedef",
                "foo",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        "foo_tag",
                        [
                            [
                                "Decl",
                                "data",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["void"]]]],
                            ]
                        ],
                    ],
                ],
            ],
        )

        self.assertEqual(
            expand_decl(s6_ast.ext[1]),
            [
                "Typedef",
                "pfoo",
                [
                    "PtrDecl",
                    [
                        "TypeDecl",
                        [
                            "Struct",
                            "foo_tag",
                            [
                                [
                                    "Decl",
                                    "data",
                                    [
                                        "PtrDecl",
                                        ["TypeDecl", ["IdentifierType", ["void"]]],
                                    ],
                                ]
                            ],
                        ],
                    ],
                ],
            ],
        )

        s7 = r"""
            struct _on_exit_args {
                void *  _fnargs[32];
                void *  _dso_handle[32];

                long _fntypes;
                #line 77 "D:\eli\cpp_stuff\libc_include/sys/reent.h"

                long _is_cxa;
            };
        """

        s7_ast = self.parse(s7, filename="test.c")
        self.assert_coord(s7_ast.ext[0].type.decls[2], 6, 22, "test.c")
        self.assert_coord(
            s7_ast.ext[0].type.decls[3],
            78,
            22,
            r"D:\eli\cpp_stuff\libc_include/sys/reent.h",
        )

        s8 = """
            typedef enum tagReturnCode {SUCCESS, FAIL} ReturnCode;

            typedef struct tagEntry
            {
                char* key;
                char* value;
            } Entry;


            typedef struct tagNode
            {
                Entry* entry;

                struct tagNode* next;
            } Node;

            typedef struct tagHash
            {
                unsigned int table_size;

                Node** heads;

            } Hash;
        """
        s8_ast = self.parse(s8)
        self.assertEqual(
            expand_decl(s8_ast.ext[3]),
            [
                "Typedef",
                "Hash",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        "tagHash",
                        [
                            [
                                "Decl",
                                "table_size",
                                ["TypeDecl", ["IdentifierType", ["unsigned", "int"]]],
                            ],
                            [
                                "Decl",
                                "heads",
                                [
                                    "PtrDecl",
                                    [
                                        "PtrDecl",
                                        ["TypeDecl", ["IdentifierType", ["Node"]]],
                                    ],
                                ],
                            ],
                        ],
                    ],
                ],
            ],
        )

    def test_struct_enum(self):
        s1 = """
            struct Foo {
                enum Bar { A = 1 };
            };
        """
        self.assertEqual(
            expand_decl(self.parse(s1).ext[0]),
            ["Decl", None, ["Struct", "Foo", [["Decl", None, ["Enum", "Bar", ["A"]]]]]],
        )
        s2 = """
            struct Foo {
                enum Bar { A = 1, B, C } bar;
                enum Baz { D = A } baz;
            } foo;
        """
        self.assertEqual(
            expand_decl(self.parse(s2).ext[0]),
            [
                "Decl",
                "foo",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        "Foo",
                        [
                            [
                                "Decl",
                                "bar",
                                ["TypeDecl", ["Enum", "Bar", ["A", "B", "C"]]],
                            ],
                            ["Decl", "baz", ["TypeDecl", ["Enum", "Baz", ["D"]]]],
                        ],
                    ],
                ],
            ],
        )

    def test_struct_with_extra_semis_inside(self):
        s1 = """
            struct {
                int a;;
            } foo;
        """
        s1_ast = self.parse(s1)
        self.assertEqual(
            expand_decl(s1_ast.ext[0]),
            [
                "Decl",
                "foo",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        None,
                        [["Decl", "a", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                    ],
                ],
            ],
        )

        s2 = """
            struct {
                int a;;;;
                float b, c;
                ;;
                char d;
            } foo;
        """
        s2_ast = self.parse(s2)
        self.assertEqual(
            expand_decl(s2_ast.ext[0]),
            [
                "Decl",
                "foo",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        None,
                        [
                            ["Decl", "a", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            ["Decl", "b", ["TypeDecl", ["IdentifierType", ["float"]]]],
                            ["Decl", "c", ["TypeDecl", ["IdentifierType", ["float"]]]],
                            ["Decl", "d", ["TypeDecl", ["IdentifierType", ["char"]]]],
                        ],
                    ],
                ],
            ],
        )

    def test_struct_with_initial_semi(self):
        s1 = """
            struct {
                ;int a;
            } foo;
        """
        s1_ast = self.parse(s1)
        self.assertEqual(
            expand_decl(s1_ast.ext[0]),
            [
                "Decl",
                "foo",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        None,
                        [["Decl", "a", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                    ],
                ],
            ],
        )

    def test_anonymous_struct_union(self):
        s1 = """
            union
            {
                union
                {
                    int i;
                    long l;
                };

                struct
                {
                    int type;
                    int intnode;
                };
            } u;
        """

        self.assertEqual(
            expand_decl(self.parse(s1).ext[0]),
            [
                "Decl",
                "u",
                [
                    "TypeDecl",
                    [
                        "Union",
                        None,
                        [
                            [
                                "Decl",
                                None,
                                [
                                    "Union",
                                    None,
                                    [
                                        [
                                            "Decl",
                                            "i",
                                            ["TypeDecl", ["IdentifierType", ["int"]]],
                                        ],
                                        [
                                            "Decl",
                                            "l",
                                            ["TypeDecl", ["IdentifierType", ["long"]]],
                                        ],
                                    ],
                                ],
                            ],
                            [
                                "Decl",
                                None,
                                [
                                    "Struct",
                                    None,
                                    [
                                        [
                                            "Decl",
                                            "type",
                                            ["TypeDecl", ["IdentifierType", ["int"]]],
                                        ],
                                        [
                                            "Decl",
                                            "intnode",
                                            ["TypeDecl", ["IdentifierType", ["int"]]],
                                        ],
                                    ],
                                ],
                            ],
                        ],
                    ],
                ],
            ],
        )

        s2 = """
            struct
            {
                int i;
                union
                {
                    int id;
                    char* name;
                };
                float f;
            } joe;
            """

        self.assertEqual(
            expand_decl(self.parse(s2).ext[0]),
            [
                "Decl",
                "joe",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        None,
                        [
                            ["Decl", "i", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            [
                                "Decl",
                                None,
                                [
                                    "Union",
                                    None,
                                    [
                                        [
                                            "Decl",
                                            "id",
                                            ["TypeDecl", ["IdentifierType", ["int"]]],
                                        ],
                                        [
                                            "Decl",
                                            "name",
                                            [
                                                "PtrDecl",
                                                [
                                                    "TypeDecl",
                                                    ["IdentifierType", ["char"]],
                                                ],
                                            ],
                                        ],
                                    ],
                                ],
                            ],
                            ["Decl", "f", ["TypeDecl", ["IdentifierType", ["float"]]]],
                        ],
                    ],
                ],
            ],
        )

        # ISO/IEC 9899:201x Committee Draft 2010-11-16, N1539
        # section 6.7.2.1, par. 19, example 1
        s3 = """
            struct v {
                union {
                    struct { int i, j; };
                    struct { long k, l; } w;
                };
                int m;
            } v1;
            """

        self.assertEqual(
            expand_decl(self.parse(s3).ext[0]),
            [
                "Decl",
                "v1",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        "v",
                        [
                            [
                                "Decl",
                                None,
                                [
                                    "Union",
                                    None,
                                    [
                                        [
                                            "Decl",
                                            None,
                                            [
                                                "Struct",
                                                None,
                                                [
                                                    [
                                                        "Decl",
                                                        "i",
                                                        [
                                                            "TypeDecl",
                                                            ["IdentifierType", ["int"]],
                                                        ],
                                                    ],
                                                    [
                                                        "Decl",
                                                        "j",
                                                        [
                                                            "TypeDecl",
                                                            ["IdentifierType", ["int"]],
                                                        ],
                                                    ],
                                                ],
                                            ],
                                        ],
                                        [
                                            "Decl",
                                            "w",
                                            [
                                                "TypeDecl",
                                                [
                                                    "Struct",
                                                    None,
                                                    [
                                                        [
                                                            "Decl",
                                                            "k",
                                                            [
                                                                "TypeDecl",
                                                                [
                                                                    "IdentifierType",
                                                                    ["long"],
                                                                ],
                                                            ],
                                                        ],
                                                        [
                                                            "Decl",
                                                            "l",
                                                            [
                                                                "TypeDecl",
                                                                [
                                                                    "IdentifierType",
                                                                    ["long"],
                                                                ],
                                                            ],
                                                        ],
                                                    ],
                                                ],
                                            ],
                                        ],
                                    ],
                                ],
                            ],
                            ["Decl", "m", ["TypeDecl", ["IdentifierType", ["int"]]]],
                        ],
                    ],
                ],
            ],
        )

        s4 = """
            struct v {
                int i;
                float;
            } v2;"""
        # just make sure this doesn't raise ParseError
        self.parse(s4)

    def test_struct_member_without_declarator(self):
        # Issue #633: lone atomic, _BitInt, and typeof specifiers must not
        # be traversed as declarators.
        decl = self.parse("struct s { _Atomic(int); };").ext[0]
        (member,) = decl.type.decls
        self.assertIsNone(member.name)
        self.assertIsInstance(member.type, Typename)
        self.assertEqual(member.type.quals, ["_Atomic"])

        c23 = c_parser.CParser(dialect="c23")
        decl = c23.parse("struct s { _BitInt(8); typeof(int); };").ext[0]
        bitint, typeof = decl.type.decls
        self.assertIsNone(bitint.name)
        self.assertIsInstance(bitint.type, BitIntType)
        self.assertIsNone(typeof.name)
        self.assertIsInstance(typeof.type, TypeOf)

    def test_struct_members_namespace(self):
        """Tests that structure/union member names reside in a separate
        namespace and can be named after existing types.
        """
        s1 = """
                typedef int Name;
                typedef Name NameArray[10];

                struct {
                    Name Name;
                    Name NameArray[3];
                } sye;

                void main(void)
                {
                    sye.Name = 1;
                }
            """

        s1_ast = self.parse(s1)
        self.assertEqual(
            expand_decl(s1_ast.ext[2]),
            [
                "Decl",
                "sye",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        None,
                        [
                            [
                                "Decl",
                                "Name",
                                ["TypeDecl", ["IdentifierType", ["Name"]]],
                            ],
                            [
                                "Decl",
                                "NameArray",
                                [
                                    "ArrayDecl",
                                    "3",
                                    [],
                                    ["TypeDecl", ["IdentifierType", ["Name"]]],
                                ],
                            ],
                        ],
                    ],
                ],
            ],
        )
        self.assertEqual(s1_ast.ext[3].body.block_items[0].lvalue.field.name, "Name")

    def test_struct_bitfields(self):
        # a struct with two bitfields, one unnamed
        s1 = """
            struct {
                int k:6;
                int :2;
            } joe;
            """

        parsed_struct = self.parse(s1).ext[0]

        # We can see here the name of the decl for the unnamed bitfield is
        # None, but expand_decl doesn't show bitfield widths
        # ...
        self.assertEqual(
            expand_decl(parsed_struct),
            [
                "Decl",
                "joe",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        None,
                        [
                            ["Decl", "k", ["TypeDecl", ["IdentifierType", ["int"]]]],
                            ["Decl", None, ["TypeDecl", ["IdentifierType", ["int"]]]],
                        ],
                    ],
                ],
            ],
        )

        # ...
        # so we test them manually
        self.assertEqual(parsed_struct.type.type.decls[0].bitsize.value, "6")
        self.assertEqual(parsed_struct.type.type.decls[1].bitsize.value, "2")

    def test_struct_empty(self):
        """
        Tests that parsing an empty struct works.

        Empty structs do NOT follow C99 (See 6.2.5-20 of the C99 standard).
        This is nevertheless supported by some compilers (clang, gcc),
        especially when using FORTIFY code.
        Some compilers (visual) will fail to compile with an error.
        """
        # an empty struct. This is NOT C99 compliant
        s1 = """
                 struct foo { };
             """

        parsed_struct = self.parse(s1).ext[0]
        self.assertEqual(
            expand_decl(parsed_struct), ["Decl", None, ["Struct", "foo", []]]
        )

        s2 = """struct { } foo;"""
        parsed_struct = self.parse(s2).ext[0]
        self.assertEqual(
            expand_decl(parsed_struct),
            ["Decl", "foo", ["TypeDecl", ["Struct", None, []]]],
        )

        s3 = """union { } foo;"""
        parsed_struct = self.parse(s3).ext[0]
        self.assertEqual(
            expand_decl(parsed_struct),
            ["Decl", "foo", ["TypeDecl", ["Union", None, []]]],
        )

    def test_tags_namespace(self):
        """Tests that the tags of structs/unions/enums reside in a separate namespace and
        can be named after existing types.
        """
        s1 = """
                typedef int tagEntry;

                struct tagEntry
                {
                    char* key;
                    char* value;
                } Entry;
            """

        s1_ast = self.parse(s1)
        self.assertEqual(
            expand_decl(s1_ast.ext[1]),
            [
                "Decl",
                "Entry",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        "tagEntry",
                        [
                            [
                                "Decl",
                                "key",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                            ],
                            [
                                "Decl",
                                "value",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                            ],
                        ],
                    ],
                ],
            ],
        )

        s2 = """
                struct tagEntry;

                typedef struct tagEntry tagEntry;

                struct tagEntry
                {
                    char* key;
                    char* value;
                } Entry;
            """

        s2_ast = self.parse(s2)
        self.assertEqual(
            expand_decl(s2_ast.ext[2]),
            [
                "Decl",
                "Entry",
                [
                    "TypeDecl",
                    [
                        "Struct",
                        "tagEntry",
                        [
                            [
                                "Decl",
                                "key",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                            ],
                            [
                                "Decl",
                                "value",
                                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                            ],
                        ],
                    ],
                ],
            ],
        )

        s3 = """
                typedef int mytag;

                enum mytag {ABC, CDE};
                enum mytag joe;
            """

        s3_type = self.parse(s3).ext[1].type

        self.assertIsInstance(s3_type, Enum)
        self.assertEqual(s3_type.name, "mytag")

    def test_multi_decls(self):
        d1 = "int a, b;"

        self.assertEqual(
            self.get_decl(d1, 0),
            ["Decl", "a", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(
            self.get_decl(d1, 1),
            ["Decl", "b", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        d2 = "char* p, notp, ar[4];"
        self.assertEqual(
            self.get_decl(d2, 0),
            ["Decl", "p", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]]],
        )
        self.assertEqual(
            self.get_decl(d2, 1),
            ["Decl", "notp", ["TypeDecl", ["IdentifierType", ["char"]]]],
        )
        self.assertEqual(
            self.get_decl(d2, 2),
            [
                "Decl",
                "ar",
                ["ArrayDecl", "4", [], ["TypeDecl", ["IdentifierType", ["char"]]]],
            ],
        )

    def test_invalid_multiple_types_error(self):
        bad = ["int enum {ab, cd} fubr;", "enum kid char brbr;"]

        for b in bad:
            self.assertRaises(ParseError, self.parse, b)

    def test_invalid_typedef_storage_qual_error(self):
        """Tests that using typedef as a storage qualifier is correctly flagged
        as an error.
        """
        bad = "typedef const int foo(int a) { return 0; }"
        self.assertRaises(ParseError, self.parse, bad)

    def test_duplicate_typedef(self):
        """Tests that redeclarations of existing types are parsed correctly.
        This is non-standard, but allowed by many compilers.
        """
        d1 = """
            typedef int numbertype;
            typedef int numbertype;
        """

        self.assertEqual(
            self.get_decl(d1, 0),
            ["Typedef", "numbertype", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(
            self.get_decl(d1, 1),
            ["Typedef", "numbertype", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        d2 = """
            typedef int (*funcptr)(int x);
            typedef int (*funcptr)(int x);
        """
        self.assertEqual(
            self.get_decl(d2, 0),
            [
                "Typedef",
                "funcptr",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [["Decl", "x", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )
        self.assertEqual(
            self.get_decl(d2, 1),
            [
                "Typedef",
                "funcptr",
                [
                    "PtrDecl",
                    [
                        "FuncDecl",
                        [["Decl", "x", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                        ["TypeDecl", ["IdentifierType", ["int"]]],
                    ],
                ],
            ],
        )

        d3 = """
            typedef int numberarray[5];
            typedef int numberarray[5];
        """
        self.assertEqual(
            self.get_decl(d3, 0),
            [
                "Typedef",
                "numberarray",
                ["ArrayDecl", "5", [], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )
        self.assertEqual(
            self.get_decl(d3, 1),
            [
                "Typedef",
                "numberarray",
                ["ArrayDecl", "5", [], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

    def test_decl_inits(self):
        d1 = "int a = 16;"
        # ~ self.parse(d1).show()
        self.assertEqual(
            self.get_decl(d1), ["Decl", "a", ["TypeDecl", ["IdentifierType", ["int"]]]]
        )
        self.assertEqual(self.get_decl_init(d1), ["Constant", "int", "16"])

        d1_1 = "float f = 0xEF.56p1;"
        self.assertEqual(self.get_decl_init(d1_1), ["Constant", "double", "0xEF.56p1"])

        d1_2 = "int bitmask = 0b1001010;"
        self.assertEqual(self.get_decl_init(d1_2), ["Constant", "int", "0b1001010"])

        d2 = "long ar[] = {7, 8, 9};"
        self.assertEqual(
            self.get_decl(d2),
            [
                "Decl",
                "ar",
                ["ArrayDecl", "", [], ["TypeDecl", ["IdentifierType", ["long"]]]],
            ],
        )
        self.assertEqual(
            self.get_decl_init(d2),
            [
                ["Constant", "int", "7"],
                ["Constant", "int", "8"],
                ["Constant", "int", "9"],
            ],
        )

        d21 = "long ar[4] = {};"
        self.assertEqual(self.get_decl_init(d21), [])

        d3 = "char p = j;"
        self.assertEqual(
            self.get_decl(d3), ["Decl", "p", ["TypeDecl", ["IdentifierType", ["char"]]]]
        )
        self.assertEqual(self.get_decl_init(d3), ["ID", "j"])

        d4 = "char x = 'c', *p = {0, 1, 2, {4, 5}, 6};"
        self.assertEqual(
            self.get_decl(d4, 0),
            ["Decl", "x", ["TypeDecl", ["IdentifierType", ["char"]]]],
        )
        self.assertEqual(self.get_decl_init(d4, 0), ["Constant", "char", "'c'"])
        self.assertEqual(
            self.get_decl(d4, 1),
            ["Decl", "p", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]]],
        )

        self.assertEqual(
            self.get_decl_init(d4, 1),
            [
                ["Constant", "int", "0"],
                ["Constant", "int", "1"],
                ["Constant", "int", "2"],
                [["Constant", "int", "4"], ["Constant", "int", "5"]],
                ["Constant", "int", "6"],
            ],
        )

        d5 = "float d = 1.0;"
        self.assertEqual(self.get_decl_init(d5), ["Constant", "double", "1.0"])

        d51 = "float ld = 1.0l;"
        self.assertEqual(self.get_decl_init(d51), ["Constant", "long double", "1.0l"])

        d52 = "float ld = 1.0L;"
        self.assertEqual(self.get_decl_init(d52), ["Constant", "long double", "1.0L"])

        d53 = "float ld = 1.0f;"
        self.assertEqual(self.get_decl_init(d53), ["Constant", "float", "1.0f"])

        d54 = "float ld = 1.0F;"
        self.assertEqual(self.get_decl_init(d54), ["Constant", "float", "1.0F"])

        d55 = "float ld = 0xDE.38p0;"
        self.assertEqual(self.get_decl_init(d55), ["Constant", "double", "0xDE.38p0"])

        d56 = "float ld = 0xDE.38p0f;"
        self.assertEqual(self.get_decl_init(d56), ["Constant", "float", "0xDE.38p0f"])

        d57 = "float ld = 0xDE.38p0F;"
        self.assertEqual(self.get_decl_init(d57), ["Constant", "float", "0xDE.38p0F"])

        d58 = "float ld = 0xDE.38p0l;"
        self.assertEqual(
            self.get_decl_init(d58), ["Constant", "long double", "0xDE.38p0l"]
        )

        d59 = "float ld = 0xDE.38p0L;"
        self.assertEqual(
            self.get_decl_init(d59), ["Constant", "long double", "0xDE.38p0L"]
        )

        d6 = "int i = 1;"
        self.assertEqual(self.get_decl_init(d6), ["Constant", "int", "1"])

        d61 = "long int li = 1l;"
        self.assertEqual(self.get_decl_init(d61), ["Constant", "long int", "1l"])

        d62 = "unsigned int ui = 1u;"
        self.assertEqual(self.get_decl_init(d62), ["Constant", "unsigned int", "1u"])

        d63 = "unsigned long long int ulli = 1LLU;"
        self.assertEqual(
            self.get_decl_init(d63), ["Constant", "unsigned long long int", "1LLU"]
        )

    def test_decl_named_inits(self):
        d1 = "int a = {.k = 16};"
        self.assertEqual(
            self.get_decl_init(d1), [([["ID", "k"]], ["Constant", "int", "16"])]
        )

        d2 = "int a = { [0].a = {1}, [1].a[0] = 2 };"
        self.assertEqual(
            self.get_decl_init(d2),
            [
                ([["Constant", "int", "0"], ["ID", "a"]], [["Constant", "int", "1"]]),
                (
                    [["Constant", "int", "1"], ["ID", "a"], ["Constant", "int", "0"]],
                    ["Constant", "int", "2"],
                ),
            ],
        )

        d3 = "int a = { .a = 1, .c = 3, 4, .b = 5};"
        self.assertEqual(
            self.get_decl_init(d3),
            [
                ([["ID", "a"]], ["Constant", "int", "1"]),
                ([["ID", "c"]], ["Constant", "int", "3"]),
                ["Constant", "int", "4"],
                ([["ID", "b"]], ["Constant", "int", "5"]),
            ],
        )

    def test_function_definitions(self):
        def parse_fdef(str):
            return self.parse(str).ext[0]

        def fdef_decl(fdef):
            return expand_decl(fdef.decl)

        f1 = parse_fdef("""
        int factorial(int p)
        {
            return 3;
        }
        """)

        self.assertEqual(
            fdef_decl(f1),
            [
                "Decl",
                "factorial",
                [
                    "FuncDecl",
                    [["Decl", "p", ["TypeDecl", ["IdentifierType", ["int"]]]]],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        self.assertEqual(type(f1.body.block_items[0]), Return)

        f2 = parse_fdef("""
        char* zzz(int p, char* c)
        {
            int a;
            char b;

            a = b + 2;
            return 3;
        }
        """)

        self.assertEqual(
            fdef_decl(f2),
            [
                "Decl",
                "zzz",
                [
                    "FuncDecl",
                    [
                        ["Decl", "p", ["TypeDecl", ["IdentifierType", ["int"]]]],
                        [
                            "Decl",
                            "c",
                            ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                        ],
                    ],
                    ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                ],
            ],
        )

        self.assertEqual(
            list(map(type, f2.body.block_items)), [Decl, Decl, Assignment, Return]
        )

        f3 = parse_fdef("""
        char* zzz(p, c)
        long p, *c;
        {
            int a;
            char b;

            a = b + 2;
            return 3;
        }
        """)

        self.assertEqual(
            fdef_decl(f3),
            [
                "Decl",
                "zzz",
                [
                    "FuncDecl",
                    [["ID", "p"], ["ID", "c"]],
                    ["PtrDecl", ["TypeDecl", ["IdentifierType", ["char"]]]],
                ],
            ],
        )

        self.assertEqual(
            list(map(type, f3.body.block_items)), [Decl, Decl, Assignment, Return]
        )

        self.assertEqual(
            expand_decl(f3.param_decls[0]),
            ["Decl", "p", ["TypeDecl", ["IdentifierType", ["long"]]]],
        )
        self.assertEqual(
            expand_decl(f3.param_decls[1]),
            ["Decl", "c", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["long"]]]]],
        )

        # function return values and parameters may not have type information
        f4 = parse_fdef("""
        que(p)
        {
            return 3;
        }
        """)

        self.assertEqual(
            fdef_decl(f4),
            [
                "Decl",
                "que",
                ["FuncDecl", [["ID", "p"]], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

    def test_static_assert(self):
        f1 = self.parse("""
        _Static_assert(1, "123");
        int factorial(int p)
        {
            _Static_assert(2, "456");
            _Static_assert(3);
        }
        """)

        self.assertEqual(expand_decl(f1.ext[0]), ["StaticAssert", "1", '"123"'])
        self.assertEqual(
            expand_decl(f1.ext[1].body.block_items[0]), ["StaticAssert", "2", '"456"']
        )
        self.assertEqual(
            expand_decl(f1.ext[1].body.block_items[1]), ["StaticAssert", "3"]
        )
        self.assertEqual(len(f1.ext[1].body.block_items), 2)

    def test_unicode_character_escapes(self):
        for prefix in ("", "L", "u8", "u", "U"):
            for escape in (r"\u00e9", r"\U0001F600"):
                literal = f"{prefix}'{escape}'"
                with self.subTest(literal=literal):
                    self.assertEqual(
                        self.get_decl_init(f"int c = {literal};"),
                        ["Constant", "char", literal],
                    )
        self.assertEqual(
            self.get_decl_init(r"int c = '\u00e9a';"),
            ["Constant", "int", r"'\u00e9a'"],
        )

    def test_unified_string_literals(self):
        # simple string, for reference
        d1 = self.get_decl_init('char* s = "hello";')
        self.assertEqual(d1, ["Constant", "string", '"hello"'])

        d2 = self.get_decl_init('char* s = "hello" " world";')
        self.assertEqual(d2, ["Constant", "string", '"hello world"'])

        # the test case from issue 6
        d3 = self.parse(r"""
            int main() {
                fprintf(stderr,
                "Wrong Params?\n"
                "Usage:\n"
                "%s <binary_file_path>\n",
                argv[0]
                );
            }
        """)

        self.assertEqual(
            d3.ext[0].body.block_items[0].args.exprs[1].value,
            r'"Wrong Params?\nUsage:\n%s <binary_file_path>\n"',
        )

        d4 = self.get_decl_init('char* s = "" "foobar";')
        self.assertEqual(d4, ["Constant", "string", '"foobar"'])

        d5 = self.get_decl_init(r'char* s = "foo\"" "bar";')
        self.assertEqual(d5, ["Constant", "string", r'"foo\"bar"'])

        # Issue #392: concatenation must not turn two characters into an escape.
        d6 = self.get_decl_init(r'char* s = "\1" "23";')
        self.assertEqual(d6, ["Constant", "string", r'"\1" "23"'])

    def test_unified_wstring_literals(self):
        d1 = self.get_decl_init('char* s = L"hello" L"world";')
        self.assertEqual(d1, ["Constant", "string", 'L"helloworld"'])

        d2 = self.get_decl_init('char* s = L"hello " L"world" L" and I";')
        self.assertEqual(d2, ["Constant", "string", 'L"hello world and I"'])

        d3 = self.get_decl_init('char* s = u8"hello" u8"world";')
        self.assertEqual(d3, ["Constant", "string", 'u8"helloworld"'])

        d4 = self.get_decl_init('char* s = u8"a" u8"b" u8"c";')
        self.assertEqual(d4, ["Constant", "string", 'u8"abc"'])

        d5 = self.get_decl_init('char* s = u"hello" u"world";')
        self.assertEqual(d5, ["Constant", "string", 'u"helloworld"'])

    def test_unified_string_literals_whitespace(self):
        for prefix in ("", "L", "u8", "u", "U"):
            for separator in ("", " ", "\t", "\n    "):
                with self.subTest(prefix=prefix, separator=separator):
                    literals = separator.join(
                        f'{prefix}"{part}"' for part in ("hello ", "world", "!")
                    )
                    self.assertEqual(
                        self.get_decl_init(f"char* s = {literals};"),
                        ["Constant", "string", f'{prefix}"hello world!"'],
                    )

    def test_unified_string_literals_empty(self):
        cases = [
            (("", "", ""), ""),
            (("", "hello"), "hello"),
            (("hello", ""), "hello"),
            (("hello", "", " world"), "hello world"),
            (("", "hello", "", " world", ""), "hello world"),
        ]
        for prefix in ("", "L", "u8", "u", "U"):
            for parts, expected in cases:
                with self.subTest(prefix=prefix, parts=parts):
                    literals = " ".join(f'{prefix}"{part}"' for part in parts)
                    self.assertEqual(
                        self.get_decl_init(f"char* s = {literals};"),
                        ["Constant", "string", f'{prefix}"{expected}"'],
                    )

    def test_unified_string_literals_escapes(self):
        cases = [
            ((r'"foo\""', r'"\"bar"'), r'"foo\"\"bar"'),
            ((r'"\\"', r'"\n\t"', r'"\0end"'), r'"\\\n\t\0end"'),
        ]
        for prefix in ("", "L", "u8", "u", "U"):
            for parts, expected in cases:
                with self.subTest(prefix=prefix, parts=parts):
                    literals = " ".join(prefix + part for part in parts)
                    self.assertEqual(
                        self.get_decl_init(f"char* s = {literals};"),
                        ["Constant", "string", prefix + expected],
                    )

    def test_unified_string_literals_escape_boundaries(self):
        cases = [
            (r'"\1" "23"', r'"\1" "23"'),
            (r'"\12" "3"', r'"\12" "3"'),
            (r'"\123" "4"', r'"\1234"'),
            (r'"\1" "89"', r'"\189"'),
            (r'"\x1" "aF"', r'"\x1" "aF"'),
            (r'"\x0012" "3"', r'"\x0012" "3"'),
            (r'"\x1" "g"', r'"\x1g"'),
            (r'"\\x1" "a"', r'"\\x1a"'),
            (r'"\\1" "23"', r'"\\123"'),
            (r'"\\\x1" "a"', r'"\\\x1" "a"'),
            (r'"\u00e9" "a"', r'"\u00e9a"'),
            (r'"\U0001F600" "a"', r'"\U0001F600a"'),
            (r'"\1" "" "2" "3"', r'"\1" "23"'),
            (r'"\x1" "a\2" "3" "end"', r'"\x1" "a\2" "3end"'),
        ]
        for prefix in ("", "L", "u8", "u", "U"):
            for literals, expected in cases:
                with self.subTest(prefix=prefix, literals=literals):
                    ast = self.parse(f"void *s = {prefix}{literals};")
                    self.assertEqual(
                        expand_init(ast.ext[0].init),
                        ["Constant", "string", prefix + expected],
                    )
                    self.assert_coord(ast.ext[0].init, 1, 11)

        # A later encoding prefix still applies to the entire string.
        for prefix in ("L", "u8", "u", "U"):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    self.get_decl_init(r'void *s = "\x1" ' + prefix + '"a";'),
                    ["Constant", "string", prefix + r'"\x1" "a"'],
                )

    def test_unified_string_literals_trigraph_boundaries(self):
        for last in "=/'()!<>-":
            for literals in (f'"?" "?{last}"', f'"??" "{last}"'):
                with self.subTest(literals=literals):
                    self.assertEqual(
                        self.get_decl_init(f"char *s = {literals};"),
                        ["Constant", "string", literals],
                    )
        self.assertEqual(
            self.get_decl_init('char *s = "?" "?" "=";'),
            ["Constant", "string", '"??" "="'],
        )

    def test_unified_string_literals_expression_boundaries(self):
        ast = self.parse("""
            int f(void) {
                consume("a" "b", "c" "d");
                char *s[] = {"e" "f", "g" "h"};
                return ("i" "j")[1];
            }
        """)
        call, decl, ret = ast.ext[0].body.block_items
        self.assertIsInstance(call, FuncCall)
        self.assertEqual(
            expand_init(call.args),
            [["Constant", "string", '"ab"'], ["Constant", "string", '"cd"']],
        )
        self.assertEqual(
            expand_init(decl.init),
            [["Constant", "string", '"ef"'], ["Constant", "string", '"gh"']],
        )
        self.assertIsInstance(ret, Return)
        self.assertIsInstance(ret.expr, ArrayRef)
        self.assertEqual(expand_init(ret.expr.name), ["Constant", "string", '"ij"'])
        self.assertEqual(expand_init(ret.expr.subscript), ["Constant", "int", "1"])

    def test_unified_string_literals_static_assert(self):
        ast = self.parse('_Static_assert(1, "hello" " " "world");')
        self.assertEqual(
            expand_decl(ast.ext[0]), ["StaticAssert", "1", '"hello world"']
        )

    def test_unified_string_literals_mixed_prefix(self):
        for prefix in ("L", "u8", "u", "U"):
            for parts in (
                f'{prefix}"hello" " world"',
                f'"hello" {prefix}" world"',
                f'"hello" {prefix}" " "world"',
            ):
                with self.subTest(prefix=prefix, parts=parts):
                    self.assertEqual(
                        self.get_decl_init(f"void *s = {parts};"),
                        ["Constant", "string", f'{prefix}"hello world"'],
                    )

    def test_unified_string_literals_coord(self):
        for prefix in ("", "L", "u8", "u", "U"):
            with self.subTest(prefix=prefix):
                ast = self.parse(
                    f'char* s =\n    {prefix}"hello "\n    {prefix}"world";',
                    filename="strings.c",
                )
                self.assertEqual(
                    expand_init(ast.ext[0].init),
                    ["Constant", "string", f'{prefix}"hello world"'],
                )
                self.assert_coord(ast.ext[0].init, 2, 5, "strings.c")

    def test_inline_specifier(self):
        ps2 = self.parse("static inline void inlinefoo(void);")
        self.assertEqual(ps2.ext[0].funcspec, ["inline"])

    def test_noreturn_specifier(self):
        ps2 = self.parse("static _Noreturn void noreturnfoo(void);")
        self.assertEqual(ps2.ext[0].funcspec, ["_Noreturn"])

    # variable length array
    def test_vla(self):
        ps2 = self.parse(r"""
            int main() {
                int size;
                int var[size = 5];

                int var2[*];
            }
        """)
        self.assertIsInstance(ps2.ext[0].body.block_items[1].type.dim, Assignment)
        self.assertIsInstance(ps2.ext[0].body.block_items[2].type.dim, ID)

    def test_pragma(self):
        s1 = r"""
            #pragma bar
            void main() {
                #pragma foo
                for(;;) {}
                #pragma baz
                {
                    int i = 0;
                }
                #pragma
            }
            struct s {
            #pragma baz
            } s;
            _Pragma("other \"string\"")
            """
        s1_ast = self.parse(s1)
        self.assertIsInstance(s1_ast.ext[0], Pragma)
        self.assertEqual(s1_ast.ext[0].string, "bar")
        self.assertEqual(s1_ast.ext[0].coord.line, 2)

        self.assertIsInstance(s1_ast.ext[1].body.block_items[0], Pragma)
        self.assertEqual(s1_ast.ext[1].body.block_items[0].string, "foo")
        self.assertEqual(s1_ast.ext[1].body.block_items[0].coord.line, 4)

        self.assertIsInstance(s1_ast.ext[1].body.block_items[2], Pragma)
        self.assertEqual(s1_ast.ext[1].body.block_items[2].string, "baz")
        self.assertEqual(s1_ast.ext[1].body.block_items[2].coord.line, 6)

        self.assertIsInstance(s1_ast.ext[1].body.block_items[4], Pragma)
        self.assertEqual(s1_ast.ext[1].body.block_items[4].string, "")
        self.assertEqual(s1_ast.ext[1].body.block_items[4].coord.line, 10)

        self.assertIsInstance(s1_ast.ext[2].type.type.decls[0], Pragma)
        self.assertEqual(s1_ast.ext[2].type.type.decls[0].string, "baz")
        self.assertEqual(s1_ast.ext[2].type.type.decls[0].coord.line, 13)

        self.assertIsInstance(s1_ast.ext[3], Pragma)
        self.assertEqual(s1_ast.ext[3].string.value, r'"other \"string\""')
        self.assertEqual(s1_ast.ext[3].coord.line, 15)

    def test_pragma_before_declaration_semicolon_issue_478(self):
        ast = self.parse(
            """struct knote;
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wnullability-completeness"
struct klist { struct knote *slh_first; }
#pragma clang diagnostic pop
;
""",
            "event.h",
        )
        forward, push, ignored, decl, pop = ast.ext
        self.assertEqual(forward.type.name, "knote")
        self.assertIsInstance(push, Pragma)
        self.assertEqual(push.string, "clang diagnostic push")
        self.assertEqual(
            ignored.string, 'clang diagnostic ignored "-Wnullability-completeness"'
        )
        self.assertIsInstance(decl.type, Struct)
        self.assertEqual(decl.type.name, "klist")
        self.assertEqual(decl.type.decls[0].name, "slh_first")
        self.assertIsInstance(pop, Pragma)
        self.assertEqual(pop.string, "clang diagnostic pop")
        self.assertEqual(pop.coord.file, "event.h")
        self.assertEqual(pop.coord.line, 5)

    def test_pragma_before_initialized_declaration_semicolon(self):
        ast = self.parse('int a = 1, b = 2 _Pragma("first")\n#pragma second\n; int c;')
        a, b, first, second, c = ast.ext
        self.assertEqual(a.init.value, "1")
        self.assertEqual(b.init.value, "2")
        self.assertIsInstance(first, Pragma)
        self.assertEqual(first.string.value, '"first"')
        self.assertIsInstance(second, Pragma)
        self.assertEqual(second.string, "second")
        self.assertEqual(c.name, "c")

    def test_pragma_before_local_declaration_semicolon(self):
        ast = self.parse('void f(void) { int x _Pragma("after"); x = 1; }')
        decl, pragma, assignment = ast.ext[0].body.block_items
        self.assertEqual(decl.name, "x")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string.value, '"after"')
        self.assertIsInstance(assignment, Assignment)

    def test_pragma_before_typedef_semicolon(self):
        ast = self.parse("typedef int T\n#pragma after\n; T value;")
        typedef, pragma, decl = ast.ext
        self.assertIsInstance(typedef, Typedef)
        self.assertEqual(typedef.name, "T")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string, "after")
        self.assertEqual(decl.type.type.names, ["T"])

    def test_pragma_before_struct_member_semicolon(self):
        ast = self.parse('struct S { int x : 3 _Pragma("after"); int y; };')
        x, pragma, y = ast.ext[0].type.decls
        self.assertEqual(x.bitsize.value, "3")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string.value, '"after"')
        self.assertEqual(y.name, "y")

    def test_pragma_before_anonymous_union_member_semicolon(self):
        ast = self.parse('struct S { union { int x; } _Pragma("after"); int y; };')
        anonymous, pragma, y = ast.ext[0].type.decls
        self.assertIsNone(anonymous.name)
        self.assertIsInstance(anonymous.type, Union)
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string.value, '"after"')
        self.assertEqual(y.name, "y")

    def test_pragma_before_for_declaration_semicolon(self):
        ast = self.parse(
            'void f(void) { for (int i = 0 _Pragma("after"); i < 2; ++i) {} }'
        )
        loop = ast.ext[0].body.block_items[0]
        decl, pragma = loop.init.decls
        self.assertEqual(decl.name, "i")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string.value, '"after"')
        self.assertIsInstance(loop.cond, BinaryOp)
        self.assertEqual(loop.next.op, "++")

    def test_pragma_before_knr_declaration_semicolon(self):
        ast = self.parse('int f(x, y) int x _Pragma("after"); int y; { return x + y; }')
        x, pragma, y = ast.ext[0].param_decls
        self.assertEqual(x.name, "x")
        self.assertIsInstance(pragma, Pragma)
        self.assertEqual(pragma.string.value, '"after"')
        self.assertEqual(y.name, "y")

    def test_declaration_pragma_requires_semicolon(self):
        with self.assertRaises(ParseError):
            self.parse('struct S { int x; } _Pragma("after")')

    def test_declaration_pragma_does_not_end_declaration(self):
        with self.assertRaises(ParseError):
            self.parse('int x _Pragma("after") int y;')

    def test_c23_attributes_with_trailing_declaration_pragma(self):
        ast = c_parser.CParser(dialect="c23").parse(
            '[[deprecated]] auto x = 1 _Pragma("global"); '
            'void f(void) { [[maybe_unused]] auto y = 2 _Pragma("local"); }'
        )
        x, global_pragma, func = ast.ext
        self.assertEqual(x.attributes[0].attributes[0].name, "deprecated")
        self.assertEqual(global_pragma.string.value, '"global"')
        y, local_pragma = func.body.block_items
        self.assertEqual(y.attributes[0].attributes[0].name, "maybe_unused")
        self.assertEqual(local_pragma.string.value, '"local"')

    def test_c23_attributes_cannot_prefix_pragma(self):
        with self.assertRaises(ParseError):
            c_parser.CParser(dialect="c23").parse('[[deprecated]] _Pragma("after")')

    def test_pragmacomp_or_statement(self):
        s1 = r"""
            void main() {
                int sum = 0;
                for (int i; i < 3; i++)
                    #pragma omp critical
                    sum += 1;

                while(sum < 10)
                    #pragma omp critical
                    sum += 1;

                mylabel:
                    #pragma foo
                    sum += 10;

                if (sum > 10)
                    #pragma bar
                    #pragma baz
                    sum = 10;

                switch (sum)
                case 10:
                    #pragma foo
                    sum = 20;
            }
        """
        s1_ast = self.parse(s1)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[1], For)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[1].stmt, Compound)
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[1].stmt.block_items[0], Pragma
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[1].stmt.block_items[1], Assignment
        )
        self.assertIsInstance(s1_ast.ext[0].body.block_items[2], While)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[2].stmt, Compound)
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[2].stmt.block_items[0], Pragma
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[2].stmt.block_items[1], Assignment
        )
        self.assertIsInstance(s1_ast.ext[0].body.block_items[3], Label)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[3].stmt, Compound)
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[3].stmt.block_items[0], Pragma
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[3].stmt.block_items[1], Assignment
        )
        self.assertIsInstance(s1_ast.ext[0].body.block_items[4], If)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[4].iftrue, Compound)
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[4].iftrue.block_items[0], Pragma
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[4].iftrue.block_items[1], Pragma
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[4].iftrue.block_items[2], Assignment
        )
        self.assertIsInstance(s1_ast.ext[0].body.block_items[5], Switch)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[5].stmt.stmts[0], Compound)
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[5].stmt.stmts[0].block_items[0], Pragma
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[5].stmt.stmts[0].block_items[1], Assignment
        )


class TestCParser_static_assert(TestCParser_base):
    def test_aggregate_members(self):
        for kind in ("struct", "union"):
            with self.subTest(kind=kind):
                ast = self.parse(f"""
                    {kind} S {{
                        _Static_assert(1, "before");
                        int x;
                        _Static_assert(2);
                        struct {{
                            int y;
                            _Static_assert(3, "nested");
                        }} member;
                    }};
                """)
                members = ast.ext[0].type.decls
                self.assertEqual(
                    [type(n) for n in members], [StaticAssert, Decl, StaticAssert, Decl]
                )
                self.assertEqual(
                    expand_decl(members[0]), ["StaticAssert", "1", '"before"']
                )
                self.assertEqual(expand_decl(members[2]), ["StaticAssert", "2"])
                nested = members[3].type.type.decls
                self.assertEqual([type(n) for n in nested], [Decl, StaticAssert])
                self.assertEqual(
                    expand_decl(nested[1]), ["StaticAssert", "3", '"nested"']
                )

    def test_semicolon_consumption(self):
        ast = self.parse("""
            _Static_assert(1, "file");
            _Static_assert(2);
            void f(void) {
                _Static_assert(3, "block");
                _Static_assert(4);;
                int x;
            }
        """)
        self.assertEqual(
            [type(n) for n in ast.ext], [StaticAssert, StaticAssert, FuncDef]
        )
        self.assertEqual(
            [type(n) for n in ast.ext[2].body.block_items],
            [StaticAssert, StaticAssert, EmptyStatement, Decl],
        )

    def test_for_initializer(self):
        for args in ('1, "init"', "1"):
            with self.subTest(args=args):
                ast = self.parse(
                    f"void f(void) {{ for (_Static_assert({args}); ; ) {{}} }}"
                )
                loop = ast.ext[0].body.block_items[0]
                self.assertIsInstance(loop, For)
                self.assertIsInstance(loop.init, DeclList)
                self.assertEqual(len(loop.init.decls), 1)
                self.assertIsInstance(loop.init.decls[0], StaticAssert)
                self.assertIsNone(loop.cond)
                self.assertIsNone(loop.next)

    def test_message_literals(self):
        for prefix in ("", "L", "u8", "u", "U"):
            for message, expected in (
                (f'{prefix}""', f'{prefix}""'),
                (f'{prefix}"hello"', f'{prefix}"hello"'),
                (f'{prefix}"hello" {prefix}" world"', f'{prefix}"hello world"'),
                (f'"hello" {prefix}" " "world"', f'{prefix}"hello world"'),
            ):
                with self.subTest(message=message):
                    ast = self.parse(f"_Static_assert(1, {message});")
                    self.assertEqual(
                        expand_decl(ast.ext[0]), ["StaticAssert", "1", expected]
                    )

    def test_coordinates(self):
        ast = self.parse(
            '\n_Static_assert(\n  1,\n  u8"hello" " world"\n);\n',
            filename="assert.c",
        )
        assertion = ast.ext[0]
        self.assert_coord(assertion, 2, 1, "assert.c")
        self.assert_coord(assertion.cond, 3, 3, "assert.c")
        self.assert_coord(assertion.message, 4, 3, "assert.c")

    def test_missing_semicolon(self):
        for assertion in ('_Static_assert(1, "ok")', "_Static_assert(1)"):
            for source in (
                assertion,
                f"{assertion} int x;",
                f"{assertion} _Static_assert(1);",
                f"void f(void) {{ {assertion} }}",
                f"struct S {{ int x; {assertion} }};",
                f"union U {{ {assertion} int x; }};",
            ):
                with self.subTest(source=source):
                    self.assertRaises(ParseError, self.parse, source)

    def test_invalid_syntax(self):
        for args in (
            "",
            ', "message"',
            '1 "message"',
            "1,",
            "1, 2",
            "1, message",
            '1, ("message")',
            '1, "message",',
            '1, "message", "extra"',
            'x = 1, "message"',
        ):
            with self.subTest(args=args):
                self.assertRaises(ParseError, self.parse, f"_Static_assert({args});")

    def test_invalid_statement_positions(self):
        for statement in (
            'if (1) _Static_assert(1, "if");',
            'if (1) {} else _Static_assert(1, "else");',
            'while (1) _Static_assert(1, "while");',
            'do _Static_assert(1, "do"); while (0);',
            'for (;;) _Static_assert(1, "for");',
        ):
            with self.subTest(statement=statement):
                self.assertRaises(
                    ParseError, self.parse, f"void f(void) {{ {statement} }}"
                )


class TestCParser_generic_selection(TestCParser_base):
    def test_associations(self):
        selection = (
            self.parse("int v = _Generic(x, int: 1, default: 2, float: 3);").ext[0].init
        )
        self.assertIsInstance(selection, GenericSelection)
        self.assertEqual(expand_init(selection.expr), ["ID", "x"])
        self.assertEqual(len(selection.associations), 3)
        for association in selection.associations:
            self.assertIsInstance(association, GenericAssociation)
        first, default, last = selection.associations
        self.assertEqual(
            expand_decl(first.type),
            ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertIsNone(default.type)
        self.assertEqual(
            expand_decl(last.type),
            ["Typename", ["TypeDecl", ["IdentifierType", ["float"]]]],
        )
        self.assertEqual(
            [a.expr.value for a in selection.associations], ["1", "2", "3"]
        )

    def test_single_association(self):
        for association in ("int: 1", "default: 1"):
            with self.subTest(association=association):
                ast = self.parse(f"int v = _Generic(x, {association});")
                selection = ast.ext[0].init
                self.assertEqual(len(selection.associations), 1)
                self.assertEqual(selection.associations[0].expr.value, "1")

    def test_association_type_names(self):
        ast = self.parse("""
            typedef int T;
            int v = _Generic(x, T: 1, const T *: 2,
                             int (*)(int, int): 3, int[3]: 4, struct S: 5);
        """)
        types = [a.type for a in ast.ext[1].init.associations]
        for typ in types:
            self.assertIsInstance(typ, Typename)
        self.assertEqual(types[0].type.type.names, ["T"])
        self.assertEqual(
            expand_decl(types[1]),
            [
                "Typename",
                ["const"],
                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["T"]]]],
            ],
        )
        self.assertIsInstance(types[2].type, PtrDecl)
        self.assertIsInstance(types[2].type.type, FuncDecl)
        self.assertEqual(len(types[2].type.type.args.params), 2)
        self.assertIsInstance(types[3].type, ArrayDecl)
        self.assertEqual(types[3].type.dim.value, "3")
        self.assertIsInstance(types[4].type.type, Struct)
        self.assertEqual(types[4].type.type.name, "S")

    def test_typedef_scope(self):
        ast = self.parse("""
            typedef int T;
            int f(void) {
                int T;
                return _Generic(T, int: 1);
            }
            int v = _Generic(0, T: 2);
        """)
        selection = ast.ext[1].body.block_items[1].expr
        self.assertEqual(expand_init(selection.expr), ["ID", "T"])
        self.assertEqual(ast.ext[2].init.associations[0].type.type.type.names, ["T"])

    def test_assignment_and_conditional_expressions(self):
        selection = (
            self.parse("int v = _Generic(x = y, int: a = b, default: flag ? c : d);")
            .ext[0]
            .init
        )
        self.assertIsInstance(selection.expr, Assignment)
        self.assertEqual(selection.expr.lvalue.name, "x")
        self.assertEqual(selection.expr.rvalue.name, "y")
        assignment, conditional = [a.expr for a in selection.associations]
        self.assertIsInstance(assignment, Assignment)
        self.assertEqual(assignment.lvalue.name, "a")
        self.assertEqual(assignment.rvalue.name, "b")
        self.assertIsInstance(conditional, TernaryOp)
        self.assertEqual(conditional.iftrue.name, "c")
        self.assertEqual(conditional.iffalse.name, "d")

    def test_comma_boundaries(self):
        ast = self.parse(
            "int v = _Generic((a, b), int: (c, d), default: f(e, g)), w = 1;"
        )
        self.assertEqual([decl.name for decl in ast.ext], ["v", "w"])
        selection = ast.ext[0].init
        self.assertIsInstance(selection.expr, ExprList)
        self.assertEqual([n.name for n in selection.expr.exprs], ["a", "b"])
        self.assertEqual(len(selection.associations), 2)
        first, second = selection.associations
        self.assertIsInstance(first.expr, ExprList)
        self.assertEqual([n.name for n in first.expr.exprs], ["c", "d"])
        self.assertIsInstance(second.expr, FuncCall)
        self.assertEqual([n.name for n in second.expr.args.exprs], ["e", "g"])

    def test_nested_selections(self):
        selection = (
            self.parse("""
            int v = _Generic(_Generic(x, int: 0, default: 1),
                             int: _Generic(y, float: 2, default: 3), default: 4);
        """)
            .ext[0]
            .init
        )
        self.assertIsInstance(selection.expr, GenericSelection)
        self.assertEqual(selection.expr.expr.name, "x")
        self.assertEqual(len(selection.expr.associations), 2)
        inner = selection.associations[0].expr
        self.assertIsInstance(inner, GenericSelection)
        self.assertEqual(inner.expr.name, "y")
        self.assertEqual(len(inner.associations), 2)
        self.assertEqual(selection.associations[1].expr.value, "4")

    def test_expression_contexts(self):
        body = (
            self.parse("""
            int f(int x) {
                _Generic(x, int: 0);
                if (x) _Generic(x, default: 1);
                for (_Generic(x, default: 2); _Generic(x, default: 3);
                     _Generic(x, default: 4)) ;
                int a[_Generic(x, int: 5)];
                return _Generic(x, int: 6);
            }
        """)
            .ext[0]
            .body.block_items
        )
        expressions = [
            body[0],
            body[1].iftrue,
            body[2].init,
            body[2].cond,
            body[2].next,
            body[3].type.dim,
            body[4].expr,
        ]
        for i, expr in enumerate(expressions):
            self.assertIsInstance(expr, GenericSelection)
            self.assertEqual(expr.associations[0].expr.value, str(i))

    def test_postfix_and_precedence(self):
        for suffix, klass, attr in (
            ("(x)", FuncCall, "name"),
            ("[0]", ArrayRef, "name"),
            (".field", StructRef, "name"),
            ("->field", StructRef, "name"),
            ("++", UnaryOp, "expr"),
        ):
            with self.subTest(suffix=suffix):
                ast = self.parse(f"int v = _Generic(x, default: y){suffix};")
                expr = ast.ext[0].init
                self.assertIsInstance(expr, klass)
                self.assertIsInstance(getattr(expr, attr), GenericSelection)
        expr = self.parse("int v = 1 + _Generic(x, int: 2) * 3;").ext[0].init
        self.assertEqual(expr.op, "+")
        self.assertEqual(expr.right.op, "*")
        self.assertIsInstance(expr.right.left, GenericSelection)

    def test_coordinates(self):
        selection = (
            self.parse(
                "int v =\n  _Generic(x,\n    const int *: 1,\n    default: 2);\n",
                filename="generic.c",
            )
            .ext[0]
            .init
        )
        self.assert_coord(selection, 2, 3, "generic.c")
        self.assert_coord(selection.expr, 2, 12, "generic.c")
        self.assert_coord(selection.associations[0], 3, 5, "generic.c")
        self.assert_coord(selection.associations[0].expr, 3, 18, "generic.c")
        self.assert_coord(selection.associations[1], 4, 5, "generic.c")

    def test_invalid_syntax(self):
        for expr in (
            "_Generic()",
            "_Generic(x)",
            "_Generic(x,)",
            "_Generic(, int: 1)",
            "_Generic(x int: 1)",
            "_Generic(x, int 1)",
            "_Generic(x, int:)",
            "_Generic(x, int: 1,)",
            "_Generic(x, default 1)",
            "_Generic(x, default:)",
            "_Generic(x, unknown_type: 1)",
            "_Generic(x, int value: 1)",
            "_Generic(x, int: 1, 2)",
            "_Generic x, int: 1",
        ):
            with self.subTest(expr=expr):
                self.assertRaises(ParseError, self.parse, f"int v = {expr};")
        for source in (
            "int v = _Generic(",
            "int v = _Generic(x,",
            "int v = _Generic(x, int:",
            "int v = _Generic(x, int: 1",
        ):
            with self.subTest(source=source):
                self.assertRaises(ParseError, self.parse, source)


class TestCParser_dialects(unittest.TestCase):
    def test_legacy_identifiers(self):
        source = """
            typedef int bool;
            bool true = 1, false = 0;
            int alignas, alignof, static_assert, thread_local;
            int constexpr, typeof, typeof_unqual;
            void *nullptr;
            _Bool b = true;
            void *p = nullptr;
        """
        for parser in (c_parser.CParser(), c_parser.CParser(dialect="legacy")):
            ast = parser.parse(source)
            self.assertIsInstance(ast.ext[0], Typedef)
            self.assertEqual(ast.ext[1].type.type.names, ["bool"])
            self.assertIsInstance(ast.ext[-2].init, ID)
            self.assertEqual(ast.ext[-2].init.name, "true")
            self.assertIsInstance(ast.ext[-1].init, ID)
            self.assertEqual(ast.ext[-1].init.name, "nullptr")

    def test_c23_keyword_aliases(self):
        parser = c_parser.CParser(dialect="c23")
        ast = parser.parse("""
            alignas(16) thread_local bool flag = false;
            int alignment = alignof(bool);
            _Alignas(16) _Thread_local _Bool old_flag = 0;
            int old_alignment = _Alignof(_Bool);
        """)
        flag, alignment, old_flag, old_alignment = ast.ext
        self.assertEqual(flag.type.type.names, ["bool"])
        self.assertEqual(flag.storage, ["thread_local"])
        self.assertEqual(flag.align[0].alignment.value, "16")
        self.assertEqual(alignment.init.op, "alignof")
        self.assertEqual(alignment.init.expr.type.type.names, ["bool"])
        self.assertEqual(old_flag.type.type.names, ["_Bool"])
        self.assertEqual(old_flag.storage, ["_Thread_local"])
        self.assertEqual(old_alignment.init.op, "_Alignof")

    def test_c23_constexpr(self):
        parser = c_parser.CParser(dialect="c23")
        declarations = """
            constexpr T limit = 16;
            int constexpr next = limit + 1;
            static constexpr double scale = 0.5;
            constexpr bool enabled = true;
            constexpr int values[] = {1, 2};
        """
        for block_scope in (False, True):
            with self.subTest(block_scope=block_scope):
                source = declarations
                if block_scope:
                    source = "void f(void) {" + declarations + "}"
                ast = parser.parse("typedef int T;" + source)
                decls = ast.ext[1].body.block_items if block_scope else ast.ext[1:]
                limit, next_value, scale, enabled, values = decls
                for decl in (limit, next_value, enabled, values):
                    self.assertEqual(decl.storage, ["constexpr"])
                self.assertEqual(scale.storage, ["static", "constexpr"])
                self.assertEqual(limit.type.type.names, ["T"])
                self.assertEqual(expand_init(limit.init), ["Constant", "int", "16"])
                self.assertIsInstance(next_value.init, BinaryOp)
                self.assertEqual(next_value.init.left.name, "limit")
                self.assertEqual(scale.init.value, "0.5")
                self.assertEqual(
                    expand_init(enabled.init), ["Constant", "bool", "true"]
                )
                self.assertIsInstance(values.type, ArrayDecl)
                self.assertEqual([expr.value for expr in values.init.exprs], ["1", "2"])

    def test_constexpr_dialect(self):
        for parser in (c_parser.CParser(), c_parser.CParser(dialect="legacy")):
            ast = parser.parse("int constexpr = 1; int x = constexpr;")
            self.assertEqual(ast.ext[0].name, "constexpr")
            self.assertIsInstance(ast.ext[1].init, ID)
            self.assertEqual(ast.ext[1].init.name, "constexpr")
            self.assertRaises(ParseError, parser.parse, "constexpr int x = 1;")

    def test_c23_static_assert_contexts(self):
        parser = c_parser.CParser(dialect="c23")
        ast = parser.parse("""
            static_assert(true);
            struct S { static_assert(true, "member"); bool value; };
            void f(void) { static_assert(!false); _Static_assert(true); }
        """)
        assertions = [
            ast.ext[0],
            ast.ext[1].type.decls[0],
            *ast.ext[2].body.block_items,
        ]
        for node in assertions:
            self.assertIsInstance(node, StaticAssert)
        self.assertIsNone(assertions[0].message)
        self.assertEqual(assertions[1].message.value, '"member"')

    def test_c23_predefined_constants(self):
        parser = c_parser.CParser(dialect="c23")
        ast = parser.parse(
            "bool t = true;\nbool f = false;\nvoid *p = nullptr;", "c23.c"
        )
        expected = [
            ("bool", "true", 10),
            ("bool", "false", 10),
            ("nullptr_t", "nullptr", 11),
        ]
        for line, (decl, (typ, value, column)) in enumerate(
            zip(ast.ext, expected), start=1
        ):
            node = decl.init
            self.assertIsInstance(node, Constant)
            self.assertEqual((node.type, node.value), (typ, value))
            self.assertEqual(str(node.coord), f"c23.c:{line}:{column}")

    def test_c23_constants_start_statements(self):
        parser = c_parser.CParser(dialect="c23")
        ast = parser.parse("""
            void f(void) {
                true; false; nullptr;
                label: true;
                if (true) false;
                while (false) nullptr;
            }
        """)
        stmts = ast.ext[0].body.block_items
        for node, value in zip(stmts[:3], ("true", "false", "nullptr")):
            self.assertIsInstance(node, Constant)
            self.assertEqual(node.value, value)
        self.assertIsInstance(stmts[3].stmt, Constant)
        self.assertIsInstance(stmts[4].iftrue, Constant)
        self.assertIsInstance(stmts[5].stmt, Constant)

    def test_c23_reserved_identifiers(self):
        parser = c_parser.CParser(dialect="c23")
        for source in (
            "typedef int bool; bool x;",
            "int true;",
            "int false;",
            "void *nullptr;",
            "int *alignas;",
            "int *alignof;",
            "int *static_assert;",
            "int *thread_local;",
            "int *constexpr;",
            "int *typeof;",
            "int *typeof_unqual;",
            "int *_BitInt;",
            "int *_Decimal32;",
            "int *_Decimal64;",
            "int *_Decimal128;",
        ):
            with self.subTest(source=source):
                self.assertRaises(ParseError, parser.parse, source)

    def test_c23_unsupported_keywords_are_reserved(self):
        parser = c_parser.CParser(dialect="c23")
        legacy = c_parser.CParser()
        self.assertEqual(legacy.parse("int _Imaginary;").ext[0].name, "_Imaginary")
        self.assertRaises(ParseError, parser.parse, "int _Imaginary;")
        self.assertRaises(ParseError, parser.parse, "_Imaginary double x;")

    def test_dialect_isolation_and_parser_reuse(self):
        legacy = c_parser.CParser()
        c23 = c_parser.CParser(dialect="c23")
        another_legacy = c_parser.CParser(dialect="legacy")
        for _ in range(2):
            for parser, expected_type in (
                (legacy, ID),
                (c23, Constant),
                (another_legacy, ID),
            ):
                with self.subTest(expected_type=expected_type):
                    ast = parser.parse("_Bool b = true; void *p = nullptr;")
                    for decl in ast.ext:
                        self.assertIsInstance(decl.init, expected_type)
            legacy.parse("typedef int bool; bool x;")
            self.assertRaises(ParseError, c23.parse, "typedef int bool;")

    def test_invalid_dialect(self):
        with self.assertRaisesRegex(ValueError, "Unknown dialect"):
            c_parser.CParser(dialect="c99")  # ty: ignore[invalid-argument-type]


class TestCParser_c23_grammar(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_ellipsis_only_declaration(self):
        decl = self.parse("void f(...);", filename="variadic.c").ext[0]
        self.assertIsInstance(decl.type, FuncDecl)
        self.assertIsInstance(decl.type.args, ParamList)
        self.assertEqual(len(decl.type.args.params), 1)
        self.assertIsInstance(decl.type.args.params[0], EllipsisParam)
        self.assert_coord(decl.type.args, 1, 8, "variadic.c")
        self.assert_coord(decl.type.args.params[0], 1, 8, "variadic.c")

    def test_ellipsis_only_definition(self):
        ast = self.parse("typedef int T; int f(...) { T value = 0; return value; }")
        func = ast.ext[1]
        self.assertIsInstance(func, FuncDef)
        self.assertEqual(len(func.decl.type.args.params), 1)
        self.assertIsInstance(func.decl.type.args.params[0], EllipsisParam)
        self.assertEqual(func.body.block_items[0].type.type.names, ["T"])
        self.assertIsInstance(func.body.block_items[1], Return)

    def test_ellipsis_only_function_pointer(self):
        decl = self.parse("void (*callback)(...);").ext[0]
        self.assertIsInstance(decl.type, PtrDecl)
        self.assertIsInstance(decl.type.type, FuncDecl)
        self.assertEqual(len(decl.type.type.args.params), 1)
        self.assertIsInstance(decl.type.type.args.params[0], EllipsisParam)

    def test_ellipsis_only_abstract_function_parameter(self):
        decl = self.parse("void f(int (...));").ext[0]
        param = decl.type.args.params[0]
        self.assertIsInstance(param, Typename)
        self.assertIsInstance(param.type, FuncDecl)
        self.assertEqual(len(param.type.args.params), 1)
        self.assertIsInstance(param.type.args.params[0], EllipsisParam)

    def test_ellipsis_only_abstract_function_pointer_parameter(self):
        decl = self.parse("void f(int (*)(...));").ext[0]
        param = decl.type.args.params[0]
        self.assertIsInstance(param, Typename)
        self.assertIsInstance(param.type, PtrDecl)
        self.assertIsInstance(param.type.type, FuncDecl)
        self.assertEqual(len(param.type.type.args.params), 1)
        self.assertIsInstance(param.type.type.args.params[0], EllipsisParam)

    def test_ellipsis_only_function_pointer_cast(self):
        decl = self.parse("void (*callback)(...) = (void (*)(...))0;").ext[0]
        self.assertIsInstance(decl.init, Cast)
        pointer = decl.init.to_type.type
        self.assertIsInstance(pointer, PtrDecl)
        self.assertIsInstance(pointer.type, FuncDecl)
        self.assertEqual(len(pointer.type.args.params), 1)
        self.assertIsInstance(pointer.type.args.params[0], EllipsisParam)

    def test_ellipsis_only_rejected_in_legacy(self):
        parser = c_parser.CParser(dialect="legacy")
        with self.assertRaisesRegex(
            ParseError, "Ellipsis-only parameter lists require C23"
        ):
            parser.parse("void f(...);")
        with self.assertRaisesRegex(
            ParseError, "Ellipsis-only parameter lists require C23"
        ):
            parser.parse("void f(...) {}")
        with self.assertRaisesRegex(
            ParseError, "Ellipsis-only parameter lists require C23"
        ):
            parser.parse("void (*callback)(...);")
        with self.assertRaisesRegex(
            ParseError, "Ellipsis-only parameter lists require C23"
        ):
            parser.parse("void f(int (...));")
        with self.assertRaisesRegex(
            ParseError, "Ellipsis-only parameter lists require C23"
        ):
            parser.parse("void f(int (*)(...));")
        with self.assertRaisesRegex(
            ParseError, "Ellipsis-only parameter lists require C23"
        ):
            parser.parse("void f(void) { (void (*)(...))0; }")

    def test_invalid_ellipsis_parameter_lists(self):
        self.assertRaises(ParseError, self.parse, "void f(, ...);")
        self.assertRaises(ParseError, self.parse, "void f(...,);")
        self.assertRaises(ParseError, self.parse, "void f(..., int x);")
        self.assertRaises(ParseError, self.parse, "void f(... ...);")
        self.assertRaises(ParseError, self.parse, "void f(int x ...);")
        self.assertRaises(ParseError, self.parse, "void f(...")
        self.assertRaises(ParseError, self.parse, "void f(int (...,));")
        self.assertRaises(ParseError, self.parse, "void f(int (*)(..., int));")

    def test_named_variadic_parameter_list(self):
        decl = self.parse("void f(int x, ...);").ext[0]
        self.assertEqual(len(decl.type.args.params), 2)
        self.assertEqual(decl.type.args.params[0].name, "x")
        self.assertIsInstance(decl.type.args.params[1], EllipsisParam)

        parser = c_parser.CParser(dialect="legacy")
        decl = parser.parse("void f(int x, ...);").ext[0]
        self.assertEqual(len(decl.type.args.params), 2)
        self.assertEqual(decl.type.args.params[0].name, "x")
        self.assertIsInstance(decl.type.args.params[1], EllipsisParam)

    def test_empty_initializers(self):
        ast = self.parse("""
            int scalar = {};
            int array[3] = {};
            struct S { int value; } object = {};
        """)
        scalar, array, obj = ast.ext
        self.assertIsInstance(scalar.init, InitList)
        self.assertEqual(scalar.init.exprs, [])
        self.assertIsInstance(array.init, InitList)
        self.assertEqual(array.init.exprs, [])
        self.assertIsInstance(obj.init, InitList)
        self.assertEqual(obj.init.exprs, [])

    def test_empty_compound_literals(self):
        ast = self.parse("int scalar = (int){}; int *array = (int[3]){};")
        scalar, array = ast.ext
        self.assertIsInstance(scalar.init, CompoundLiteral)
        self.assertEqual(scalar.init.type.type.type.names, ["int"])
        self.assertEqual(scalar.init.init.exprs, [])
        self.assertIsInstance(array.init, CompoundLiteral)
        self.assertIsInstance(array.init.type.type, ArrayDecl)
        self.assertEqual(array.init.init.exprs, [])

    def test_labels_before_declarations_and_at_block_end(self):
        func = self.parse("void f(void) { start: int x = 1; end: }").ext[0]
        start, decl, end = func.body.block_items
        self.assertIsInstance(start, Label)
        self.assertEqual(start.name, "start")
        self.assertIsInstance(start.stmt, EmptyStatement)
        self.assertIsInstance(decl, Decl)
        self.assertEqual(decl.name, "x")
        self.assertIsInstance(end, Label)
        self.assertEqual(end.name, "end")
        self.assertIsInstance(end.stmt, EmptyStatement)

    def test_case_before_declaration_and_trailing_default(self):
        func = self.parse("""
            void f(int x) {
                switch (x) { case 1: int y = 2; default: }
            }
        """).ext[0]
        case, default = func.body.block_items[0].stmt.block_items
        self.assertIsInstance(case, Case)
        self.assertEqual(case.expr.value, "1")
        self.assertIsInstance(case.stmts[0], EmptyStatement)
        self.assertIsInstance(case.stmts[1], Decl)
        self.assertEqual(case.stmts[1].name, "y")
        self.assertIsInstance(default, Default)
        self.assertIsInstance(default.stmts[0], EmptyStatement)

    def test_default_before_declaration_and_trailing_case(self):
        func = self.parse("""
            void f(int x) {
                switch (x) { default: int y = 2; case 1: }
            }
        """).ext[0]
        default, case = func.body.block_items[0].stmt.block_items
        self.assertIsInstance(default, Default)
        self.assertIsInstance(default.stmts[0], EmptyStatement)
        self.assertIsInstance(default.stmts[1], Decl)
        self.assertEqual(default.stmts[1].name, "y")
        self.assertIsInstance(case, Case)
        self.assertEqual(case.expr.value, "1")
        self.assertIsInstance(case.stmts[0], EmptyStatement)

    def test_unnamed_parameters_in_definition(self):
        func = self.parse("int f(int, const int *, int (*)(int)) { return 0; }").ext[0]
        scalar, pointer, callback = func.decl.type.args.params
        self.assertIsInstance(scalar, Typename)
        self.assertEqual(scalar.type.type.names, ["int"])
        self.assertIsNone(scalar.type.declname)
        self.assertIsInstance(pointer, Typename)
        self.assertIsInstance(pointer.type, PtrDecl)
        self.assertEqual(pointer.type.type.quals, ["const"])
        self.assertIsNone(pointer.type.type.declname)
        self.assertIsInstance(callback, Typename)
        self.assertIsInstance(callback.type, PtrDecl)
        self.assertIsInstance(callback.type.type, FuncDecl)
        self.assertIsNone(callback.type.type.type.declname)
        self.assertIsInstance(func.body.block_items[0], Return)


class TestCParser_c23_compound_literals(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_storage_specifiers(self):
        ast = self.parse("""
            int *p = &(static int){1};
            int value = (constexpr int){42};
            void f(void) { (register int){2}; }
        """)
        static = ast.ext[0].init.expr
        self.assertIsInstance(static, CompoundLiteral)
        self.assertEqual(static.storage, ["static"])
        self.assertEqual(static.type.type.type.names, ["int"])
        self.assertEqual(static.init.exprs[0].value, "1")
        constexpr = ast.ext[1].init
        self.assertEqual(constexpr.storage, ["constexpr"])
        self.assertEqual(constexpr.init.exprs[0].value, "42")
        register = ast.ext[2].body.block_items[0]
        self.assertIsInstance(register, CompoundLiteral)
        self.assertEqual(register.storage, ["register"])

    def test_thread_local_storage(self):
        func = self.parse("""
            void f(void) {
                (thread_local int){1};
                (_Thread_local int){2};
                (static thread_local int){3};
                (thread_local static int){4};
            }
        """).ext[0]
        thread, old_spelling, static_first, thread_first = func.body.block_items
        self.assertEqual(thread.storage, ["thread_local"])
        self.assertEqual(old_spelling.storage, ["_Thread_local"])
        self.assertEqual(static_first.storage, ["static", "thread_local"])
        self.assertEqual(thread_first.storage, ["thread_local", "static"])

    def test_storage_and_type_qualifiers(self):
        literal = (
            self.parse("int x = (static constexpr const unsigned long){42};")
            .ext[0]
            .init
        )
        self.assertEqual(literal.storage, ["static", "constexpr"])
        self.assertEqual(literal.type.quals, ["const"])
        self.assertEqual(literal.type.type.quals, ["const"])
        self.assertEqual(literal.type.type.type.names, ["unsigned", "long"])

    def test_typedef_and_abstract_types(self):
        ast = self.parse("""
            typedef int T;
            T *array = (static T[]){1, 2};
            T *pointer = (static T *){0};
        """)
        array = ast.ext[1].init
        self.assertEqual(array.storage, ["static"])
        self.assertIsInstance(array.type.type, ArrayDecl)
        self.assertIsNone(array.type.type.dim)
        self.assertEqual(array.type.type.type.type.names, ["T"])
        pointer = ast.ext[2].init
        self.assertEqual(pointer.storage, ["static"])
        self.assertIsInstance(pointer.type.type, PtrDecl)
        self.assertEqual(pointer.type.type.type.type.names, ["T"])

    def test_empty_and_designated_initializers(self):
        ast = self.parse("""
            struct S { int value; };
            struct S empty = (static struct S){};
            struct S designated = (static struct S){.value = 1,};
        """)
        empty = ast.ext[1].init
        self.assertEqual(empty.storage, ["static"])
        self.assertIsInstance(empty.init, InitList)
        self.assertEqual(empty.init.exprs, [])
        designated = ast.ext[2].init.init.exprs[0]
        self.assertIsInstance(designated, NamedInitializer)
        self.assertEqual(designated.name[0].name, "value")
        self.assertEqual(designated.expr.value, "1")

    def test_member_access(self):
        ast = self.parse("""
            struct S { int value; };
            int value = (static struct S){.value = 2}.value;
            int zero = (static struct S){}.value;
        """)
        member = ast.ext[1].init
        self.assertIsInstance(member, StructRef)
        self.assertEqual(member.type, ".")
        self.assertEqual(member.field.name, "value")
        self.assertIsInstance(member.name, CompoundLiteral)
        self.assertEqual(member.name.storage, ["static"])
        empty_member = ast.ext[2].init
        self.assertIsInstance(empty_member, StructRef)
        self.assertEqual(empty_member.name.init.exprs, [])

    def test_array_indexing(self):
        ast = self.parse("""
            int value = (static int[]){1, 2}[1];
            int zero = (static int[2]){}[0];
        """)
        indexed = ast.ext[0].init
        self.assertIsInstance(indexed, ArrayRef)
        self.assertEqual(indexed.subscript.value, "1")
        self.assertIsInstance(indexed.name, CompoundLiteral)
        self.assertEqual(indexed.name.storage, ["static"])
        self.assertEqual(len(indexed.name.init.exprs), 2)
        empty_indexed = ast.ext[1].init
        self.assertIsInstance(empty_indexed, ArrayRef)
        self.assertEqual(empty_indexed.name.init.exprs, [])

    def test_other_postfix_operators(self):
        ast = self.parse("""
            struct S { int value; } object;
            int callback(void);
            void f(void) {
                (static struct S *){&object}->value;
                (static int (*)(void)){callback}();
                (register int){1}++;
                (register int){2}--;
            }
        """)
        arrow, call, increment, decrement = ast.ext[2].body.block_items
        self.assertIsInstance(arrow, StructRef)
        self.assertEqual(arrow.type, "->")
        self.assertIsInstance(arrow.name, CompoundLiteral)
        self.assertIsInstance(call, FuncCall)
        self.assertIsInstance(call.name, CompoundLiteral)
        self.assertEqual(call.name.storage, ["static"])
        self.assertEqual(increment.op, "p++")
        self.assertEqual(increment.expr.storage, ["register"])
        self.assertEqual(decrement.op, "p--")
        self.assertEqual(decrement.expr.storage, ["register"])

    def test_sizeof_compound_literal(self):
        ast = self.parse("""
            int array_size = sizeof (static int[3]){};
            int element_size = sizeof (static int[]){1, 2}[0];
            int ordinary = sizeof (int){1};
            int type_size = sizeof(int);
        """)
        array_size = ast.ext[0].init
        self.assertEqual(array_size.op, "sizeof")
        self.assertIsInstance(array_size.expr, CompoundLiteral)
        self.assertEqual(array_size.expr.storage, ["static"])
        self.assertEqual(array_size.expr.init.exprs, [])
        element_size = ast.ext[1].init
        self.assertIsInstance(element_size.expr, ArrayRef)
        self.assertIsInstance(element_size.expr.name, CompoundLiteral)
        self.assertIsInstance(ast.ext[2].init.expr, CompoundLiteral)
        self.assertEqual(ast.ext[2].init.expr.storage, [])
        self.assertIsInstance(ast.ext[3].init.expr, Typename)

    def test_nested_initializer(self):
        literal = (
            self.parse("""
            struct S { int *values; } object =
                (static struct S){.values = (static int[]){1, 2}};
        """)
            .ext[0]
            .init
        )
        self.assertEqual(literal.storage, ["static"])
        nested = literal.init.exprs[0].expr
        self.assertIsInstance(nested, CompoundLiteral)
        self.assertEqual(nested.storage, ["static"])
        self.assertIsInstance(nested.type.type, ArrayDecl)
        self.assertEqual(len(nested.init.exprs), 2)

    def test_cast_of_compound_literal(self):
        expr = self.parse("int value = (int)(constexpr unsigned int){42};").ext[0].init
        self.assertIsInstance(expr, Cast)
        self.assertEqual(expr.to_type.type.type.names, ["int"])
        self.assertIsInstance(expr.expr, CompoundLiteral)
        self.assertEqual(expr.expr.storage, ["constexpr"])

    def test_storage_rejected_in_legacy(self):
        parser = c_parser.CParser(dialect="legacy")
        with self.assertRaisesRegex(ParseError, "compound literals require C23"):
            parser.parse("int value = (static int){1};")
        with self.assertRaisesRegex(ParseError, "compound literals require C23"):
            parser.parse("void f(void) { (register int){1}; }")
        with self.assertRaisesRegex(ParseError, "compound literals require C23"):
            parser.parse("void f(void) { (_Thread_local int){1}; }")

    def test_storage_requires_braced_initializer(self):
        with self.assertRaisesRegex(
            ParseError, "require a compound literal initializer"
        ):
            self.parse("int value = (static int)1;")
        with self.assertRaisesRegex(
            ParseError, "require a compound literal initializer"
        ):
            self.parse("int value = sizeof(static int);")
        with self.assertRaisesRegex(
            ParseError, "require a compound literal initializer"
        ):
            self.parse("int value = (constexpr int);")
        self.assertRaises(ParseError, self.parse, "int value = alignof(static int);")
        self.assertRaises(ParseError, self.parse, "typeof(static int) value;")

    def test_invalid_syntax(self):
        self.assertRaises(ParseError, self.parse, "int value = (static){1};")
        self.assertRaises(ParseError, self.parse, "int value = (static unknown){1};")
        self.assertRaises(ParseError, self.parse, "int value = (const static int){1};")
        self.assertRaises(ParseError, self.parse, "int value = (int static){1};")
        self.assertRaises(ParseError, self.parse, "int value = (static int name){1};")
        self.assertRaises(ParseError, self.parse, "int value = (static int){,};")
        self.assertRaises(ParseError, self.parse, "int value = (static int){1;")

    def test_legacy_compound_literal_postfix(self):
        parser = c_parser.CParser(dialect="legacy")
        ast = parser.parse("""
            struct S { int value; };
            int member = (struct S){1}.value;
            int empty_member = (struct S){}.value;
            int element = (int[]){1, 2}[0];
            int empty_element = (int[2]){}[0];
            int size = sizeof (int[]){1, 2};
        """)
        member = ast.ext[1].init
        self.assertIsInstance(member, StructRef)
        self.assertEqual(member.name.storage, [])
        self.assertIsInstance(ast.ext[2].init, StructRef)
        self.assertEqual(ast.ext[2].init.name.init.exprs, [])
        self.assertIsInstance(ast.ext[3].init, ArrayRef)
        self.assertEqual(ast.ext[3].init.name.storage, [])
        self.assertIsInstance(ast.ext[4].init, ArrayRef)
        self.assertEqual(ast.ext[4].init.name.init.exprs, [])
        self.assertIsInstance(ast.ext[5].init.expr, CompoundLiteral)


class TestCParser_fixed_enum(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_named_definition(self):
        enum = self.parse("enum E : unsigned char { A = 1, B, };").ext[0].type
        self.assertIsInstance(enum, Enum)
        self.assertEqual(enum.name, "E")
        self.assertIsInstance(enum.underlying_type, Typename)
        self.assertIsNone(enum.underlying_type.name)
        self.assertIsInstance(enum.underlying_type.type, TypeDecl)
        self.assertEqual(enum.underlying_type.type.type.names, ["unsigned", "char"])
        self.assertEqual(enum.values.enumerators[0].name, "A")
        self.assertEqual(enum.values.enumerators[0].value.value, "1")
        self.assertEqual(enum.values.enumerators[1].name, "B")
        self.assertIsNone(enum.values.enumerators[1].value)

    def test_forward_declaration_and_reference(self):
        ast = self.parse("""
            enum E : unsigned int;
            enum E : unsigned int { A };
            enum E value = A;
        """)
        forward, definition, variable = ast.ext
        self.assertIsNone(forward.type.values)
        self.assertEqual(forward.type.name, "E")
        self.assertEqual(
            forward.type.underlying_type.type.type.names, ["unsigned", "int"]
        )
        self.assertIsInstance(definition.type.values, EnumeratorList)
        self.assertEqual(
            definition.type.underlying_type.type.type.names, ["unsigned", "int"]
        )
        self.assertIsNone(variable.type.type.underlying_type)
        self.assertEqual(variable.type.type.name, "E")
        self.assertIsInstance(variable.init, ID)
        self.assertEqual(variable.init.name, "A")

    def test_anonymous_definition_with_declarators(self):
        ast = self.parse("enum : unsigned short { A } first = A, *second;")
        first, second = ast.ext
        enum = first.type.type
        self.assertIsInstance(enum, Enum)
        self.assertIsNone(enum.name)
        self.assertEqual(enum.underlying_type.type.type.names, ["unsigned", "short"])
        self.assertEqual(first.init.name, "A")
        self.assertIsInstance(second.type, PtrDecl)
        self.assertIs(second.type.type.type, enum)

    def test_typedef_underlying_type_and_tag(self):
        ast = self.parse("""
            typedef unsigned char Byte;
            enum Byte : Byte { A };
            Byte value;
        """)
        enum = ast.ext[1].type
        self.assertEqual(enum.name, "Byte")
        self.assertEqual(enum.underlying_type.type.type.names, ["Byte"])
        self.assertEqual(ast.ext[2].type.type.names, ["Byte"])

    def test_typedef_of_fixed_enum(self):
        ast = self.parse("typedef enum : unsigned short { A } E; E value;")
        typedef = ast.ext[0]
        self.assertIsInstance(typedef, Typedef)
        self.assertEqual(typedef.name, "E")
        self.assertIsNone(typedef.type.type.name)
        self.assertEqual(
            typedef.type.type.underlying_type.type.type.names, ["unsigned", "short"]
        )
        self.assertEqual(ast.ext[1].type.type.names, ["E"])

    def test_qualified_underlying_type(self):
        decl = self.parse(
            "const enum E : volatile unsigned int const { A } value;"
        ).ext[0]
        self.assertEqual(decl.quals, ["const"])
        underlying = decl.type.type.underlying_type
        self.assertEqual(underlying.quals, ["volatile", "const"])
        self.assertEqual(underlying.type.quals, ["volatile", "const"])
        self.assertEqual(underlying.type.type.names, ["unsigned", "int"])

    def test_typeof_underlying_types(self):
        ast = self.parse("""
            enum E : typeof(unsigned int) { A };
            enum F : typeof_unqual(A + 1) { B };
        """)
        first = ast.ext[0].type.underlying_type.type.type
        self.assertIsInstance(first, TypeOf)
        self.assertEqual(first.op, "typeof")
        self.assertIsInstance(first.expr, Typename)
        self.assertEqual(first.expr.type.type.names, ["unsigned", "int"])
        second = ast.ext[1].type.underlying_type.type.type
        self.assertEqual(second.op, "typeof_unqual")
        self.assertIsInstance(second.expr, BinaryOp)
        self.assertEqual(second.expr.left.name, "A")

    def test_atomic_underlying_type(self):
        enum = self.parse("enum E : _Atomic(unsigned int) { A };").ext[0].type
        self.assertEqual(enum.underlying_type.quals, ["_Atomic"])
        self.assertEqual(enum.underlying_type.type.quals, ["_Atomic"])
        self.assertEqual(enum.underlying_type.type.type.names, ["unsigned", "int"])

    def test_enumerator_expressions_are_preserved(self):
        enum = (
            self.parse("""
            enum E : unsigned long long {
                A = 1ULL << 40, B = 0xffffffffffffffffULL, C
            };
        """)
            .ext[0]
            .type
        )
        a, b, c = enum.values.enumerators
        self.assertIsInstance(a.value, BinaryOp)
        self.assertEqual(a.value.op, "<<")
        self.assertEqual(a.value.left.value, "1ULL")
        self.assertEqual(a.value.right.value, "40")
        self.assertEqual(b.value.value, "0xffffffffffffffffULL")
        self.assertIsNone(c.value)

    def test_definition_in_struct_member(self):
        struct = (
            self.parse("struct S { enum E : unsigned char { A } member : 2; };")
            .ext[0]
            .type
        )
        member = struct.decls[0]
        self.assertEqual(member.name, "member")
        self.assertEqual(member.bitsize.value, "2")
        self.assertEqual(
            member.type.type.underlying_type.type.type.names, ["unsigned", "char"]
        )

    def test_definition_in_parameter(self):
        func = self.parse("void f(enum E : unsigned int { A } value);").ext[0]
        param = func.type.args.params[0]
        self.assertEqual(param.name, "value")
        self.assertEqual(param.type.type.name, "E")
        self.assertEqual(
            param.type.type.underlying_type.type.type.names, ["unsigned", "int"]
        )

    def test_definition_in_type_name(self):
        func = self.parse("void f(void) { (enum E : unsigned char { A })0; }").ext[0]
        expr = func.body.block_items[0]
        self.assertIsInstance(expr, Cast)
        enum = expr.to_type.type.type
        self.assertEqual(enum.name, "E")
        self.assertEqual(enum.underlying_type.type.type.names, ["unsigned", "char"])

    def test_unnamed_enum_bitfields(self):
        ast = self.parse("""
            enum E : unsigned int { A, WIDTH = 3 };
            struct S { enum E : 3; enum E : WIDTH; enum E : sizeof(int); };
        """)
        literal, identifier, size = ast.ext[1].type.decls
        self.assertIsNone(literal.name)
        self.assertIsNone(literal.type.type.underlying_type)
        self.assertEqual(literal.bitsize.value, "3")
        self.assertIsNone(identifier.name)
        self.assertIsNone(identifier.type.type.underlying_type)
        self.assertEqual(identifier.bitsize.name, "WIDTH")
        self.assertIsNone(size.type.type.underlying_type)
        self.assertEqual(size.bitsize.op, "sizeof")

    def test_legacy_enum_bitfields(self):
        parser = c_parser.CParser(dialect="legacy")
        ast = parser.parse("""
            enum E { A, WIDTH = 3 };
            struct S { enum E : 3; enum E : WIDTH; enum E member : sizeof(int); };
        """)
        self.assertIsNone(ast.ext[0].type.underlying_type)
        literal, identifier, size = ast.ext[1].type.decls
        self.assertIsNone(literal.type.type.underlying_type)
        self.assertEqual(literal.bitsize.value, "3")
        self.assertEqual(identifier.bitsize.name, "WIDTH")
        self.assertEqual(size.name, "member")
        self.assertEqual(size.bitsize.op, "sizeof")

    def test_fixed_enum_rejected_in_legacy(self):
        parser = c_parser.CParser(dialect="legacy")
        with self.assertRaisesRegex(
            ParseError, "Fixed underlying enum types require C23"
        ):
            parser.parse("enum E : unsigned int { A };")
        with self.assertRaisesRegex(
            ParseError, "Fixed underlying enum types require C23"
        ):
            parser.parse("enum E : unsigned int;")
        with self.assertRaisesRegex(
            ParseError, "Fixed underlying enum types require C23"
        ):
            parser.parse("enum : unsigned int { A } value;")
        with self.assertRaisesRegex(
            ParseError, "Fixed underlying enum types require C23"
        ):
            parser.parse("typedef int T; enum E : T { A };")

    def test_invalid_underlying_type_syntax(self):
        self.assertRaises(ParseError, self.parse, "enum E : { A };")
        self.assertRaises(ParseError, self.parse, "enum E :;")
        self.assertRaises(ParseError, self.parse, "enum E :")
        self.assertRaises(ParseError, self.parse, "enum E : unknown { A };")
        self.assertRaises(ParseError, self.parse, "enum E : const { A };")
        self.assertRaises(ParseError, self.parse, "enum E : static int { A };")
        self.assertRaises(ParseError, self.parse, "enum E : int * { A };")
        self.assertRaises(ParseError, self.parse, "enum E : int [3] { A };")
        self.assertRaises(ParseError, self.parse, "enum E : int () { A };")
        self.assertRaises(ParseError, self.parse, "enum E : (int) { A };")
        self.assertRaises(ParseError, self.parse, "enum E : int { A;")
        self.assertRaises(ParseError, self.parse, "enum E : int {};")
        self.assertRaises(ParseError, self.parse, "enum : int;")
        self.assertRaises(ParseError, self.parse, "enum : int value;")
        self.assertRaises(
            ParseError,
            self.parse,
            "typedef int T; void f(void) { int T; enum E : T { A }; }",
        )

    def test_coordinates_and_traversal(self):
        enum = (
            self.parse("enum E :\n  unsigned char { A };", filename="enum.c")
            .ext[0]
            .type
        )
        underlying = enum.underlying_type
        self.assert_coord(enum, 1, 1, "enum.c")
        self.assert_coord(underlying, 2, 3, "enum.c")
        self.assert_coord(underlying.type.type, 2, 3, "enum.c")
        self.assertEqual(
            enum.children(), (("values", enum.values), ("underlying_type", underlying))
        )
        self.assertEqual(list(enum), [enum.values, underlying])

        class TypeVisitor(NodeVisitor):
            def __init__(self):
                self.names = []

            def visit_IdentifierType(self, node):
                self.names.append(node.names)

        visitor = TypeVisitor()
        visitor.visit(enum)
        self.assertEqual(visitor.names, [["unsigned", "char"]])


class TestCParser_auto(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_inferred_declarations(self):
        declarations = """
            auto count = 42;
            const auto scale = 0.5;
            static auto enabled = true;
            constexpr auto limit = 16;
            auto pointer = &count;
            auto ((parenthesized)) = 1;
            alignas(16) auto aligned = 0;
        """
        for block_scope in (False, True):
            with self.subTest(block_scope=block_scope):
                source = declarations
                if block_scope:
                    source = "void f(void) {" + declarations + "}"
                ast = self.parse(source, filename="auto.c")
                decls = ast.ext[0].body.block_items if block_scope else ast.ext
                self.assertEqual(len(decls), 7)
                for decl in decls:
                    self.assertIsInstance(decl.type, TypeDecl)
                    self.assertIsInstance(decl.type.type, InferredType)
                    self.assertIn("auto", decl.storage)
                self.assertEqual(expand_init(decls[0].init), ["Constant", "int", "42"])
                self.assertEqual(decls[1].quals, ["const"])
                self.assertEqual(decls[1].type.quals, ["const"])
                self.assertEqual(decls[2].storage, ["static", "auto"])
                self.assertEqual(decls[3].storage, ["constexpr", "auto"])
                self.assertIsInstance(decls[4].init, UnaryOp)
                self.assertEqual(decls[4].init.op, "&")
                self.assertEqual(decls[5].name, "parenthesized")
                self.assertEqual(decls[6].align[0].alignment.value, "16")

    def test_expression_initializers(self):
        ast = self.parse("""
            typedef int T;
            int compute(void);
            void f(void) {
                int values[3];
                auto p = values;
                auto q = &values;
                auto cast = (T)3;
                auto literal = (T){4};
                auto call = compute();
                auto comma = (compute(), 5);
                auto string = "text";
                auto null = nullptr;
                T after = cast;
            }
        """)
        decls = ast.ext[2].body.block_items
        expected = (
            ID,
            UnaryOp,
            Cast,
            CompoundLiteral,
            FuncCall,
            ExprList,
            Constant,
            Constant,
        )
        for decl, init_type in zip(decls[1:-1], expected):
            self.assertIsInstance(decl.type.type, InferredType)
            self.assertIsInstance(decl.init, init_type)
        self.assertEqual(decls[-1].type.type.names, ["T"])

    def test_for_loop_and_typedef_scopes(self):
        ast = self.parse("""
            typedef int T;
            void f(void) {
                auto start = 0;
                for (auto i = start; i < 3; ++i) { auto j = i; }
                { auto int T = 2; auto value = T; }
                T after;
            }
        """)
        body = ast.ext[1].body.block_items
        loop = body[1]
        self.assertIsInstance(loop.init.decls[0].type.type, InferredType)
        self.assertEqual(loop.init.decls[0].init.name, "start")
        self.assertIsInstance(loop.stmt.block_items[0].type.type, InferredType)
        self.assertEqual(body[2].block_items[1].init.name, "T")
        self.assertEqual(body[3].type.type.names, ["T"])

    def test_explicit_types_and_legacy_mode(self):
        source = "typedef int T; void f(void) { auto int x; auto T y = 3; }"
        parsers = (self.cparser, c_parser.CParser(), c_parser.CParser(dialect="legacy"))
        for _ in range(2):
            for parser in parsers:
                ast = parser.parse(source)
                x, y = ast.ext[1].body.block_items
                self.assertEqual(x.storage, ["auto"])
                self.assertEqual(x.type.type.names, ["int"])
                self.assertEqual(y.type.type.names, ["T"])
            self.assertIsInstance(
                self.parse("auto x = 1;").ext[0].type.type, InferredType
            )
            for parser in parsers[1:]:
                for source_without_type in (
                    "auto x = 1;",
                    "void f(void) { auto x = 1; }",
                ):
                    self.assertRaises(ParseError, parser.parse, source_without_type)

    def test_invalid_inferred_declarations(self):
        for source in (
            "auto x;",
            "auto x = {};",
            "auto x = {1};",
            "auto x = 1, y = 2;",
            "auto *p = &x;",
            "auto a[3] = x;",
            "auto f(void) = 0;",
            "auto f(void) { return 0; }",
            "auto;",
            "auto = 1;",
            "auto x =;",
            "const x = 1;",
        ):
            for block_scope in (False, True):
                with self.subTest(source=source, block_scope=block_scope):
                    wrapped = "void f(void) {" + source + "}" if block_scope else source
                    self.assertRaises(ParseError, self.parse, wrapped)
        for source in (
            "void f(auto x);",
            "void f(const auto);",
            "typedef int T; void f(void) { auto T = 1; }",
        ):
            with self.subTest(source=source):
                self.assertRaises(ParseError, self.parse, source)

    def test_coordinates_and_visitor(self):
        ast = self.parse("auto count = 42;", filename="auto.c")
        decl = ast.ext[0]
        self.assert_coord(decl.type.type, 1, 6, "auto.c")
        self.assert_coord(decl.init, 1, 14, "auto.c")

        class InferredVisitor(NodeVisitor):
            def __init__(self):
                self.types = []

            def visit_InferredType(self, node):
                self.types.append(node)

        visitor = InferredVisitor()
        visitor.visit(ast)
        self.assertEqual(visitor.types, [decl.type.type])


class TestCParser_typeof(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_typeof_type_operands(self):
        typ = self.parse("typeof(int) value;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertEqual(
            expand_decl(typ.expr),
            ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        typ = self.parse("typeof(const int *) value;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertEqual(
            expand_decl(typ.expr),
            [
                "Typename",
                ["const"],
                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

        typ = self.parse("typeof(int [3]) value;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertEqual(
            expand_decl(typ.expr),
            [
                "Typename",
                ["ArrayDecl", "3", [], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

        typ = self.parse("typeof(int (*)(int)) callback;").ext[0].type.type
        self.assertIsInstance(typ.expr.type, PtrDecl)
        self.assertIsInstance(typ.expr.type.type, FuncDecl)
        self.assertEqual(typ.expr.type.type.args.params[0].type.type.names, ["int"])

    def test_typeof_unqual_type_operands(self):
        typ = self.parse("typeof_unqual(int) value;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertEqual(
            expand_decl(typ.expr),
            ["Typename", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        typ = self.parse("typeof_unqual(const int *) value;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertEqual(
            expand_decl(typ.expr),
            [
                "Typename",
                ["const"],
                ["PtrDecl", ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

        typ = self.parse("typeof_unqual(int [3]) value;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertEqual(
            expand_decl(typ.expr),
            [
                "Typename",
                ["ArrayDecl", "3", [], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )

        typ = self.parse("typeof_unqual(int (*)(int)) callback;").ext[0].type.type
        self.assertIsInstance(typ.expr.type, PtrDecl)
        self.assertIsInstance(typ.expr.type.type, FuncDecl)
        self.assertEqual(typ.expr.type.type.args.params[0].type.type.names, ["int"])

    def test_typeof_expression_operands(self):
        typ = self.parse("typeof(value) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertIsInstance(typ.expr, ID)

        typ = self.parse("typeof(value + 1) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertIsInstance(typ.expr, BinaryOp)

        typ = self.parse("typeof(value++) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertIsInstance(typ.expr, UnaryOp)

        typ = self.parse("typeof(f(value)) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertIsInstance(typ.expr, FuncCall)

        typ = self.parse("typeof((int)value) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertIsInstance(typ.expr, Cast)

        typ = self.parse("typeof((int){1}) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertIsInstance(typ.expr, CompoundLiteral)

        typ = self.parse("typeof(value, f()) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof")
        self.assertIsInstance(typ.expr, ExprList)

    def test_typeof_unqual_expression_operands(self):
        typ = self.parse("typeof_unqual(value) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertIsInstance(typ.expr, ID)

        typ = self.parse("typeof_unqual(value + 1) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertIsInstance(typ.expr, BinaryOp)

        typ = self.parse("typeof_unqual(value++) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertIsInstance(typ.expr, UnaryOp)

        typ = self.parse("typeof_unqual(f(value)) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertIsInstance(typ.expr, FuncCall)

        typ = self.parse("typeof_unqual((int)value) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertIsInstance(typ.expr, Cast)

        typ = self.parse("typeof_unqual((int){1}) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertIsInstance(typ.expr, CompoundLiteral)

        typ = self.parse("typeof_unqual(value, f()) copy;").ext[0].type.type
        self.assertIsInstance(typ, TypeOf)
        self.assertEqual(typ.op, "typeof_unqual")
        self.assertIsInstance(typ.expr, ExprList)

    def test_typedef_scopes(self):
        ast = self.parse("""
            typedef int T;
            typeof(T) outer;
            void f(void) {
                typeof(T) before;
                typeof(int) T = 0;
                typeof(T) after;
                { typedef char T; typeof_unqual(T) inner; }
                typeof(T) last;
            }
            typeof(T) restored;
        """)
        before, shadow, after, block, last = ast.ext[2].body.block_items
        for decl in (ast.ext[1], before, block.block_items[1], ast.ext[3]):
            self.assertIsInstance(decl.type.type.expr, Typename)
            self.assertEqual(decl.type.type.expr.type.type.names, ["T"])
        self.assertEqual(shadow.name, "T")
        for decl in (after, last):
            self.assertIsInstance(decl.type.type.expr, ID)
            self.assertEqual(decl.type.type.expr.name, "T")

    def test_nested_types_and_qualifiers(self):
        ast = self.parse("""
            typeof(typeof_unqual(const int)) nested;
            typeof(_Atomic(int)) inner_atomic;
            _Atomic(typeof(int)) outer_atomic;
            const typeof_unqual(volatile int) qualified;
        """)
        nested, inner, outer, qualified = ast.ext
        self.assertEqual(nested.type.type.expr.type.type.op, "typeof_unqual")
        self.assertEqual(nested.type.type.expr.type.type.expr.quals, ["const"])
        self.assertEqual(inner.quals, [])
        self.assertEqual(inner.type.type.expr.quals, ["_Atomic"])
        self.assertEqual(outer.quals, ["_Atomic"])
        self.assertEqual(outer.type.type.expr.quals, [])
        self.assertEqual(qualified.quals, ["const"])
        self.assertEqual(qualified.type.type.expr.quals, ["volatile"])

    def test_declaration_contexts(self):
        ast = self.parse("""
            typedef typeof(1) T;
            struct S { typeof(T) member; typeof_unqual(unsigned int) bits : 3; };
            typeof(int) f(typeof(int) arg, typeof_unqual(const int)) {
                typeof(arg) local = arg;
                for (typeof(arg) i = 0; i < 3; ++i) {}
                return local;
            }
        """)
        typedef, struct, func = ast.ext
        self.assertIsInstance(typedef.type.type, TypeOf)
        for member in struct.type.decls:
            self.assertIsInstance(member.type.type, TypeOf)
        self.assertEqual(struct.type.decls[1].bitsize.value, "3")
        self.assertIsInstance(func.decl.type.type.type, TypeOf)
        for param in func.decl.type.args.params:
            self.assertIsInstance(param.type.type, TypeOf)
        local, loop, _ = func.body.block_items
        self.assertIsInstance(local.type.type, TypeOf)
        self.assertIsInstance(loop.init.decls[0].type.type, TypeOf)

    def test_type_name_contexts(self):
        ast = self.parse("""
            alignas(typeof(int)) int aligned;
            void f(void) {
                sizeof(typeof(int));
                alignof(typeof_unqual(const int));
                (typeof(1))2;
                (typeof(int)){3};
                _Generic(1, typeof(int): 1, default: 0);
            }
        """)
        self.assertIsInstance(ast.ext[0].align[0].alignment.type.type, TypeOf)
        size, align, cast, literal, generic = ast.ext[1].body.block_items
        for expr in (size, align):
            self.assertIsInstance(expr.expr.type.type, TypeOf)
        self.assertIsInstance(cast.to_type.type.type, TypeOf)
        self.assertIsInstance(literal.type.type.type, TypeOf)
        self.assertIsInstance(generic.associations[0].type.type.type, TypeOf)

    def test_invalid_typeof_specifiers(self):
        self.assertRaises(ParseError, self.parse, "typeof() x;")
        self.assertRaises(ParseError, self.parse, "typeof int x;")
        self.assertRaises(ParseError, self.parse, "typeof(int x;")
        self.assertRaises(ParseError, self.parse, "typeof(int x) y;")
        self.assertRaises(ParseError, self.parse, "typeof(value,) x;")
        self.assertRaises(ParseError, self.parse, "typeof(int);")
        self.assertRaises(ParseError, self.parse, "int typeof(int);")
        self.assertRaises(ParseError, self.parse, "int typeof(int) x;")
        self.assertRaises(ParseError, self.parse, "typeof(int) int x;")
        self.assertRaises(ParseError, self.parse, "typeof(int) typeof(int) x;")
        self.assertRaises(ParseError, self.parse, "void f(int typeof(int));")
        self.assertRaises(ParseError, self.parse, "void f(void) { int x = typeof(1); }")

    def test_invalid_typeof_unqual_specifiers(self):
        self.assertRaises(ParseError, self.parse, "typeof_unqual() x;")
        self.assertRaises(ParseError, self.parse, "typeof_unqual int x;")
        self.assertRaises(ParseError, self.parse, "typeof_unqual(int x;")
        self.assertRaises(ParseError, self.parse, "typeof_unqual(int x) y;")
        self.assertRaises(ParseError, self.parse, "typeof_unqual(value,) x;")
        self.assertRaises(ParseError, self.parse, "typeof_unqual(int);")
        self.assertRaises(ParseError, self.parse, "int typeof_unqual(int);")
        self.assertRaises(ParseError, self.parse, "int typeof_unqual(int) x;")
        self.assertRaises(ParseError, self.parse, "typeof_unqual(int) int x;")
        self.assertRaises(
            ParseError, self.parse, "typeof_unqual(int) typeof_unqual(int) x;"
        )
        self.assertRaises(ParseError, self.parse, "void f(int typeof_unqual(int));")
        self.assertRaises(
            ParseError, self.parse, "void f(void) { int x = typeof_unqual(1); }"
        )

    def test_legacy_mode(self):
        for parser in (c_parser.CParser(), c_parser.CParser(dialect="legacy")):
            ast = parser.parse("""
                int typeof(int x) { return x; }
                int typeof_unqual(int x) { return typeof(x); }
            """)
            self.assertEqual(ast.ext[0].decl.name, "typeof")
            self.assertEqual(ast.ext[1].decl.name, "typeof_unqual")
            self.assertEqual(ast.ext[1].body.block_items[0].expr.name.name, "typeof")
            self.assertRaises(ParseError, parser.parse, "typeof(int) x;")
            self.assertRaises(ParseError, parser.parse, "typeof_unqual(const int) x;")

    def test_coordinates_and_visitor(self):
        ast = self.parse("typeof(x + 1) y;", filename="typeof.c")
        typ = ast.ext[0].type.type
        self.assert_coord(typ, 1, 1, "typeof.c")
        self.assert_coord(typ.expr, 1, 8, "typeof.c")

        class TypeOfVisitor(NodeVisitor):
            def __init__(self):
                self.operators = []
                self.ids = []

            def visit_TypeOf(self, node):
                self.operators.append(node.op)
                self.generic_visit(node)

            def visit_ID(self, node):
                self.ids.append(node.name)

        visitor = TypeOfVisitor()
        visitor.visit(ast)
        self.assertEqual(visitor.operators, ["typeof"])
        self.assertEqual(visitor.ids, ["x"])


class TestCParser_bitint(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_plain_type(self):
        decl = self.parse("_BitInt(17) value;").ext[0]
        self.assertEqual(decl.name, "value")
        self.assertIsInstance(decl.type.type, BitIntType)
        self.assertIsNone(decl.type.type.signedness)
        self.assertEqual(expand_init(decl.type.type.width), ["Constant", "int", "17"])

    def test_signed_type(self):
        typ = self.parse("signed _BitInt(17) value;").ext[0].type.type
        self.assertIsInstance(typ, BitIntType)
        self.assertEqual(typ.signedness, "signed")
        self.assertEqual(typ.width.value, "17")

        typ = self.parse("_BitInt(17) signed value;").ext[0].type.type
        self.assertIsInstance(typ, BitIntType)
        self.assertEqual(typ.signedness, "signed")
        self.assertEqual(typ.width.value, "17")

    def test_unsigned_type(self):
        typ = self.parse("unsigned _BitInt(1) flag;").ext[0].type.type
        self.assertIsInstance(typ, BitIntType)
        self.assertEqual(typ.signedness, "unsigned")
        self.assertEqual(typ.width.value, "1")

        typ = self.parse("_BitInt(17) unsigned value;").ext[0].type.type
        self.assertIsInstance(typ, BitIntType)
        self.assertEqual(typ.signedness, "unsigned")
        self.assertEqual(typ.width.value, "17")

    def test_width_expressions(self):
        width = self.parse("_BitInt(WIDTH) value;").ext[0].type.type.width
        self.assertIsInstance(width, ID)
        self.assertEqual(width.name, "WIDTH")

        width = self.parse("_BitInt(8 * sizeof(int)) value;").ext[0].type.type.width
        self.assertIsInstance(width, BinaryOp)
        self.assertEqual(width.op, "*")
        self.assertEqual(width.left.value, "8")
        self.assertIsInstance(width.right, UnaryOp)
        self.assertEqual(width.right.op, "sizeof")
        self.assertEqual(width.right.expr.type.type.names, ["int"])

        width = (
            self.parse("_BitInt(WIDTH > 8 ? WIDTH : 8) value;").ext[0].type.type.width
        )
        self.assertIsInstance(width, TernaryOp)
        self.assertEqual(width.cond.op, ">")
        self.assertEqual(width.iftrue.name, "WIDTH")
        self.assertEqual(width.iffalse.value, "8")

    def test_qualifiers_and_declarators(self):
        value, pointer, array = self.parse(
            "static const unsigned _BitInt(17) value = 1, *pointer, array[3];"
        ).ext
        self.assertEqual(value.storage, ["static"])
        self.assertEqual(value.quals, ["const"])
        self.assertEqual(value.type.quals, ["const"])
        self.assertEqual(value.type.type.signedness, "unsigned")
        self.assertEqual(value.type.type.width.value, "17")
        self.assertEqual(value.init.value, "1")
        self.assertIsInstance(pointer.type, PtrDecl)
        self.assertEqual(pointer.type.type.quals, ["const"])
        self.assertEqual(pointer.type.type.type.signedness, "unsigned")
        self.assertEqual(pointer.type.type.type.width.value, "17")
        self.assertIsInstance(array.type, ArrayDecl)
        self.assertEqual(array.type.dim.value, "3")
        self.assertEqual(array.type.type.type.signedness, "unsigned")
        self.assertEqual(array.type.type.type.width.value, "17")

    def test_atomic_and_typeof(self):
        atomic, qualified, typeof = self.parse("""
            _Atomic(unsigned _BitInt(17)) atomic;
            _Atomic _BitInt(17) qualified;
            typeof_unqual(const unsigned _BitInt(17)) value;
        """).ext
        self.assertEqual(atomic.quals, ["_Atomic"])
        self.assertIsInstance(atomic.type.type, BitIntType)
        self.assertEqual(atomic.type.type.signedness, "unsigned")
        self.assertEqual(qualified.quals, ["_Atomic"])
        self.assertIsInstance(qualified.type.type, BitIntType)
        self.assertIsNone(qualified.type.type.signedness)
        self.assertEqual(typeof.type.type.op, "typeof_unqual")
        self.assertEqual(typeof.type.type.expr.quals, ["const"])
        self.assertIsInstance(typeof.type.type.expr.type.type, BitIntType)
        self.assertEqual(typeof.type.type.expr.type.type.signedness, "unsigned")

    def test_declaration_contexts(self):
        ast = self.parse("""
            typedef unsigned _BitInt(17) T;
            struct S { _BitInt(8) member; unsigned _BitInt(3) bits : 3; };
            _BitInt(17) f(unsigned _BitInt(8) arg, _BitInt(17)) {
                T from_typedef;
                _BitInt(8) T = 0;
                for (unsigned _BitInt(8) i = 0; i < 3; ++i) {}
                return T;
            }
            T after;
        """)
        typedef, struct, func, after = ast.ext
        self.assertIsInstance(typedef, Typedef)
        self.assertIsInstance(typedef.type.type, BitIntType)
        self.assertEqual(typedef.type.type.signedness, "unsigned")
        member, bits = struct.type.decls
        self.assertIsInstance(member.type.type, BitIntType)
        self.assertIsInstance(bits.type.type, BitIntType)
        self.assertEqual(bits.type.type.signedness, "unsigned")
        self.assertEqual(bits.bitsize.value, "3")
        self.assertIsInstance(func.decl.type.type.type, BitIntType)
        named, unnamed = func.decl.type.args.params
        self.assertEqual(named.name, "arg")
        self.assertIsInstance(named.type.type, BitIntType)
        self.assertIsInstance(unnamed, Typename)
        self.assertIsInstance(unnamed.type.type, BitIntType)
        from_typedef, shadow, loop, _ = func.body.block_items
        self.assertEqual(from_typedef.type.type.names, ["T"])
        self.assertEqual(shadow.name, "T")
        self.assertIsInstance(shadow.type.type, BitIntType)
        self.assertEqual(loop.init.decls[0].type.type.signedness, "unsigned")
        self.assertEqual(after.type.type.names, ["T"])

    def test_type_name_contexts(self):
        ast = self.parse("""
            alignas(_BitInt(8)) int aligned;
            void f(void) {
                sizeof(_BitInt(17));
                alignof(unsigned _BitInt(8));
                (_BitInt(17))2;
                (unsigned _BitInt(8)){3};
                _Generic(1, _BitInt(17): 1, default: 0);
            }
        """)
        self.assertIsInstance(ast.ext[0].align[0].alignment.type.type, BitIntType)
        size, align, cast, literal, generic = ast.ext[1].body.block_items
        self.assertIsInstance(size.expr.type.type, BitIntType)
        self.assertEqual(align.expr.type.type.signedness, "unsigned")
        self.assertIsInstance(cast.to_type.type.type, BitIntType)
        self.assertEqual(literal.type.type.type.signedness, "unsigned")
        self.assertIsInstance(generic.associations[0].type.type.type, BitIntType)

    def test_invalid_width_syntax(self):
        self.assertRaises(ParseError, self.parse, "_BitInt() x;")
        self.assertRaises(ParseError, self.parse, "_BitInt 17 x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(17 x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(int) x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(8, 17) x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(WIDTH = 17) x;")

    def test_invalid_type_combinations(self):
        self.assertRaises(ParseError, self.parse, "int _BitInt(17) x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(17) int x;")
        self.assertRaises(ParseError, self.parse, "long _BitInt(17) x;")
        self.assertRaises(ParseError, self.parse, "unsigned signed _BitInt(17) x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(17) unsigned unsigned x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(8) _BitInt(17) x;")
        self.assertRaises(ParseError, self.parse, "_BitInt(17) typeof(int) x;")
        self.assertRaises(ParseError, self.parse, "typeof(int) _BitInt(17) x;")
        self.assertRaises(ParseError, self.parse, "int _BitInt(17);")
        self.assertRaises(ParseError, self.parse, "void f(int _BitInt(17));")

    def test_legacy_mode(self):
        parser = c_parser.CParser()
        ast = parser.parse("int _BitInt = 1; int f(void) { return _BitInt; }")
        self.assertEqual(ast.ext[0].name, "_BitInt")
        self.assertEqual(ast.ext[1].body.block_items[0].expr.name, "_BitInt")
        self.assertRaises(ParseError, parser.parse, "_BitInt(17) x;")
        self.assertRaises(ParseError, parser.parse, "unsigned _BitInt(17) x;")

    def test_coordinates_and_visitor(self):
        ast = self.parse("unsigned _BitInt(WIDTH + 1) x;", filename="bitint.c")
        typ = ast.ext[0].type.type
        self.assert_coord(typ, 1, 10, "bitint.c")
        self.assert_coord(typ.width, 1, 18, "bitint.c")

        class BitIntVisitor(NodeVisitor):
            def __init__(self):
                self.types = []
                self.ids = []

            def visit_BitIntType(self, node):
                self.types.append(node)
                self.generic_visit(node)

            def visit_ID(self, node):
                self.ids.append(node.name)

        visitor = BitIntVisitor()
        visitor.visit(ast)
        self.assertEqual(visitor.types, [typ])
        self.assertEqual(visitor.ids, ["WIDTH"])


class TestCParser_digit_separators(TestCParser_base):
    def test_integer_constants_in_default_mode(self):
        init = self.parse("int x = 1'000'000;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "int", "1'000'000"])

        init = self.parse("int x = 0'7'7;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "int", "0'7'7"])

        init = self.parse("int x = 0xAB'CD;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "int", "0xAB'CD"])

        init = self.parse("int x = 0b1010'0101;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "int", "0b1010'0101"])

    def test_floating_constants_in_default_mode(self):
        init = self.parse("double x = 1'234.56'78;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "double", "1'234.56'78"])

        init = self.parse("double x = .1'25;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "double", ".1'25"])

        init = self.parse("double x = 1'000.;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "double", "1'000."])

        init = self.parse("double x = 1'2e-3'4;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "double", "1'2e-3'4"])

        init = self.parse("double x = 0xAB'CD.EF'01p+1'0;").ext[0].init
        self.assertEqual(
            expand_init(init), ["Constant", "double", "0xAB'CD.EF'01p+1'0"]
        )

    def test_suffixes(self):
        init = self.parse("unsigned x = 1'000U;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned int", "1'000U"])

        init = self.parse("long x = 1'000L;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "long int", "1'000L"])

        init = self.parse("unsigned long long x = 0xFF'FFuLL;").ext[0].init
        self.assertEqual(
            expand_init(init), ["Constant", "unsigned long long int", "0xFF'FFuLL"]
        )

        init = self.parse("float x = 1.2'5F;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "float", "1.2'5F"])

        init = self.parse("long double x = 0xA'B.p1'0L;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "long double", "0xA'B.p1'0L"])

    def test_c23_constants(self):
        parser = c_parser.CParser(dialect="c23")
        init = parser.parse("auto x = 1'000;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "int", "1'000"])

        init = parser.parse("auto x = 1'000wb;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_BitInt", "1'000wb"])

        init = parser.parse("auto x = 0b1010'0101UWB;").ext[0].init
        self.assertEqual(
            expand_init(init), ["Constant", "unsigned _BitInt", "0b1010'0101UWB"]
        )

        init = parser.parse("_Decimal32 x = 1'2.3'4e+1'0DF;").ext[0].init
        self.assertEqual(
            expand_init(init), ["Constant", "_Decimal32", "1'2.3'4e+1'0DF"]
        )

        init = parser.parse("_Decimal64 x = 1'000.00dd;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_Decimal64", "1'000.00dd"])

        init = parser.parse("_Decimal128 x = .1'25DL;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_Decimal128", ".1'25DL"])

    def test_separators_do_not_enable_c23_suffixes_in_legacy_mode(self):
        self.assertRaises(ParseError, self.parse, "int x = 1'000wb;")
        self.assertRaises(ParseError, self.parse, "int x = 1'000uwb;")
        self.assertRaises(ParseError, self.parse, "double x = 1'000.0df;")
        self.assertRaises(ParseError, self.parse, "double x = 1'000.0dd;")
        self.assertRaises(ParseError, self.parse, "double x = 1'000.0dl;")

    def test_invalid_separator_positions(self):
        self.assertRaises(ParseError, self.parse, "int x = 1''000;")
        self.assertRaises(ParseError, self.parse, "int x = 1'000';")
        self.assertRaises(ParseError, self.parse, "int x = 0x'FF;")
        self.assertRaises(ParseError, self.parse, "int x = 0b'10;")
        self.assertRaises(ParseError, self.parse, "int x = 1'U;")
        self.assertRaises(ParseError, self.parse, "int x = 0'8;")
        self.assertRaises(ParseError, self.parse, "double x = 1'.0;")
        self.assertRaises(ParseError, self.parse, "double x = 1.'0;")
        self.assertRaises(ParseError, self.parse, "double x = 1'e2;")
        self.assertRaises(ParseError, self.parse, "double x = 1e'2;")
        self.assertRaises(ParseError, self.parse, "double x = 1e+'2;")
        self.assertRaises(ParseError, self.parse, "double x = 0x1'p2;")
        self.assertRaises(ParseError, self.parse, "double x = 0x1p'2;")

    def test_coordinates_and_line_directives(self):
        ast = self.parse("int x = 1'000, y = 2'000;", filename="digits.c")
        self.assert_coord(ast.ext[0].init, 1, 9, "digits.c")
        self.assert_coord(ast.ext[1].init, 1, 20, "digits.c")

        ast = self.parse("#line 1'000\nint x = 2'000;", filename="digits.c")
        self.assert_coord(ast.ext[0].init, 1000, 9, "digits.c")


class TestCParser_bitint_literals(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_signed_suffixes(self):
        init = self.parse("auto x = 42wb;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_BitInt", "42wb"])

        init = self.parse("auto x = 42WB;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_BitInt", "42WB"])

    def test_unsigned_prefixes(self):
        init = self.parse("auto x = 42uwb;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42uwb"])

        init = self.parse("auto x = 42uWB;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42uWB"])

        init = self.parse("auto x = 42Uwb;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42Uwb"])

        init = self.parse("auto x = 42UWB;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42UWB"])

    def test_unsigned_suffixes(self):
        init = self.parse("auto x = 42wbu;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42wbu"])

        init = self.parse("auto x = 42wbU;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42wbU"])

        init = self.parse("auto x = 42WBu;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42WBu"])

        init = self.parse("auto x = 42WBU;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "42WBU"])

    def test_integer_bases(self):
        init = self.parse("auto x = 0wb;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_BitInt", "0wb"])

        init = self.parse("auto x = 077uwb;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "077uwb"])

        init = self.parse("auto x = 0x1bwb;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_BitInt", "0x1bwb"])

        init = self.parse("auto x = 0XffUWB;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned _BitInt", "0XffUWB"])

        init = self.parse("auto x = 0b101wbu;").ext[0].init
        self.assertEqual(
            expand_init(init), ["Constant", "unsigned _BitInt", "0b101wbu"]
        )

        init = self.parse("auto x = 0B101WB;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_BitInt", "0B101WB"])

    def test_large_value_and_negation(self):
        init = (
            self.parse("auto x = 340282366920938463463374607431768211456wb;")
            .ext[0]
            .init
        )
        self.assertEqual(init.type, "_BitInt")
        self.assertEqual(init.value, "340282366920938463463374607431768211456wb")

        init = self.parse("auto x = -3wb;").ext[0].init
        self.assertIsInstance(init, UnaryOp)
        self.assertEqual(init.op, "-")
        self.assertEqual(expand_init(init.expr), ["Constant", "_BitInt", "3wb"])

    def test_expression_contexts(self):
        ast = self.parse("""
            _BitInt(8wb) value = 42wb;
            void f(void) {
                1wb;
                auto sum = 1uwb + 2WBU;
                consume(3WB);
                if (1wb) 2uwb; else 3WB;
                _Generic(1wb, _BitInt(2): 1, default: 0);
            }
        """)
        self.assertEqual(ast.ext[0].type.type.width.type, "_BitInt")
        self.assertEqual(ast.ext[0].init.type, "_BitInt")
        constant, sum_decl, call, conditional, generic = ast.ext[1].body.block_items
        self.assertEqual(expand_init(constant), ["Constant", "_BitInt", "1wb"])
        self.assertEqual(sum_decl.init.op, "+")
        self.assertEqual(sum_decl.init.left.type, "unsigned _BitInt")
        self.assertEqual(sum_decl.init.right.type, "unsigned _BitInt")
        self.assertEqual(call.args.exprs[0].type, "_BitInt")
        self.assertEqual(conditional.cond.type, "_BitInt")
        self.assertEqual(conditional.iftrue.type, "unsigned _BitInt")
        self.assertEqual(conditional.iffalse.type, "_BitInt")
        self.assertEqual(generic.expr.type, "_BitInt")

    def test_invalid_suffixes(self):
        self.assertRaises(ParseError, self.parse, "auto x = 42wB;")
        self.assertRaises(ParseError, self.parse, "auto x = 42Wb;")
        self.assertRaises(ParseError, self.parse, "auto x = 42uwB;")
        self.assertRaises(ParseError, self.parse, "auto x = 42Wbu;")
        self.assertRaises(ParseError, self.parse, "auto x = 42uwbu;")
        self.assertRaises(ParseError, self.parse, "auto x = 42wbwb;")
        self.assertRaises(ParseError, self.parse, "auto x = 42wbl;")
        self.assertRaises(ParseError, self.parse, "auto x = 42Lwb;")
        self.assertRaises(ParseError, self.parse, "auto x = 42llwb;")
        self.assertRaises(ParseError, self.parse, "auto x = 42WBUL;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0wb;")
        self.assertRaises(ParseError, self.parse, "auto x = 1e2wb;")
        self.assertRaises(ParseError, self.parse, "auto x = 0x1p0wb;")

    def test_ordinary_integer_and_character_constants(self):
        init = self.parse("auto x = 42U;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "unsigned int", "42U"])

        init = self.parse("auto x = 42uLL;").ext[0].init
        self.assertEqual(
            expand_init(init), ["Constant", "unsigned long long int", "42uLL"]
        )

        init = self.parse("auto x = 'wb';").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "int", "'wb'"])

    def test_legacy_mode_and_reuse(self):
        parser = c_parser.CParser()
        with self.assertRaisesRegex(
            ParseError, "Bit-precise integer constants require C23"
        ):
            parser.parse("int x = 42wb;")
        self.assertRaises(ParseError, parser.parse, "int x = 42WB;")
        self.assertRaises(ParseError, parser.parse, "int x = 42uwb;")
        self.assertRaises(ParseError, parser.parse, "int x = 42UWB;")
        self.assertRaises(ParseError, parser.parse, "int x = 42wbu;")
        self.assertRaises(ParseError, parser.parse, "int x = 42WBU;")
        self.assertEqual(self.parse("auto x = 42wb;").ext[0].init.type, "_BitInt")
        self.assertEqual(parser.parse("int x = 42;").ext[0].init.type, "int")
        self.assertEqual(
            self.parse("auto x = 42uwb;").ext[0].init.type, "unsigned _BitInt"
        )
        self.assertRaises(ParseError, parser.parse, "int x = 42uwb;")

    def test_coordinates(self):
        init = self.parse("auto x = 42uwb;", filename="bitint.c").ext[0].init
        self.assert_coord(init, 1, 10, "bitint.c")


class TestCParser_decimal_float(TestCParser_base):
    def setUp(self):
        self.cparser = c_parser.CParser(dialect="c23")

    def test_decimal32(self):
        decl = self.parse("_Decimal32 price = 1.25df;").ext[0]
        self.assertEqual(decl.type.type.names, ["_Decimal32"])
        self.assertEqual(expand_init(decl.init), ["Constant", "_Decimal32", "1.25df"])

    def test_decimal64(self):
        decl = self.parse("_Decimal64 total = 100.00dd;").ext[0]
        self.assertEqual(decl.type.type.names, ["_Decimal64"])
        self.assertEqual(expand_init(decl.init), ["Constant", "_Decimal64", "100.00dd"])

    def test_decimal128(self):
        decl = self.parse("_Decimal128 precise = 0.1dl;").ext[0]
        self.assertEqual(decl.type.type.names, ["_Decimal128"])
        self.assertEqual(expand_init(decl.init), ["Constant", "_Decimal128", "0.1dl"])

    def test_uppercase_suffixes(self):
        init = self.parse("_Decimal32 x = 1.25DF;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_Decimal32", "1.25DF"])

        init = self.parse("_Decimal64 x = 100.00DD;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_Decimal64", "100.00DD"])

        init = self.parse("_Decimal128 x = 0.1DL;").ext[0].init
        self.assertEqual(expand_init(init), ["Constant", "_Decimal128", "0.1DL"])

    def test_fractional_and_exponent_forms(self):
        zero, fraction, exponent, combined = self.parse("""
            auto zero = 0.dd;
            auto fraction = .5df;
            auto exponent = 12e-2dl;
            auto combined = 1.5e+2DF;
        """).ext
        self.assertEqual(expand_init(zero.init), ["Constant", "_Decimal64", "0.dd"])
        self.assertEqual(expand_init(fraction.init), ["Constant", "_Decimal32", ".5df"])
        self.assertEqual(
            expand_init(exponent.init), ["Constant", "_Decimal128", "12e-2dl"]
        )
        self.assertEqual(
            expand_init(combined.init), ["Constant", "_Decimal32", "1.5e+2DF"]
        )

    def test_declaration_contexts(self):
        ast = self.parse("""
            typedef _Decimal64 Money;
            const _Decimal32 *pointer;
            _Decimal128 array[2];
            struct S { _Decimal64 amount; };
            _Decimal64 f(_Decimal32 arg, _Decimal128) {
                constexpr _Decimal64 rate = 0.05dd;
                Money result = rate;
                return result;
            }
        """)
        typedef, pointer, array, struct, func = ast.ext
        self.assertEqual(typedef.type.type.names, ["_Decimal64"])
        self.assertIsInstance(pointer.type, PtrDecl)
        self.assertEqual(pointer.type.type.quals, ["const"])
        self.assertEqual(pointer.type.type.type.names, ["_Decimal32"])
        self.assertIsInstance(array.type, ArrayDecl)
        self.assertEqual(array.type.type.type.names, ["_Decimal128"])
        self.assertEqual(struct.type.decls[0].type.type.names, ["_Decimal64"])
        self.assertEqual(func.decl.type.type.type.names, ["_Decimal64"])
        named, unnamed = func.decl.type.args.params
        self.assertEqual(named.type.type.names, ["_Decimal32"])
        self.assertEqual(unnamed.type.type.names, ["_Decimal128"])
        rate, result, _ = func.body.block_items
        self.assertEqual(rate.storage, ["constexpr"])
        self.assertEqual(rate.init.type, "_Decimal64")
        self.assertEqual(result.type.type.names, ["Money"])

    def test_type_name_contexts(self):
        ast = self.parse("""
            alignas(_Decimal64) int aligned;
            _Atomic(_Decimal32) atomic;
            typeof_unqual(const _Decimal128) value;
            void f(void) {
                sizeof(_Decimal32);
                alignof(_Decimal64);
                (_Decimal128)1;
                (_Decimal64){2.dd};
                _Generic(1.df, _Decimal32: 1, default: 0);
            }
        """)
        self.assertEqual(ast.ext[0].align[0].alignment.type.type.names, ["_Decimal64"])
        self.assertEqual(ast.ext[1].quals, ["_Atomic"])
        self.assertEqual(ast.ext[1].type.type.names, ["_Decimal32"])
        self.assertEqual(ast.ext[2].type.type.expr.type.type.names, ["_Decimal128"])
        size, align, cast, literal, generic = ast.ext[3].body.block_items
        self.assertEqual(size.expr.type.type.names, ["_Decimal32"])
        self.assertEqual(align.expr.type.type.names, ["_Decimal64"])
        self.assertEqual(cast.to_type.type.type.names, ["_Decimal128"])
        self.assertEqual(literal.type.type.type.names, ["_Decimal64"])
        self.assertEqual(generic.associations[0].type.type.type.names, ["_Decimal32"])

    def test_literals_in_expressions_and_statements(self):
        ast = self.parse("""
            void f(void) {
                1.25df;
                -2.5dd;
                auto sum = 1.df + 2.df;
                consume(3.dl);
                if (1.DF) 2.DD; else 3.DL;
            }
        """)
        constant, negative, sum_decl, call, conditional = ast.ext[0].body.block_items
        self.assertEqual(expand_init(constant), ["Constant", "_Decimal32", "1.25df"])
        self.assertEqual(negative.op, "-")
        self.assertEqual(
            expand_init(negative.expr), ["Constant", "_Decimal64", "2.5dd"]
        )
        self.assertEqual(sum_decl.init.op, "+")
        self.assertEqual(sum_decl.init.left.type, "_Decimal32")
        self.assertEqual(sum_decl.init.right.type, "_Decimal32")
        self.assertEqual(call.args.exprs[0].type, "_Decimal128")
        self.assertEqual(conditional.cond.type, "_Decimal32")
        self.assertEqual(conditional.iftrue.type, "_Decimal64")
        self.assertEqual(conditional.iffalse.type, "_Decimal128")

    def test_binary_floating_constants(self):
        double, float_decl, long_double, hex_float = self.parse("""
            double x = 1.25;
            float y = 1.25f;
            long double z = 1.25L;
            float h = 0x1.fp2F;
        """).ext
        self.assertEqual(double.init.type, "double")
        self.assertEqual(float_decl.init.type, "float")
        self.assertEqual(long_double.init.type, "long double")
        self.assertEqual(hex_float.init.type, "float")

    def test_invalid_suffixes(self):
        self.assertRaises(ParseError, self.parse, "auto x = 1.0dF;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0Df;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0dD;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0Dd;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0dL;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0Dl;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0fdf;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0ddL;")
        self.assertRaises(ParseError, self.parse, "auto x = 1.0ddextra;")
        self.assertRaises(ParseError, self.parse, "auto x = 1df;")
        self.assertRaises(ParseError, self.parse, "auto x = 1dd;")
        self.assertRaises(ParseError, self.parse, "auto x = 1dl;")

    def test_hexadecimal_decimal_suffixes(self):
        self.assertRaises(ParseError, self.parse, "auto x = 0x1p0df;")
        self.assertRaises(ParseError, self.parse, "auto x = 0x1p0dd;")
        self.assertRaises(ParseError, self.parse, "auto x = 0x1p0dl;")
        self.assertRaises(ParseError, self.parse, "auto x = 0x1.fp+2DF;")
        self.assertRaises(ParseError, self.parse, "auto x = 0x1.fp+2DD;")
        self.assertRaises(ParseError, self.parse, "auto x = 0x1.fp+2DL;")

    def test_legacy_mode_and_reuse(self):
        parser = c_parser.CParser()
        names = parser.parse("int _Decimal32, _Decimal64, _Decimal128;").ext
        self.assertEqual(names[0].name, "_Decimal32")
        self.assertEqual(names[1].name, "_Decimal64")
        self.assertEqual(names[2].name, "_Decimal128")
        self.assertRaises(ParseError, parser.parse, "_Decimal32 x;")
        self.assertRaises(ParseError, parser.parse, "_Decimal64 x;")
        self.assertRaises(ParseError, parser.parse, "_Decimal128 x;")
        self.assertRaises(ParseError, parser.parse, "double x = 1.25df;")
        self.assertRaises(ParseError, parser.parse, "double x = 1.25dd;")
        self.assertRaises(ParseError, parser.parse, "double x = 1.25dl;")
        self.assertRaises(ParseError, parser.parse, "double x = 1.25DF;")
        self.assertRaises(ParseError, parser.parse, "double x = 1.25DD;")
        self.assertRaises(ParseError, parser.parse, "double x = 1.25DL;")

        self.assertEqual(
            self.parse("_Decimal32 x = 1.df;").ext[0].init.type, "_Decimal32"
        )
        self.assertEqual(parser.parse("double x = 1.;").ext[0].init.type, "double")
        self.assertEqual(
            self.parse("_Decimal64 x = 1.dd;").ext[0].init.type, "_Decimal64"
        )
        self.assertRaises(ParseError, parser.parse, "double x = 1.dd;")

    def test_coordinates(self):
        ast = self.parse("_Decimal64 x = 1.25dd;", filename="decimal.c")
        self.assert_coord(ast.ext[0].type.type, 1, 1, "decimal.c")
        self.assert_coord(ast.ext[0].init, 1, 16, "decimal.c")

    def test_legacy_literal_diagnostic(self):
        parser = c_parser.CParser(dialect="legacy")
        with self.assertRaisesRegex(
            ParseError, "decimal.c:1:12: Decimal floating constants require C23"
        ):
            parser.parse("double x = 1.25dd;", filename="decimal.c")


class TestUnmatchedRbrace(unittest.TestCase):
    """Regression for #603: unmatched '}' raises ParseError, not AssertionError."""

    def test_unmatched_rbrace_raises_parse_error(self):
        parser = c_parser.CParser()
        with self.assertRaises(ParseError):
            parser.parse("}", filename="test.c")


class TestCParser_whole_code(TestCParser_base):
    """Testing of parsing whole chunks of code.

    Since I don't want to rely on the structure of ASTs too
    much, most of these tests are implemented with visitors.
    """

    # A simple helper visitor that lists the values of all the
    # Constant nodes it sees.
    #
    class ConstantVisitor(NodeVisitor):
        def __init__(self):
            self.values = []

        def visit_Constant(self, node):
            self.values.append(node.value)

    # This visitor counts the amount of references to the ID
    # with the name provided to it in the constructor.
    #
    class IDNameCounter(NodeVisitor):
        def __init__(self, name):
            self.name = name
            self.nrefs = 0

        def visit_ID(self, node):
            if node.name == self.name:
                self.nrefs += 1

    # Counts the amount of nodes of a given class
    #
    class NodeKlassCounter(NodeVisitor):
        def __init__(self, node_klass):
            self.klass = node_klass
            self.n = 0

        def generic_visit(self, node):
            if node.__class__ == self.klass:
                self.n += 1

            NodeVisitor.generic_visit(self, node)

    def assert_all_Constants(self, code, constants):
        """Asserts that the list of all Constant values (by
        'preorder' appearance) in the chunk of code is as
        given.
        """
        if isinstance(code, str):
            parsed = self.parse(code)
        else:
            parsed = code

        cv = self.ConstantVisitor()
        cv.visit(parsed)
        self.assertEqual(cv.values, constants)

    def assert_num_ID_refs(self, code, name, num):
        """Asserts the number of references to the ID with
        the given name.
        """
        if isinstance(code, str):
            parsed = self.parse(code)
        else:
            parsed = code

        iv = self.IDNameCounter(name)
        iv.visit(parsed)
        self.assertEqual(iv.nrefs, num)

    def assert_num_klass_nodes(self, code, klass, num):
        """Asserts the amount of klass nodes in the code."""
        if isinstance(code, str):
            parsed = self.parse(code)
        else:
            parsed = code

        cv = self.NodeKlassCounter(klass)
        cv.visit(parsed)
        self.assertEqual(cv.n, num)

    def test_generic_selection_visitors(self):
        ast = self.parse("int v = _Generic(0, int[1]: 2, default: 3);")
        self.assert_all_Constants(ast, ["0", "1", "2", "3"])
        self.assert_num_klass_nodes(ast, GenericSelection, 1)
        self.assert_num_klass_nodes(ast, GenericAssociation, 2)
        self.assert_num_klass_nodes(ast, Typename, 1)

    def test_expressions(self):
        e1 = """int k = (r + 10.0) >> 6 + 8 << (3 & 0x14);"""
        self.assert_all_Constants(e1, ["10.0", "6", "8", "3", "0x14"])

        e2 = r"""char n = '\n', *prefix = "st_";"""
        self.assert_all_Constants(e2, [r"'\n'", '"st_"'])

        s1 = r"""int main() {
                    int i = 5, j = 6, k = 1;
                    if ((i=j && k == 1) || k > j)
                        printf("Hello, world\n");
                    return 0;
                 }"""
        ps1 = self.parse(s1)
        self.assert_all_Constants(ps1, ["5", "6", "1", "1", '"Hello, world\\n"', "0"])
        self.assert_num_ID_refs(ps1, "i", 1)
        self.assert_num_ID_refs(ps1, "j", 2)

    def test_statements(self):
        s1 = r"""
            void foo(){
            if (sp == 1)
                if (optind >= argc ||
                    argv[optind][0] != '-' || argv[optind][1] == '\0')
                        return -1;
                else if (strcmp(argv[optind], "--") == 0) {
                    optind++;
                    return -1;
                }
            }
        """

        self.assert_all_Constants(
            s1, ["1", "0", r"'-'", "1", r"'\0'", "1", r'"--"', "0", "1"]
        )

        ps1 = self.parse(s1)
        self.assert_num_ID_refs(ps1, "argv", 3)
        self.assert_num_ID_refs(ps1, "optind", 5)

        self.assert_num_klass_nodes(ps1, If, 3)
        self.assert_num_klass_nodes(ps1, Return, 2)
        self.assert_num_klass_nodes(ps1, FuncCall, 1)  # strcmp
        self.assert_num_klass_nodes(ps1, BinaryOp, 7)

        # In the following code, Hash and Node were defined as
        # int to pacify the parser that sees they're used as
        # types
        #
        s2 = r"""
        typedef int Hash, Node;

        void HashDestroy(Hash* hash)
        {
            unsigned int i;

            if (hash == NULL)
                return;

            for (i = 0; i < hash->table_size; ++i)
            {
                Node* temp = hash->heads[i];

                while (temp != NULL)
                {
                    Node* temp2 = temp;

                    free(temp->entry->key);
                    free(temp->entry->value);
                    free(temp->entry);

                    temp = temp->next;

                    free(temp2);
                }
            }

            free(hash->heads);
            hash->heads = NULL;

            free(hash);
        }
        """

        ps2 = self.parse(s2)
        self.assert_num_klass_nodes(ps2, FuncCall, 6)
        self.assert_num_klass_nodes(ps2, FuncDef, 1)
        self.assert_num_klass_nodes(ps2, For, 1)
        self.assert_num_klass_nodes(ps2, While, 1)
        self.assert_num_klass_nodes(ps2, StructRef, 10)

        # declarations don't count
        self.assert_num_ID_refs(ps2, "hash", 6)
        self.assert_num_ID_refs(ps2, "i", 4)

        s3 = r"""
        void x(void) {
          int a, b;
          if (a < b)
            do {
              a = 0;
            } while (0);
          else if (a == b) {
            a = 1;
          }
        }
        """

        ps3 = self.parse(s3)
        self.assert_num_klass_nodes(ps3, DoWhile, 1)
        self.assert_num_ID_refs(ps3, "a", 4)
        self.assert_all_Constants(ps3, ["0", "0", "1"])

    def test_empty_statements(self):
        s1 = r"""
        void foo(void){
            ;
            return;;

            ;
        }
        """
        ps1 = self.parse(s1)
        self.assert_num_klass_nodes(ps1, EmptyStatement, 3)
        self.assert_num_klass_nodes(ps1, Return, 1)
        self.assert_coord(ps1.ext[0].body.block_items[0], 3)
        self.assert_coord(ps1.ext[0].body.block_items[1], 4)
        self.assert_coord(ps1.ext[0].body.block_items[2], 4)
        self.assert_coord(ps1.ext[0].body.block_items[3], 6)

    def test_switch_statement(self):
        def assert_case_node(node, const_value):
            self.assertIsInstance(node, Case)
            self.assertIsInstance(node.expr, Constant)
            self.assertEqual(node.expr.value, const_value)

        def assert_default_node(node):
            self.assertIsInstance(node, Default)

        s1 = r"""
        int foo(void) {
            switch (myvar) {
                case 10:
                    k = 10;
                    p = k + 1;
                    return 10;
                case 20:
                case 30:
                    return 20;
                default:
                    break;
            }
            return 0;
        }
        """
        ps1 = self.parse(s1)
        switch = ps1.ext[0].body.block_items[0]

        block = switch.stmt.block_items
        self.assertEqual(len(block), 4)
        assert_case_node(block[0], "10")
        self.assertEqual(len(block[0].stmts), 3)
        assert_case_node(block[1], "20")
        self.assertEqual(len(block[1].stmts), 0)
        assert_case_node(block[2], "30")
        self.assertEqual(len(block[2].stmts), 1)
        assert_default_node(block[3])

        s2 = r"""
        int foo(void) {
            switch (myvar) {
                default:
                    joe = moe;
                    return 10;
                case 10:
                case 20:
                case 30:
                case 40:
                    break;
            }
            return 0;
        }
        """
        ps2 = self.parse(s2)
        switch = ps2.ext[0].body.block_items[0]

        block = switch.stmt.block_items
        self.assertEqual(len(block), 5)
        assert_default_node(block[0])
        self.assertEqual(len(block[0].stmts), 2)
        assert_case_node(block[1], "10")
        self.assertEqual(len(block[1].stmts), 0)
        assert_case_node(block[2], "20")
        self.assertEqual(len(block[1].stmts), 0)
        assert_case_node(block[3], "30")
        self.assertEqual(len(block[1].stmts), 0)
        assert_case_node(block[4], "40")
        self.assertEqual(len(block[4].stmts), 1)

        s3 = r"""
        int foo(void) {
            switch (myvar) {
            }
            return 0;
        }
        """
        ps3 = self.parse(s3)
        switch = ps3.ext[0].body.block_items[0]

        self.assertEqual(switch.stmt.block_items, [])

    def test_for_statement(self):
        s2 = r"""
        void x(void)
        {
            int i;
            for (i = 0; i < 5; ++i) {
                x = 50;
            }
        }
        """
        ps2 = self.parse(s2)
        self.assert_num_klass_nodes(ps2, For, 1)
        # here there are 3 refs to 'i' since the declaration doesn't count as
        # a ref in the visitor
        #
        self.assert_num_ID_refs(ps2, "i", 3)

        s3 = r"""
        void x(void)
        {
            for (int i = 0; i < 5; ++i) {
                x = 50;
            }
        }
        """
        ps3 = self.parse(s3)
        self.assert_num_klass_nodes(ps3, For, 1)
        # here there are 2 refs to 'i' since the declaration doesn't count as
        # a ref in the visitor
        #
        self.assert_num_ID_refs(ps3, "i", 2)

        s4 = r"""
        void x(void) {
            for (int i = 0;;)
                i;
        }
        """
        ps4 = self.parse(s4)
        self.assert_num_ID_refs(ps4, "i", 1)

    def _open_c_file(self, name):
        """Find a c file by name, taking into account the current dir can be
        in a couple of typical places
        """
        testdir = os.path.dirname(__file__)
        name = os.path.join(testdir, "c_files", name)
        assert os.path.exists(name)
        return open(name)

    def test_whole_file(self):
        # See how pycparser handles a whole, real C file.
        #
        with self._open_c_file("memmgr_with_h.c") as f:
            code = f.read()
        p = self.parse(code)

        self.assert_num_klass_nodes(p, FuncDef, 5)

        # each FuncDef also has a FuncDecl. 4 declarations
        # + 5 definitions, overall 9
        self.assert_num_klass_nodes(p, FuncDecl, 9)

        self.assert_num_klass_nodes(p, Typedef, 4)

        self.assertEqual(p.ext[4].coord.line, 88)
        self.assertEqual(p.ext[4].coord.file, "./memmgr.h")

        self.assertEqual(p.ext[6].coord.line, 10)
        self.assertEqual(p.ext[6].coord.file, "memmgr.c")

    def test_whole_file_with_stdio(self):
        # Parse a whole file with stdio.h included by cpp
        #
        with self._open_c_file("cppd_with_stdio_h.c") as f:
            code = f.read()
        p = self.parse(code)

        self.assertIsInstance(p.ext[0], Typedef)
        self.assertEqual(p.ext[0].coord.line, 213)
        self.assertEqual(p.ext[0].coord.file, r"D:\eli\cpp_stuff\libc_include/stddef.h")

        self.assertIsInstance(p.ext[-1], FuncDef)
        self.assertEqual(p.ext[-1].coord.line, 15)
        self.assertEqual(p.ext[-1].coord.file, "example_c_file.c")

        self.assertIsInstance(p.ext[-8], Typedef)
        self.assertIsInstance(p.ext[-8].type, TypeDecl)
        self.assertEqual(p.ext[-8].name, "cookie_io_functions_t")


class TestCParser_typenames(TestCParser_base):
    """Test issues related to the typedef-name problem."""

    def test_innerscope_typedef(self):
        # should fail since TT is not a type in bar
        s1 = r"""
            void foo() {
              typedef char TT;
              TT x;
            }
            void bar() {
              TT y;
            }
            """
        self.assertRaises(ParseError, self.parse, s1)

        # should succeed since TT is not a type in bar
        s2 = r"""
            void foo() {
              typedef char TT;
              TT x;
            }
            void bar() {
                unsigned TT;
            }
            """
        self.assertIsInstance(self.parse(s2), FileAST)

    def test_ambiguous_parameters(self):
        # From ISO/IEC 9899:TC2, 6.7.5.3.11:
        # "If, in a parameter declaration, an identifier can be treated either
        #  as a typedef name or as a parameter name, it shall be taken as a
        #  typedef name."

        # foo takes an int named aa
        # bar takes a function taking a TT
        s1 = r"""
        typedef char TT;
        int foo(int (aa));
        int bar(int (TT));
        """
        s1_ast = self.parse(s1)
        self.assertEqual(
            expand_decl(s1_ast.ext[1].type.args.params[0]),
            ["Decl", "aa", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(
            expand_decl(s1_ast.ext[2].type.args.params[0]),
            [
                "Typename",
                [
                    "FuncDecl",
                    [["Typename", ["TypeDecl", ["IdentifierType", ["TT"]]]]],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        # foo takes a function taking a char
        # bar takes a function taking a function taking a char
        s2 = r"""
        typedef char TT;
        int foo(int (aa (char)));
        int bar(int (TT (char)));
        """
        s2_ast = self.parse(s2)
        self.assertEqual(
            expand_decl(s2_ast.ext[1].type.args.params[0]),
            [
                "Decl",
                "aa",
                [
                    "FuncDecl",
                    [["Typename", ["TypeDecl", ["IdentifierType", ["char"]]]]],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )
        self.assertEqual(
            expand_decl(s2_ast.ext[2].type.args.params[0]),
            [
                "Typename",
                [
                    "FuncDecl",
                    [
                        [
                            "Typename",
                            [
                                "FuncDecl",
                                [
                                    [
                                        "Typename",
                                        ["TypeDecl", ["IdentifierType", ["char"]]],
                                    ]
                                ],
                                ["TypeDecl", ["IdentifierType", ["TT"]]],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

        # foo takes an int array named aa
        # bar takes a function taking a TT array
        s3 = r"""
        typedef char TT;
        int foo(int (aa[]));
        int bar(int (TT[]));
        """
        s3_ast = self.parse(s3)
        self.assertEqual(
            expand_decl(s3_ast.ext[1].type.args.params[0]),
            [
                "Decl",
                "aa",
                ["ArrayDecl", "", [], ["TypeDecl", ["IdentifierType", ["int"]]]],
            ],
        )
        self.assertEqual(
            expand_decl(s3_ast.ext[2].type.args.params[0]),
            [
                "Typename",
                [
                    "FuncDecl",
                    [
                        [
                            "Typename",
                            [
                                "ArrayDecl",
                                "",
                                [],
                                ["TypeDecl", ["IdentifierType", ["TT"]]],
                            ],
                        ]
                    ],
                    ["TypeDecl", ["IdentifierType", ["int"]]],
                ],
            ],
        )

    def test_innerscope_reuse_typedef_name(self):
        # identifiers can be reused in inner scopes; the original should be
        # restored at the end of the block
        s1 = r"""
            typedef char TT;
            void foo(void) {
              unsigned TT;
              TT = 10;
            }
            TT x = 5;
            """
        s1_ast = self.parse(s1)
        self.assertEqual(
            expand_decl(s1_ast.ext[1].body.block_items[0]),
            ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
        )
        self.assertEqual(
            expand_decl(s1_ast.ext[2]),
            ["Decl", "x", ["TypeDecl", ["IdentifierType", ["TT"]]]],
        )

        # this should be recognized even with an initializer
        s2 = r"""
            typedef char TT;
            void foo(void) {
              unsigned TT = 10;
            }
            """
        s2_ast = self.parse(s2)
        self.assertEqual(
            expand_decl(s2_ast.ext[1].body.block_items[0]),
            ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
        )

        # before the second local variable, TT is a type; after, it's a
        # variable
        s3 = r"""
            typedef char TT;
            void foo(void) {
              TT tt = sizeof(TT);
              unsigned TT = 10;
            }
            """
        s3_ast = self.parse(s3)
        self.assertEqual(
            expand_decl(s3_ast.ext[1].body.block_items[0]),
            ["Decl", "tt", ["TypeDecl", ["IdentifierType", ["TT"]]]],
        )
        self.assertEqual(
            expand_decl(s3_ast.ext[1].body.block_items[1]),
            ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
        )

        # a variable and its type can even share the same name
        s4 = r"""
            typedef char TT;
            void foo(void) {
              TT TT = sizeof(TT);
              unsigned uu = TT * 2;
            }
            """
        s4_ast = self.parse(s4)
        self.assertEqual(
            expand_decl(s4_ast.ext[1].body.block_items[0]),
            ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["TT"]]]],
        )
        self.assertEqual(
            expand_decl(s4_ast.ext[1].body.block_items[1]),
            ["Decl", "uu", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
        )

        # ensure an error is raised if a type, redeclared as a variable, is
        # used as a type
        s5 = r"""
            typedef char TT;
            void foo(void) {
              unsigned TT = 10;
              TT erroneous = 20;
            }
            """
        self.assertRaises(ParseError, self.parse, s5)

        # reusing a type name should work with multiple declarators
        s6 = r"""
            typedef char TT;
            void foo(void) {
              unsigned TT, uu;
            }
            """
        s6_ast = self.parse(s6)
        items = s6_ast.ext[1].body.block_items
        self.assertEqual(
            expand_decl(items[0]),
            ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
        )
        self.assertEqual(
            expand_decl(items[1]),
            ["Decl", "uu", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
        )

        # reusing a type name should work after a pointer
        s7 = r"""
            typedef char TT;
            void foo(void) {
              unsigned * TT;
            }
            """
        s7_ast = self.parse(s7)
        items = s7_ast.ext[1].body.block_items
        self.assertEqual(
            expand_decl(items[0]),
            ["Decl", "TT", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["unsigned"]]]]],
        )

        # redefine a name in the middle of a multi-declarator declaration
        s8 = r"""
            typedef char TT;
            void foo(void) {
                int tt = sizeof(TT), TT, uu = sizeof(TT);
                int uu = sizeof(tt);
            }
            """
        s8_ast = self.parse(s8)
        items = s8_ast.ext[1].body.block_items
        self.assertEqual(
            expand_decl(items[0]),
            ["Decl", "tt", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(
            expand_decl(items[1]),
            ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )
        self.assertEqual(
            expand_decl(items[2]),
            ["Decl", "uu", ["TypeDecl", ["IdentifierType", ["int"]]]],
        )

        # Don't test this until we have support for it
        # self.assertEqual(expand_init(items[0].init),
        #     ['UnaryOp', 'sizeof', ['Typename', ['TypeDecl', ['IdentifierType', ['TT']]]]])
        # self.assertEqual(expand_init(items[2].init),
        #     ['UnaryOp', 'sizeof', ['ID', 'TT']])

    def test_parameter_reuse_typedef_name(self):
        # Parameter names shadow typedef names inside the body; the outer
        # typedef is visible again immediately after the function.
        s1 = r"""
            typedef char TT;
            void foo(unsigned TT, TT bar) {
              TT = 10;
            }
            TT x = 5;
            """
        s1_ast = self.parse(s1)
        self.assertEqual(
            expand_decl(s1_ast.ext[1].decl),
            [
                "Decl",
                "foo",
                [
                    "FuncDecl",
                    [
                        ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
                        ["Decl", "bar", ["TypeDecl", ["IdentifierType", ["TT"]]]],
                    ],
                    ["TypeDecl", ["IdentifierType", ["void"]]],
                ],
            ],
        )

        # Parameter names in a prototype must not hide typedef names in
        # subsequent declarations.
        s2 = r"""
            typedef char TT;
            void foo(unsigned TT, TT bar);
            TT x = 5;
            """
        s2_ast = self.parse(s2)
        self.assertEqual(
            expand_decl(s2_ast.ext[1]),
            [
                "Decl",
                "foo",
                [
                    "FuncDecl",
                    [
                        ["Decl", "TT", ["TypeDecl", ["IdentifierType", ["unsigned"]]]],
                        ["Decl", "bar", ["TypeDecl", ["IdentifierType", ["TT"]]]],
                    ],
                    ["TypeDecl", ["IdentifierType", ["void"]]],
                ],
            ],
        )

        # ensure an error is raised if a type, redeclared as a parameter, is
        # used as a type
        s3 = r"""
            typedef char TT;
            void foo(unsigned TT, TT bar) {
              TT erroneous = 20;
            }
            """
        self.assertRaises(ParseError, self.parse, s3)

    def test_nested_function_decls(self):
        # parameter names of nested function declarations must not escape into
        # the top-level function _definition's_ scope; the following must
        # succeed because TT is still a typedef inside foo's body
        s1 = r"""
            typedef char TT;
            void foo(unsigned bar(int TT)) {
              TT x = 10;
            }
            """
        self.assertIsInstance(self.parse(s1), FileAST)

    def test_for_loop_reuse_typedef_name(self):
        # Looking for an else peeks at TT while the loop's TT is still visible.
        s = """
            typedef char TT;
            void foo(void) {
                for (unsigned TT = 0; TT < 3; TT++)
                    if (TT) TT++;
                TT *x;
            }
        """
        items = self.parse(s).ext[1].body.block_items
        self.assertEqual(
            expand_decl(items[-1]),
            ["Decl", "x", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["TT"]]]]],
        )

    def test_buffered_identifiers_across_statement_expression_scope(self):
        # Scanning the parenthesized declarator reads through the inner block
        # before parsing it. Its T must still be interpreted in the right scope.
        tree = self.parse("""
            typedef char T;
            void f(void) {
                int (a[sizeof(({ int T = 0; T++; T; }))]);
                T *x;
            }
        """)
        array, pointer = tree.ext[1].body.block_items
        inner = array.type.dim.expr.block_items
        self.assertEqual(inner[1].expr.name, "T")
        self.assertEqual(
            expand_decl(pointer),
            ["Decl", "x", ["PtrDecl", ["TypeDecl", ["IdentifierType", ["T"]]]]],
        )

    def test_function_returning_function_pointer_parameter_scope(self):
        tree = self.parse("""
            typedef int T;
            typedef int U;
            int (*f(int T))(int U) {
                T++;
                U value = 0;
                return 0;
            }
            T x;
        """)
        body = tree.ext[2].body.block_items
        self.assertEqual(body[0].expr.name, "T")
        self.assertEqual(body[1].type.type.names, ["U"])
        self.assertEqual(tree.ext[-1].type.type.names, ["T"])

    def test_old_style_parameter_scope(self):
        tree = self.parse("""
            int f(x)
                int x;
            {
                return x;
            }
            typedef int x;
        """)
        self.assertEqual(tree.ext[0].param_decls[0].name, "x")
        self.assertIsInstance(tree.ext[1], Typedef)
        self.assertEqual(tree.ext[1].name, "x")

    def test_for_loop_scope_before_closing_brace(self):
        # Looking for an else peeks at the function's closing brace. Both the
        # loop's TT and the function's TT must go out of scope.
        s = """
            typedef char TT;
            void foo(void) {
                int TT;
                for (unsigned TT = 0; TT < 3; TT++)
                    if (TT) TT++;
            }
            TT x;
        """
        tree = self.parse(s)
        self.assertEqual(
            expand_decl(tree.ext[-1]),
            ["Decl", "x", ["TypeDecl", ["IdentifierType", ["TT"]]]],
        )

    def test_samescope_reuse_name(self):
        # a typedef name cannot be reused as an object name in the same scope
        s1 = r"""
            typedef char TT;
            char TT = 5;
            """
        self.assertRaises(ParseError, self.parse, s1)

        # ...and vice-versa
        s2 = r"""
            char TT = 5;
            typedef char TT;
            """
        self.assertRaises(ParseError, self.parse, s2)

    def test_label_empty_statement(self):
        # Labels with empty statements and no semicolon should be parsed correctly
        s1 = r"""
            int main() {
                int i = 0;
                label0: i++;
                label1:
            }
            """
        s1_ast: FileAST = self.parse(s1)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[1], Label)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[1].stmt, UnaryOp)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[2], Label)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[2].stmt, EmptyStatement)

    def test_case_empty_statement(self):
        # Labels with empty statements and no semicolon should be parsed correctly
        s1 = r"""
            int main() {
                int i = 0;
                switch (i) {
                    case 0:
                        i = 1;
                    case 1:
                }
                return i;
            }
            """
        s2 = r"""
            int main() {
                int i = 0;
                switch (i) {
                    case 0:
                        i = 1;
                    default:
                }
                return i;
            }
            """
        s1_ast: FileAST = self.parse(s1)
        s2_ast: FileAST = self.parse(s2)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[1], Switch)
        self.assertIsInstance(s1_ast.ext[0].body.block_items[1].stmt, Compound)
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[1].stmt.block_items[0], Case
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[1].stmt.block_items[0].stmts[0], Assignment
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[1].stmt.block_items[1], Case
        )
        self.assertIsInstance(
            s1_ast.ext[0].body.block_items[1].stmt.block_items[1].stmts[0],
            EmptyStatement,
        )
        self.assertIsInstance(
            s2_ast.ext[0].body.block_items[1].stmt.block_items[1].stmts[0],
            EmptyStatement,
        )


if __name__ == "__main__":
    unittest.main()
