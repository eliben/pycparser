import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from examples.dump_ast_dot import _quote, ast_to_dot
from pycparser import c_ast, c_parser


class TestDumpAstDot(unittest.TestCase):
    def test_empty_ast(self):
        self.assertEqual(
            ast_to_dot(c_parser.CParser().parse("")),
            'digraph AST {\n  node [shape=box];\n  n0 [label="FileAST"];\n}\n',
        )

    def test_order_attributes_and_no_mutation(self):
        ast = c_parser.CParser().parse("int main(void) { int x = 0; return x; }")
        before = io.StringIO()
        ast.show(buf=before, showcoord=True)
        first = ast_to_dot(ast)
        self.assertEqual(first, ast_to_dot(ast))
        self.assertIn('n0 -> n1 [label="ext[0]"]', first)
        self.assertIn("name: 'x'", first)
        self.assertIn("quals: []", first)
        self.assertIn("value: '0'", first)
        self.assertLess(
            first.index('label="block_items[0]"'), first.index('label="block_items[1]"')
        )
        self.assertNotIn("coord:", first)
        self.assertIn(
            "coord: sample.c:1:",
            ast_to_dot(c_parser.CParser().parse("int x;", filename="sample.c"), True),
        )
        after = io.StringIO()
        ast.show(buf=after, showcoord=True)
        self.assertEqual(before.getvalue(), after.getvalue())

    def test_quote(self):
        self.assertEqual(_quote('"\\N\n\x00\t\r雪'), '"\\"\\\\N\\n\\\\x00\\\\t\\\\r雪"')

    def test_deep_tree(self):
        ast = c_ast.ID("leaf")
        for _ in range(1500):
            ast = c_ast.UnaryOp("!", ast)
        self.assertIn('n1500 [label="ID', ast_to_dot(ast))

    @unittest.skipUnless(shutil.which("dot"), "Graphviz dot is not installed")
    def test_graphviz_render_labels(self):
        ast = c_parser.CParser().parse(
            'int main(void) { const char *s = "quoted\\" text\\n"; return 0; }',
            filename='雪\\N"file.c',
        )
        # Exercise attribute escaping independently of the C lexer.
        ast.ext.append(c_ast.Constant("string", '"<> & \\N \\G \\l\n\r\t\x00雪"'))
        dot = ast_to_dot(ast, showcoord=True)
        with tempfile.TemporaryDirectory() as cache_dir:
            result = subprocess.run(
                ["dot", "-Tsvg"],
                input=dot,
                encoding="utf-8",
                capture_output=True,
                check=True,
                env={**os.environ, "XDG_CACHE_HOME": cache_dir},
            )
        svg = ElementTree.fromstring(result.stdout)
        text = "\n".join(svg.itertext())
        self.assertIn("FileAST", text)
        self.assertIn("ext[1]", text)
        self.assertIn("雪", text)
        self.assertIn("\\N", text)
        self.assertIn("\\G", text)
        self.assertIn("\\x00", text)
        self.assertEqual(result.stderr, "")

    def run_cli(self, *args, env=None):
        return subprocess.run(
            [sys.executable, "examples/dump_ast_dot.py", *args],
            encoding="utf-8",
            capture_output=True,
            check=False,
            env=env,
        )

    def test_cli_default_and_help(self):
        default = self.run_cli()
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertTrue(default.stdout.startswith("digraph AST {\n"))
        self.assertEqual(default.stderr, "")
        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("preprocess", help_result.stdout)
        invalid = self.run_cli("--unknown")
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(invalid.stdout, "")
        self.assertIn("usage:", invalid.stderr)

    def test_cli_utf8_output_and_input_encoding(self):
        with tempfile.TemporaryDirectory() as dirname:
            filename = Path(dirname) / "unicode.c"
            filename.write_text('const char *s = "雪";', encoding="utf-8")
            result = self.run_cli(
                str(filename), env={**os.environ, "PYTHONIOENCODING": "ascii"}
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("雪", result.stdout)
            filename.write_bytes('const char *s = "café";'.encode("latin-1"))
            result = self.run_cli("--encoding", "latin-1", str(filename))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("café", result.stdout)
            result = self.run_cli("--encoding", "not-an-encoding", str(filename))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_files_and_errors(self):
        with tempfile.TemporaryDirectory() as dirname:
            filename = Path(dirname) / "input.c"
            filename.write_text("int value = 7;", encoding="utf-8")
            result = self.run_cli("--coord", str(filename))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("coord:", result.stdout)
            self.assertEqual(set(os.listdir(dirname)), {"input.c"})
            filename.write_text("int = ;", encoding="utf-8")
            result = self.run_cli(str(filename))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("input.c", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            filename.write_bytes(b"int x;\xff")
            result = self.run_cli(str(filename))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("Traceback", result.stderr)
            result = self.run_cli(str(filename.with_name("missing.c")))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("missing.c", result.stderr)


if __name__ == "__main__":
    unittest.main()
