import unittest

from pycparser import c_ast, c_generator, c_parser
from pycparser.c_lexer import CLexer
from tests.test_c_generator import compare_asts


class TestAttributeLexer(unittest.TestCase):
    def test_opaque_arguments(self):
        def error(msg, line, column):
            self.fail(msg)

        lexer = CLexer(error, dialect="c23")
        lexer.input('[[int::return({if (x) [y];}, 1\'000, "[)]")]] {}')
        tokens = list(iter(lexer.token, None))
        self.assertEqual(
            [t.type for t in tokens],
            [
                "ATTRIBUTE_BEGIN",
                "ID",
                "COLONCOLON",
                "ID",
                "ATTRIBUTE_ARGUMENTS",
                "ATTRIBUTE_END",
                "LBRACE",
                "RBRACE",
            ],
        )
        self.assertEqual(tokens[1].value, "int")
        self.assertEqual(tokens[3].value, "return")
        self.assertEqual(tokens[4].value, '{if (x) [y];}, 1\'000, "[)]"')

    def test_multiline_coordinates_and_input_reset(self):
        lexer = CLexer(lambda msg, line, column: self.fail(msg))
        lexer.input('[\n[deprecated(\n"old"\n)]\n] int x;')
        tokens = list(iter(lexer.token, None))
        self.assertEqual((tokens[0].lineno, tokens[0].column), (1, 1))
        self.assertEqual((tokens[1].lineno, tokens[1].column), (2, 2))
        self.assertEqual((tokens[2].lineno, tokens[2].column), (2, 12))
        self.assertEqual(tokens[2].value, '\n"old"\n')
        self.assertEqual((tokens[4].lineno, tokens[4].column), (5, 3))
        lexer.input("[[int")
        self.assertEqual(
            [t.type for t in iter(lexer.token, None)], ["ATTRIBUTE_BEGIN", "ID"]
        )
        lexer.input("int x[2];")
        self.assertEqual(
            [t.type for t in iter(lexer.token, None)],
            ["INT", "ID", "LBRACKET", "INT_CONST_DEC", "RBRACKET", "SEMI"],
        )


class TestAttributeParser(unittest.TestCase):
    def setUp(self):
        self.parser = c_parser.CParser(dialect="c23")

    def test_groups_names_and_arguments(self):
        decl = self.parser.parse(
            '[[nodiscard, vendor::flag]] [[deprecated("old")]] int f(void);'
        ).ext[0]
        self.assertEqual(len(decl.attributes), 2)
        first, second = decl.attributes
        self.assertIsInstance(first, c_ast.AttributeSpecifier)
        self.assertEqual(first.attributes[0].name, "nodiscard")
        self.assertIsNone(first.attributes[0].namespace)
        self.assertIsNone(first.attributes[0].arguments)
        self.assertEqual(first.attributes[1].name, "flag")
        self.assertEqual(first.attributes[1].namespace, "vendor")
        self.assertEqual(second.attributes[0].name, "deprecated")
        self.assertEqual(second.attributes[0].arguments, '"old"')

    def test_empty_groups_and_argument_clauses(self):
        decl = self.parser.parse(
            "[[]] [[,vendor::plain,,vendor::empty(),]] int x;"
        ).ext[0]
        self.assertEqual(decl.attributes[0].attributes, [])
        plain, empty = decl.attributes[1].attributes
        self.assertIsNone(plain.arguments)
        self.assertEqual(empty.arguments, "")

    def test_keywords_and_typedefs_as_attribute_names(self):
        ast = self.parser.parse(
            "typedef int vendor; [[vendor::int, if, constexpr::return]] int x;"
        )
        attrs = ast.ext[1].attributes[0].attributes
        self.assertEqual((attrs[0].namespace, attrs[0].name), ("vendor", "int"))
        self.assertEqual(attrs[1].name, "if")
        self.assertEqual((attrs[2].namespace, attrs[2].name), ("constexpr", "return"))

    def test_balanced_argument_text(self):
        source = r"""[[vendor::tokens(if (x) { [y]; }, "[)]", '\'', 1'000, /* ) */ 0xA'B)]] int x;"""
        decl = self.parser.parse(source).ext[0]
        self.assertEqual(
            decl.attributes[0].attributes[0].arguments,
            r"""if (x) { [y]; }, "[)]", '\'', 1'000, /* ) */ 0xA'B""",
        )

    def test_standalone_attributes(self):
        ast = self.parser.parse(
            "[[vendor::global]]; void f(void) { [[fallthrough]]; [[]]; }"
        )
        self.assertIsInstance(ast.ext[0], c_ast.AttributeDeclaration)
        first, second = ast.ext[1].body.block_items
        self.assertIsInstance(first, c_ast.AttributeDeclaration)
        self.assertEqual(first.attributes[0].attributes[0].name, "fallthrough")
        self.assertEqual(second.attributes[0].attributes, [])

    def test_prefixed_literals_in_arguments(self):
        decl = self.parser.parse(
            """[[vendor::text(u8']', U'}', L')', u8"[(]", token123')')]] int x;"""
        ).ext[0]
        self.assertEqual(
            decl.attributes[0].attributes[0].arguments,
            """u8']', U'}', L')', u8"[(]", token123')'""",
        )

    def test_comma_declarations_and_typedefs(self):
        ast = self.parser.parse(
            "[[maybe_unused]] int a, b; [[deprecated]] typedef int T; T value;"
        )
        self.assertEqual(ast.ext[0].attributes[0].attributes[0].name, "maybe_unused")
        self.assertEqual(ast.ext[1].attributes[0].attributes[0].name, "maybe_unused")
        self.assertIsInstance(ast.ext[2], c_ast.Typedef)
        self.assertEqual(ast.ext[2].attributes[0].attributes[0].name, "deprecated")
        self.assertEqual(ast.ext[3].type.type.names, ["T"])

    def test_type_and_declarator_attributes(self):
        decl = self.parser.parse(
            "[[vendor::decl]] const int [[vendor::type]] x [[vendor::name]];"
        ).ext[0]
        self.assertEqual(decl.attributes[0].attributes[0].name, "decl")
        self.assertEqual(decl.type.attributes[0].attributes[0].name, "name")
        self.assertIsInstance(decl.type.type, c_ast.AttributedType)
        self.assertEqual(decl.type.type.attributes[0].attributes[0].name, "type")
        self.assertEqual(decl.type.type.type.names, ["int"])
        self.assertEqual(decl.quals, ["const"])

    def test_pointer_and_array_attributes(self):
        ast = self.parser.parse(
            "int * [[vendor::ptr]] const p [[vendor::id]]; int a[2] [[vendor::outer]][3] [[vendor::inner]];"
        )
        pointer, array = ast.ext
        self.assertEqual(pointer.type.attributes[0].attributes[0].name, "ptr")
        self.assertEqual(pointer.type.quals, ["const"])
        self.assertEqual(pointer.type.type.attributes[0].attributes[0].name, "id")
        self.assertEqual(array.type.attributes[0].attributes[0].name, "outer")
        self.assertEqual(array.type.type.attributes[0].attributes[0].name, "inner")

    def test_function_and_parameter_attributes(self):
        func = self.parser.parse(
            "[[nodiscard]] int f([[maybe_unused]] int x, [[vendor::arg]] int) [[unsequenced]] { return x; }"
        ).ext[0]
        self.assertEqual(func.decl.attributes[0].attributes[0].name, "nodiscard")
        self.assertEqual(func.decl.type.attributes[0].attributes[0].name, "unsequenced")
        named, unnamed = func.decl.type.args.params
        self.assertEqual(named.attributes[0].attributes[0].name, "maybe_unused")
        self.assertIsInstance(unnamed, c_ast.Typename)
        self.assertEqual(unnamed.attributes[0].attributes[0].name, "arg")

    def test_abstract_declarator_attributes(self):
        decl = self.parser.parse(
            "void f(int (* [[vendor::ptr]])(int) [[vendor::fn]], int [3] [[vendor::arr]], int (int) [[vendor::direct]]);"
        ).ext[0]
        pointer, array, function = decl.type.args.params
        self.assertEqual(pointer.type.attributes[0].attributes[0].name, "ptr")
        self.assertEqual(pointer.type.type.attributes[0].attributes[0].name, "fn")
        self.assertEqual(array.type.attributes[0].attributes[0].name, "arr")
        self.assertEqual(function.type.attributes[0].attributes[0].name, "direct")

    def test_tags_members_and_enumerators(self):
        ast = self.parser.parse("""
            struct [[deprecated]] S { [[maybe_unused]] int field [[vendor::member]]; };
            union [[vendor::union]] U { int x; };
            enum [[vendor::enum]] E : unsigned int [[vendor::base]] {
                A [[deprecated]] = 1, B [[vendor::enumerator()]]
            };
        """)
        struct, union, enum = ast.ext
        self.assertEqual(struct.type.attributes[0].attributes[0].name, "deprecated")
        member = struct.type.decls[0]
        self.assertEqual(member.attributes[0].attributes[0].name, "maybe_unused")
        self.assertEqual(member.type.attributes[0].attributes[0].name, "member")
        self.assertEqual(union.type.attributes[0].attributes[0].name, "union")
        self.assertEqual(enum.type.attributes[0].attributes[0].name, "enum")
        self.assertEqual(
            enum.type.underlying_type.type.type.attributes[0].attributes[0].name, "base"
        )
        a, b = enum.type.values.enumerators
        self.assertEqual(a.attributes[0].attributes[0].name, "deprecated")
        self.assertEqual(a.value.value, "1")
        self.assertEqual(b.attributes[0].attributes[0].arguments, "")

    def test_statement_attributes(self):
        func = self.parser.parse("""
            void f(int x) {
                [[vendor::expr]] x++;
                [[vendor::if]] if (x) [[vendor::return]] return;
                [[vendor::block]] { [[maybe_unused]] int y; }
            }
        """).ext[0]
        expr, branch, block = func.body.block_items
        self.assertIsInstance(expr, c_ast.AttributedStatement)
        self.assertIsInstance(expr.stmt, c_ast.UnaryOp)
        self.assertEqual(expr.attributes[0].attributes[0].name, "expr")
        self.assertIsInstance(branch.stmt, c_ast.If)
        self.assertIsInstance(branch.stmt.iftrue, c_ast.AttributedStatement)
        self.assertIsInstance(branch.stmt.iftrue.stmt, c_ast.Return)
        self.assertIsInstance(block.stmt, c_ast.Compound)
        self.assertEqual(
            block.stmt.block_items[0].attributes[0].attributes[0].name, "maybe_unused"
        )

    def test_labels_and_switch_cases(self):
        func = self.parser.parse("""
            void f(int x) {
                switch (x) [[vendor::body]] {
                    [[vendor::first]] case 1: [[vendor::second]] case 2:
                        x++; [[fallthrough]];
                    [[vendor::default]] default:
                }
                [[maybe_unused]] label: [[maybe_unused]] int value;
                [[maybe_unused]] end:
            }
        """).ext[0]
        switch, label, declaration, end = func.body.block_items
        self.assertIsInstance(switch.stmt, c_ast.AttributedStatement)
        first, second, default = switch.stmt.stmt.block_items
        self.assertIsInstance(first, c_ast.Case)
        self.assertEqual(first.attributes[0].attributes[0].name, "first")
        self.assertEqual(first.stmts, [])
        self.assertEqual(second.attributes[0].attributes[0].name, "second")
        self.assertIsInstance(second.stmts[1], c_ast.AttributeDeclaration)
        self.assertEqual(default.attributes[0].attributes[0].name, "default")
        self.assertEqual(label.attributes[0].attributes[0].name, "maybe_unused")
        self.assertIsInstance(label.stmt, c_ast.EmptyStatement)
        self.assertEqual(declaration.name, "value")
        self.assertIsInstance(end.stmt, c_ast.EmptyStatement)

    def test_scope_and_parameter_shadowing(self):
        ast = self.parser.parse("""
            typedef int T;
            int f(int T) [[vendor::tokens({ T; })]] {
                [[vendor::tokens({ typedef int Other; })]] int value;
                T = 1;
                return T;
            }
            T outside;
        """)
        func = ast.ext[1]
        self.assertIsInstance(func.body.block_items[1], c_ast.Assignment)
        self.assertEqual(func.body.block_items[1].lvalue.name, "T")
        self.assertEqual(ast.ext[2].type.type.names, ["T"])

    def test_coordinates_and_parser_reuse(self):
        decl = self.parser.parse(
            "[[vendor::attr(\n{ x; }\n)]]\nint x;", "attributes.c"
        ).ext[0]
        group = decl.attributes[0]
        self.assertEqual(str(group.coord), "attributes.c:1:1")
        self.assertEqual(str(group.attributes[0].coord), "attributes.c:1:11")
        self.assertEqual(str(decl.coord), "attributes.c:4:5")
        with self.assertRaises(c_parser.ParseError):
            self.parser.parse("[[vendor::bad({)]] int x;")
        plain = self.parser.parse("int x;").ext[0]
        self.assertEqual(plain.attributes, [])

    def test_legacy_rejection(self):
        parser = c_parser.CParser(dialect="legacy")
        with self.assertRaisesRegex(c_parser.ParseError, "Attributes require C23"):
            parser.parse("[[maybe_unused]] int x;")
        with self.assertRaisesRegex(c_parser.ParseError, "Attributes require C23"):
            parser.parse("int x [[maybe_unused]];")
        with self.assertRaisesRegex(c_parser.ParseError, "Attributes require C23"):
            parser.parse("struct [[deprecated]] S;")
        with self.assertRaisesRegex(c_parser.ParseError, "Attributes require C23"):
            parser.parse("void f(void) { [[fallthrough]]; }")

    def test_malformed_attributes(self):
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[a b]] int x;")
        self.assertRaises(
            c_parser.ParseError, self.parser.parse, "[[vendor:attr]] int x;"
        )
        self.assertRaises(
            c_parser.ParseError, self.parser.parse, "[[vendor : : attr]] int x;"
        )
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[vendor::]] int x;")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[a::b::c]] int x;")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[123]] int x;")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[a] int x;")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[a")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[a]]")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[a(()]] int x;")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "[[a([))]] int x;")
        self.assertRaises(
            c_parser.ParseError, self.parser.parse, '[[a("unterminated)]] int x;'
        )
        self.assertRaises(
            c_parser.ParseError, self.parser.parse, '[[a("line\nbreak")]] int x;'
        )
        self.assertRaises(c_parser.ParseError, self.parser.parse, "int x = [[a]] 1;")
        self.assertRaises(c_parser.ParseError, self.parser.parse, "int [[a]] const x;")
        self.assertRaises(
            c_parser.ParseError, self.parser.parse, "int * const [[a]] x;"
        )


class TestAttributeGeneration(unittest.TestCase):
    def round_trip(self, source):
        parser = c_parser.CParser(dialect="c23")
        ast = parser.parse(source)
        generated = c_generator.CGenerator().visit(ast)
        self.assertTrue(compare_asts(ast, parser.parse(generated)), generated)
        return generated

    def test_declarations_and_declarators(self):
        generated = self.round_trip("""
            [[maybe_unused]] typedef int T;
            [[vendor::decl]] const T [[vendor::type]] * [[vendor::ptr]] const p [[vendor::id]];
            int a [[vendor::name]][2] [[vendor::array]][3] [[vendor::element]];
            [[vendor::decl]] int first, second;
            [[maybe_unused]] auto count [[vendor::name]] = 1;
        """)
        self.assertIn(
            "[[vendor::decl]] const T [[vendor::type]] * [[vendor::ptr]] const p [[vendor::id]];",
            generated,
        )
        self.assertIn(
            "int a [[vendor::name]][2] [[vendor::array]][3] [[vendor::element]];",
            generated,
        )
        self.assertIn("[[maybe_unused]] auto count [[vendor::name]] = 1;", generated)

    def test_tag_and_member_attributes(self):
        generated = self.round_trip("""
            struct [[deprecated("old")]] S { [[maybe_unused]] int value [[vendor::member]]; };
            struct [[vendor::forward]] Forward;
            union [[vendor::union]] U { int x; };
            enum [[vendor::enum]] E : unsigned int [[vendor::base]] { A [[deprecated]], B [[vendor::enumerator()]] };
        """)
        self.assertIn('struct [[deprecated("old")]] S', generated)
        self.assertIn("[[maybe_unused]] int value [[vendor::member]];", generated)
        self.assertIn(
            "enum [[vendor::enum]] E : unsigned int [[vendor::base]]", generated
        )
        self.assertIn("B [[vendor::enumerator()]]", generated)

    def test_shared_attributed_definition(self):
        # The shared type's attributes are emitted once; name attributes
        # still belong to their individual declarators.
        generated = self.round_trip("""
            [[maybe_unused]] struct S { int x; } [[vendor::type]]
                a [[vendor::first]], b [[vendor::second]];
        """)
        self.assertEqual(generated.count("struct S"), 1)
        self.assertEqual(generated.count("[[maybe_unused]]"), 1)
        self.assertEqual(generated.count("[[vendor::type]]"), 1)
        self.assertIn("a [[vendor::first]], b [[vendor::second]];", generated)
        first, second = c_parser.CParser(dialect="c23").parse(generated).ext
        self.assertIs(first.type.type.type, second.type.type.type)

    def test_shared_attributed_typedef(self):
        # A pointer typedef must reuse the same union definition and retain
        # its own pointer attribute when the declarations are grouped.
        generated = self.round_trip("""
            typedef union U { int x; } [[vendor::type]]
                Value, * [[vendor::ptr]] Pointer;
        """)
        self.assertEqual(generated.count("union U"), 1)
        self.assertEqual(generated.count("[[vendor::type]]"), 1)
        self.assertIn("Value, * [[vendor::ptr]] Pointer;", generated)
        value, pointer = c_parser.CParser(dialect="c23").parse(generated).ext
        self.assertIs(value.type.type.type, pointer.type.type.type.type)

    def test_separate_attributed_definitions(self):
        # Identical anonymous definitions remain distinct types, even when
        # their attributes also match.
        generated = self.round_trip("""
            struct { int x; } [[vendor::type]] a;
            struct { int x; } [[vendor::type]] b;
        """)
        self.assertEqual(generated.count("struct"), 2)
        self.assertEqual(generated.count("[[vendor::type]]"), 2)
        first, second = c_parser.CParser(dialect="c23").parse(generated).ext
        self.assertIsNot(first.type.type.type, second.type.type.type)

    def test_functions_and_type_operands(self):
        generated = self.round_trip("""
            [[nodiscard]] int f([[maybe_unused]] int x, [[vendor::arg]] int) [[unsequenced]] { return x; }
            void callback(int (* [[vendor::ptr]])(int) [[vendor::fn]], int [3] [[vendor::array]], int (int) [[vendor::direct]]);
            int * [[vendor::ptr]] (*factory(void) [[vendor::factory]])(int) [[vendor::result]];
            int size = sizeof(int [[vendor::type]] * [[vendor::ptr]]);
            _Atomic(int [[vendor::inner]]) atomic;
            typeof(int [[vendor::inner]]) [[vendor::outer]] value;
        """)
        self.assertIn(
            "[[nodiscard]] int f([[maybe_unused]] int x, [[vendor::arg]] int) [[unsequenced]]",
            generated,
        )
        self.assertIn("sizeof(int [[vendor::type]] * [[vendor::ptr]])", generated)

    def test_statements_and_labels(self):
        self.round_trip("""
            void f(int x) {
                [[vendor::expression]] x++;
                [[vendor::block]] { [[maybe_unused]] int value; }
                [[vendor::if]] if (x) [[vendor::return]] return; else [[vendor::else]] x--;
                [[vendor::while]] while (x) [[vendor::body]] x--;
                [[vendor::do]] do [[vendor::body]] x++; while (x < 1);
                [[vendor::for]] for ([[maybe_unused]] int i=0, j=1; i<j; ++i) [[vendor::body]] x++;
                switch (x) [[vendor::body]] {
                    [[vendor::first]] case 1: [[vendor::second]] case 2:
                        x++; [[fallthrough]];
                    [[vendor::default]] default: [[vendor::break]] break;
                }
                [[maybe_unused]] label: [[maybe_unused]] int value;
                [[maybe_unused]] end:
            }
        """)

    def test_argument_spelling_and_empty_groups(self):
        generated = self.round_trip(
            r"""[[]] [[vendor::int(if (x) { [y]; }, "[)]", '\'', 1'000)]] [[vendor::empty()]] int x;"""
        )
        self.assertIn(
            r"""[[vendor::int(if (x) { [y]; }, "[)]", '\'', 1'000)]]""", generated
        )
        self.assertIn("[[]]", generated)
        self.assertIn("[[vendor::empty()]]", generated)

    def test_standard_attributes_and_standalone_declarations(self):
        self.round_trip("""
            [[deprecated("old")]] int old;
            [[maybe_unused]] int unused;
            [[nodiscard("check")]] int result(void);
            [[noreturn]] void terminate(void);
            int pure(void) [[reproducible]];
            int independent(void) [[unsequenced]];
            [[vendor::global]];
            void f(void) { [[fallthrough]]; [[]]; }
        """)
