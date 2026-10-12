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
    def test_named_initializer_round_trip(self):
        source = "enum { x }; struct A { int x; }; struct A a[] = { [x].x = 1 };"
        original = c_parser.CParser().parse(source)
        restored = c_json.from_json(c_json.to_json(original))
        generator = c_generator.CGenerator()
        self.assertEqual(generator.visit(restored), generator.visit(original))
        self.assertIn("[x].x = 1", generator.visit(restored))

    def test_named_initializer_legacy_json(self):
        original = c_ast.NamedInitializer([c_ast.ID("x")], c_ast.Constant("int", "1"))
        serialized = c_json.to_dict(original)
        serialized.pop("designator_types")
        restored = c_json.from_dict(serialized)
        assert isinstance(restored, c_ast.NamedInitializer)
        self.assertIsNone(restored.designator_types)
        self.assertEqual(c_generator.CGenerator().visit(restored), ".x = 1")


if __name__ == "__main__":
    unittest.main()
