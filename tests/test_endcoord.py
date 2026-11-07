import io
import pickle
import unittest

from examples import c_json
from pycparser import CParser, c_ast
from pycparser.c_lexer import CLexer, Token
from pycparser.c_parser import Coord


class TestEndCoordinates(unittest.TestCase):
    def test_declarators_and_initializers(self):
        ast = CParser().parse("int a = (1 + 2), b = (3);", "in.c")
        a, b = ast.ext
        self.assertEqual(a.endcoord, Coord("in.c", 1, 16))
        self.assertEqual(b.endcoord, Coord("in.c", 1, 25))
        self.assertEqual(a.type.endcoord, Coord("in.c", 1, 6))
        self.assertEqual(a.type.type.endcoord, Coord("in.c", 1, 4))
        self.assertEqual(a.init.endcoord, Coord("in.c", 1, 15))
        self.assertEqual(b.init.endcoord, Coord("in.c", 1, 24))
        self.assertEqual(ast.endcoord, Coord("in.c", 1, 26))

        decl = CParser().parse("int (*f)(int x, ...);").ext[0]
        self.assertEqual(decl.endcoord, Coord("", 1, 21))
        self.assertEqual(decl.type.endcoord, Coord("", 1, 21))
        self.assertEqual(decl.type.type.endcoord, Coord("", 1, 21))
        params = decl.type.type.args
        self.assertEqual(params.endcoord, Coord("", 1, 20))
        self.assertEqual(params.params[-1].endcoord, Coord("", 1, 20))

        decl = CParser().parse("int (*a[2])(int);").ext[0]
        self.assertEqual(decl.type.endcoord, Coord("", 1, 17))
        self.assertEqual(decl.type.type.endcoord, Coord("", 1, 17))
        self.assertEqual(decl.type.type.type.endcoord, Coord("", 1, 17))

    def test_expression_end_is_not_lookahead(self):
        ast = CParser().parse("void f(void) { x = (a + b) * c; return x; }")
        func = ast.ext[0]
        assign, ret = func.body.block_items
        self.assertEqual(assign.endcoord, Coord("", 1, 31))
        self.assertEqual(assign.rvalue.left.endcoord, Coord("", 1, 26))
        self.assertEqual(assign.rvalue.left.right.endcoord, Coord("", 1, 26))
        self.assertEqual(ret.expr.endcoord, Coord("", 1, 41))
        self.assertEqual(ret.endcoord, Coord("", 1, 42))
        self.assertEqual(func.body.endcoord, Coord("", 1, 44))
        self.assertEqual(func.endcoord, Coord("", 1, 44))
        self.assertEqual(func.decl.endcoord, Coord("", 1, 13))

    def test_string_spelling_and_line_directives(self):
        parser = CParser()
        ast = parser.parse(
            '#line 10 "one.h"\nchar *x = "abc"\n'
            '#line 20 "two.h"\n"def";\n'
            '#line 30 "later.h"\n',
            "in.c",
        )
        literal = ast.ext[0].init
        self.assertEqual(literal.coord, Coord("one.h", 10, 11))
        self.assertEqual(literal.endcoord, Coord("two.h", 20, 6))
        self.assertEqual(ast.endcoord, Coord("two.h", 20, 7))
        self.assertEqual(parser.parse("int x;").ext[0].endcoord, Coord("", 1, 6))

        # Literal values are normalized; their endpoints use the raw spelling.
        literal = parser.parse(r'char *s = "\x1" "a";').ext[0].init
        self.assertEqual(literal.endcoord, Coord("", 1, 20))
        literal = parser.parse('char *s = "\u00e9";').ext[0].init
        self.assertEqual(literal.endcoord, Coord("", 1, 14))

    def test_initializer_and_postfix_delimiters(self):
        ast = CParser().parse("int a[2] = {1, 2}; void f(void) { a[1]++; g(a); }")
        decl = ast.ext[0]
        post, call = ast.ext[1].body.block_items
        self.assertEqual(decl.type.endcoord, Coord("", 1, 9))
        self.assertEqual(decl.init.endcoord, Coord("", 1, 18))
        self.assertEqual(post.endcoord, Coord("", 1, 41))
        self.assertEqual(post.expr.endcoord, Coord("", 1, 39))
        self.assertEqual(call.endcoord, Coord("", 1, 47))
        self.assertEqual(call.args.endcoord, Coord("", 1, 46))

    def test_switch_normalization(self):
        ast = CParser().parse(
            "void f(void) { switch(x) { case 0: case 1: x++; y=2; break; default: x=3; } }"
        )
        switch = ast.ext[0].body.block_items[0]
        empty, case, default = switch.stmt.block_items
        self.assertEqual(empty.stmts, [])
        self.assertEqual(empty.endcoord, Coord("", 1, 35))
        self.assertEqual(case.endcoord, Coord("", 1, 60))
        self.assertEqual(default.endcoord, Coord("", 1, 73))
        self.assertEqual(switch.stmt.endcoord, Coord("", 1, 76))

        ast = CParser().parse("void f(){switch(x) case 1: break;}")
        case = ast.ext[0].body.block_items[0].stmt
        self.assertEqual(case.endcoord, Coord("", 1, 34))
        ast = CParser().parse("void f(){switch(x) { if(y) case 1: break; }}")
        case = ast.ext[0].body.block_items[0].stmt.block_items[0].iftrue
        self.assertEqual(case.endcoord, Coord("", 1, 42))

        ast = CParser().parse(
            'void f(){switch(x){case 1:\n#line 30 "later.h"\ncase 2: break;}}'
        )
        first, second = ast.ext[0].body.block_items[0].stmt.block_items
        self.assertEqual(first.endcoord, Coord("", 1, 27))
        self.assertEqual(second.endcoord, Coord("later.h", 30, 15))

    def test_c23_attributes_and_types(self):
        ast = CParser(dialect="c23").parse('[[gnu::attr(\n "x", [a])]] int x;')
        attribute = ast.ext[0].attributes[0]
        self.assertEqual(attribute.endcoord, Coord("", 2, 13))
        self.assertEqual(attribute.attributes[0].endcoord, Coord("", 2, 11))
        self.assertEqual(ast.ext[0].endcoord, Coord("", 2, 19))
        ast = CParser(dialect="c23").parse("_BitInt(5) unsigned x; typeof(x) y;")
        self.assertEqual(ast.ext[0].type.type.endcoord, Coord("", 1, 20))
        self.assertEqual(ast.ext[1].type.type.endcoord, Coord("", 1, 33))

    def test_implicit_and_manual_nodes(self):
        node = c_ast.ID("value", Coord("in.c", 1, 1))
        self.assertIsNone(node.endcoord)
        before = repr(node)
        shown = io.StringIO()
        node.show(buf=shown, showcoord=True)
        node.endcoord = Coord("in.c", 1, 6)
        self.assertEqual(repr(node), before)
        after = io.StringIO()
        node.show(buf=after, showcoord=True)
        self.assertEqual(after.getvalue(), shown.getvalue())
        self.assertEqual(pickle.loads(pickle.dumps(node)).endcoord, node.endcoord)
        self.assertEqual(node.children(), ())
        self.assertIsNone(CParser().parse("").endcoord)
        func = CParser().parse("void f(void) { lab: }").ext[0]
        self.assertIsNone(func.decl.type.args.params[0].type.endcoord)
        self.assertIsNone(func.body.block_items[0].stmt.endcoord)
        decl = CParser().parse("int f(register x);").ext[0]
        self.assertIsNone(decl.type.args.params[0].type.type.endcoord)

    def test_json_round_trip(self):
        ast = CParser().parse("int x = 42;", "in.c")
        restored = c_json.from_json(c_json.to_json(ast))
        assert isinstance(restored, c_ast.FileAST)
        self.assertEqual(restored.ext[0].init.endcoord, Coord("in.c", 1, 11))
        legacy = {"_nodetype": "ID", "name": "x", "coord": "in.c:1:1"}
        self.assertIsNone(c_json.from_dict(legacy).endcoord)

    def test_token_end_before_normalization_and_custom_lexer(self):
        lexer = CLexer(lambda *args: self.fail(str(args)), dialect="c23")
        lexer.input('[[a(\n "x")]]')
        lexer.token()
        lexer.token()
        arguments = lexer.token()
        assert arguments is not None
        self.assertEqual(arguments.value, '\n "x"')
        self.assertEqual((arguments.end_lineno, arguments.end_column), (2, 6))
        token = Token("ID", "abc", 4, 2, "in.c")
        self.assertEqual((token.end_lineno, token.end_column), (4, 5))
        self.assertEqual(
            repr(token),
            "Token(type='ID', value='abc', lineno=4, column=2, filename='in.c')",
        )

        class LegacyLexer(CLexer):
            def token(self):
                token = super().token()
                if token is not None:
                    del token.end_lineno
                    del token.end_column
                return token

        ast = CParser(lexer=LegacyLexer).parse("int x;")
        self.assertEqual(ast.ext[0].endcoord, Coord("", 1, 6))
