import json
import os
import sys
import unittest

sys.path.insert(0, ".")
from examples import c_json
from pycparser import c_ast, c_generator, c_parser
from tests.test_util import cpp_supported, run_exe


# Runs all pycparser examples with no command-line arguments and makes sure they
# run successfully (return code = 0), without actually verifying their output.
class TestExamplesSucceed(unittest.TestCase):
    @unittest.skipUnless(cpp_supported(), "cpp only works on Unix")
    def test_all_examples(self):
        root = "./examples"
        for filename in os.listdir(root):
            if os.path.splitext(filename)[1] == ".py":
                with self.subTest(name=filename):
                    path = os.path.join(root, filename)
                    rc, stdout, stderr = run_exe(path)
                    self.assertEqual(
                        rc,
                        0,
                        f'example "{filename}" failed with stdout =\n{stdout}\nstderr =\n{stderr}',
                    )


class TestCJson(unittest.TestCase):
    def _assert_equal(self, actual, expected):
        self.assertIs(type(actual), type(expected))
        if isinstance(expected, c_ast.Node):
            for attr in expected.__slots__:
                if attr != "__weakref__":
                    self._assert_equal(getattr(actual, attr), getattr(expected, attr))
        elif isinstance(expected, c_parser.Coord):
            self.assertEqual(
                (actual.file, actual.line, actual.column),
                (expected.file, expected.line, expected.column),
            )
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for actual_item, expected_item in zip(actual, expected):
                self._assert_equal(actual_item, expected_item)
        else:
            self.assertEqual(actual, expected)

    def _assert_roundtrip(self, node):
        restored = c_json.from_json(c_json.to_json(node))
        self._assert_equal(restored, node)
        return restored

    def test_empty_child_lists(self):
        for node, attr in [
            (c_ast.FileAST([]), "ext"),
            (c_ast.Compound([]), "block_items"),
            (c_ast.Case(c_ast.Constant("int", "0"), []), "stmts"),
            (c_ast.Default([]), "stmts"),
            (c_ast.InitList([]), "exprs"),
        ]:
            with self.subTest(node=type(node).__name__):
                self.assertEqual(json.loads(c_json.to_json(node))[attr], [])
                self._assert_roundtrip(node)

    def test_absent_children(self):
        for node, attr in [
            (c_ast.Compound(None), "block_items"),
            (c_ast.Struct("S", None), "decls"),
            (c_ast.Union("U", None), "decls"),
            (c_ast.Return(None), "expr"),
            (c_ast.FuncCall(c_ast.ID("f"), None), "args"),
        ]:
            with self.subTest(node=type(node).__name__):
                self.assertIsNone(json.loads(c_json.to_json(node))[attr])
                self._assert_roundtrip(node)

    def test_switch_roundtrip(self):
        for body in [
            "case 0: case 1: break;",
            "case 0: default: break;",
            "default: case 0: break;",
            "case 0: case 1: default: break;",
            "case 0: ; default: break;",
            "case 0: break; default: break;",
        ]:
            with self.subTest(body=body):
                node = c_parser.CParser().parse(
                    "void f(int n) { switch (n) { " + body + " } }",
                    filename="switch.c",
                )
                restored = self._assert_roundtrip(node)
                generator = c_generator.CGenerator()
                self.assertEqual(generator.visit(restored), generator.visit(node))

    def test_other_code_roundtrip(self):
        for code in [
            "",
            "void f(void) {}",
            "void f(void) { ; }",
            "struct S; union U; int a[]; void f() { if (1) return; for (;;) break; }",
            "int f(int n) { int a[] = {1, 2}; return a[n]; }",
        ]:
            with self.subTest(code=code):
                node = c_parser.CParser().parse(code, filename="roundtrip.c")
                restored = self._assert_roundtrip(node)
                generator = c_generator.CGenerator()
                self.assertEqual(generator.visit(restored), generator.visit(node))


if __name__ == "__main__":
    unittest.main()
