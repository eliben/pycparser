import sys
sys.path.insert(0, '../..')

from pycparser import c_parser, c_ast, parse_file


if __name__ == "__main__":
    ast = parse_file('zc_pp.c', use_cpp=True, cpp_path="../cpp.exe")
    

