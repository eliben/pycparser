import os
import sys
import tempfile
import unittest

sys.path.insert(0, "..")
from pycparser import CParser, c_ast, parse_file
from tests.test_util import cpp_args, cpp_path, cpp_supported


# Test successful parsing
#
class TestParsing(unittest.TestCase):
    def _find_file(self, name):
        """Find a c file by name, taking into account the current dir can be
        in a couple of typical places
        """
        testdir = os.path.dirname(__file__)
        name = os.path.join(testdir, "c_files", name)
        assert os.path.exists(name)
        return name

    def test_without_cpp(self):
        ast = parse_file(self._find_file("example_c_file.c"))
        self.assertIsInstance(ast, c_ast.FileAST)

    def test_c23_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = os.path.join(directory, "c23.c")
            with open(filename, "w", encoding="utf-8") as source:
                source.write("bool flag = true; void *p = nullptr;")
            ast = parse_file(filename, parser=CParser(dialect="c23"))
        self.assertEqual(ast.ext[0].type.type.names, ["bool"])
        for decl, typ in zip(ast.ext, ("bool", "nullptr_t")):
            self.assertIsInstance(decl.init, c_ast.Constant)
            self.assertEqual(decl.init.type, typ)

    @unittest.skipUnless(cpp_supported(), "cpp only works on Unix")
    def test_with_cpp(self):
        memmgr_path = self._find_file("memmgr.c")
        c_files_path = os.path.dirname(memmgr_path)
        ast = parse_file(
            memmgr_path,
            use_cpp=True,
            cpp_path=cpp_path(),
            cpp_args=cpp_args(f"-I{c_files_path}"),
        )
        self.assertIsInstance(ast, c_ast.FileAST)

        fake_libc = os.path.join(c_files_path, "..", "..", "utils", "fake_libc_include")
        ast2 = parse_file(
            self._find_file("year.c"),
            use_cpp=True,
            cpp_path=cpp_path(),
            cpp_args=cpp_args(f"-I{fake_libc}"),
        )

        self.assertIsInstance(ast2, c_ast.FileAST)

    @unittest.skipUnless(cpp_supported(), "cpp only works on Unix")
    def test_va_arg_preserves_type(self):
        # Issue #533: preprocessing with the fake headers must retain the type.
        fake_libc = os.path.join(
            os.path.dirname(__file__), "..", "utils", "fake_libc_include"
        )
        with tempfile.TemporaryDirectory() as directory:
            filename = os.path.join(directory, "va_arg.c")
            with open(filename, "w", encoding="utf-8") as source:
                source.write("""
                    #include <stdarg.h>
                    int f(int first, ...) {
                        va_list ap;
                        va_start(ap, first);
                        int value = va_arg(ap, int);
                        va_end(ap);
                        return value;
                    }
                """)
            ast = parse_file(
                filename,
                use_cpp=True,
                cpp_path=cpp_path(),
                cpp_args=cpp_args(["-nostdinc", f"-I{fake_libc}"]),
            )
        call = ast.ext[-1].body.block_items[2].init
        self.assertEqual(call.name.name, "__builtin_va_arg")
        self.assertEqual(len(call.args.exprs), 2)
        self.assertIsInstance(call.args.exprs[1], c_ast.Typename)
        self.assertEqual(call.args.exprs[1].type.type.names, ["int"])

    @unittest.skipUnless(cpp_supported(), "cpp only works on Unix")
    def test_cpp_funkydir(self):
        # This test contains Windows specific path escapes
        if sys.platform != "win32":
            return

        c_files_path = os.path.join("tests", "c_files")
        ast = parse_file(
            self._find_file("simplemain.c"),
            use_cpp=True,
            cpp_path=cpp_path(),
            cpp_args=cpp_args(f"-I{c_files_path}"),
        )
        self.assertIsInstance(ast, c_ast.FileAST)

    @unittest.skipUnless(cpp_supported(), "cpp only works on Unix")
    def test_no_real_content_after_cpp(self):
        ast = parse_file(
            self._find_file("empty.h"),
            use_cpp=True,
            cpp_path=cpp_path(),
            cpp_args=cpp_args(),
        )
        self.assertIsInstance(ast, c_ast.FileAST)

    @unittest.skipUnless(cpp_supported(), "cpp only works on Unix")
    def test_c11_with_cpp(self):
        c_files_path = os.path.join("tests", "c_files")
        fake_libc = os.path.join(c_files_path, "..", "..", "utils", "fake_libc_include")
        ast = parse_file(
            self._find_file("c11.c"),
            use_cpp=True,
            cpp_path=cpp_path(),
            # Missing fake headers must not fall back to the host's libc headers.
            cpp_args=cpp_args(["-std=c11", "-nostdinc", f"-I{fake_libc}"]),
        )
        self.assertIsInstance(ast, c_ast.FileAST)
        decls = {node.name: node for node in ast.ext if isinstance(node, c_ast.Decl)}
        self.assertEqual(decls["flag2"].storage, ["_Thread_local"])
        # Unexpanded macro names would also parse, so check their expansion.
        for name in ("once", "destructor_iterations"):
            with self.subTest(name=name):
                self.assertIsInstance(decls[name].init, c_ast.Constant)
                self.assertEqual(decls[name].init.type, "int")


if __name__ == "__main__":
    unittest.main()
