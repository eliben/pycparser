# -----------------------------------------------------------------
# pycparser: serialize_ast.py
#
# Simple example of serializing AST
#
# Hart Chu [https://github.com/CtheSky]
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
# -----------------------------------------------------------------
import pickle
import sys
import tempfile

sys.path.extend([".", ".."])
from pycparser import c_parser

text = r"""
void func(void)
{
  x = 1;
}
"""

if __name__ == "__main__":
    parser = c_parser.CParser()
    ast = parser.parse(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pickle") as f:
        dump_filename = f.name
        pickle.dump(ast, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"Dumped to {dump_filename}")

    # Deserialize.
    with open(dump_filename, "rb") as f:
        ast = pickle.load(f)
        ast.show()
