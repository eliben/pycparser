#-----------------------------------------------------------------
# pycparser: using_cpp_libc.py
#
# Shows how to use 'cpp' (the C pre-processor binary) and "fake" libc includes
# to parse a file that includes standard C headers.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import parse_file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename  = sys.argv[1]
    else:
        filename = 'examples/c_files/year.c'

    ast = parse_file(filename, use_cpp=True,
            cpp_path='cpp',
            cpp_args=r'-Iutils/fake_libc_include')
    ast.show()
