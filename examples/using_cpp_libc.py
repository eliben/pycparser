#-----------------------------------------------------------------
# pycparser: use_cpp_libc.py
#
# Shows how to use the provided 'cpp' (on Windows, substitute for
# the 'real' cpp if you're on Linux/Unix) and "fake" libc includes
# to parse a file that includes standard C headers.
#
# Copyright (C) 2008-2011, Eli Bendersky
# License: BSD
#-----------------------------------------------------------------
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
#
sys.path.extend(['.', '..'])

# Portable cpp path for Windows and Linux/Unix
CPPPATH = '../utils/cpp.exe' if sys.platform == 'win32' else 'cpp'

from pycparser import parse_file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename  = sys.argv[1]
    else:
        filename = 'c_files/year.c'

    ast = parse_file(filename, use_cpp=True,
            cpp_path=CPPPATH, 
            cpp_args=r'-I../utils/fake_libc_include')
    
    ast.show()

