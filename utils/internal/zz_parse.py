import sys
sys.path.insert(0, '../..')

from pycparser import c_parser, c_ast, parse_file


if __name__ == "__main__":
    #ast = parse_file('zc_pp.c', use_cpp=True, cpp_path="../cpp.exe")
    parser = c_parser.CParser()

    #code = r'''int ar[30];'''
    code = r'''
    char ***arr3d[40];
    '''

    #code = r'''
    #int foo(int a, int arr[*]);
            #'''
    print(code)
    ast = parser.parse(code)
    ast.show(attrnames=True, nodenames=True)
