import sys, os
import unittest

sys.path.insert(0, '..')
from pycparser import parse_file, c_ast

# Portable cpp path for Windows and Linux/Unix
CPPPATH = 'utils/cpp.exe' if sys.platform == 'win32' else 'cpp'


# Test successful parsing
#
class TestParsing(unittest.TestCase):
    def _find_file(self, name):
        """ Find a c file by name, taking into account the current dir can be
            in a couple of typical places
        """
        fullnames = [
            os.path.join('c_files', name),
            os.path.join('tests', 'c_files', name)]
        for fullname in fullnames:
            if os.path.exists(fullname):
                return fullname
        assert False, "Unreachable"

    def test_without_cpp(self):
        ast = parse_file(self._find_file('example_c_file.c'))
        self.failUnless(isinstance(ast, c_ast.FileAST))

    def test_with_cpp(self):
        c_files_path = os.path.join('tests', 'c_files')
        ast = parse_file(self._find_file('memmgr.c'), use_cpp=True,
            cpp_path=CPPPATH,
            cpp_args='-I%s' % c_files_path)
        self.failUnless(isinstance(ast, c_ast.FileAST))
    
        ast2 = parse_file(self._find_file('year.c'), use_cpp=True,
            cpp_path=CPPPATH, 
            cpp_args=r'-Iutils/fake_libc_include')
    
        self.failUnless(isinstance(ast2, c_ast.FileAST))


if __name__ == '__main__':
    unittest.main()

        



