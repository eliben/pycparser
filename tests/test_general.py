import sys
import unittest

sys.path.insert(0, '..')
from pycparser import parse_file, c_ast

# Portable cpp path for Windows and Linux/Unix
CPPPATH = '../utils/cpp.exe' if sys.platform == 'win32' else 'cpp'


# Test successful parsing
#
class TestParsing(unittest.TestCase):
    def test_without_cpp(self):
        ast = parse_file('c_files/example_c_file.c')
        self.failUnless(isinstance(ast, c_ast.FileAST))

    def test_with_cpp(self):
        ast = parse_file('c_files/memmgr.c', use_cpp=True,
            cpp_path=CPPPATH,
            cpp_args=r'-I../utils/fake_libc_include')
        self.failUnless(isinstance(ast, c_ast.FileAST))
    
        ast2 = parse_file('c_files/year.c', use_cpp=True,
            cpp_path=CPPPATH, 
            cpp_args=r'-I../utils/fake_libc_include')
    
        self.failUnless(isinstance(ast2, c_ast.FileAST))


if __name__ == '__main__':
    unittest.main()

        



