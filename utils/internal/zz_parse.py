from pycparser import c_parser, c_generator


if __name__ == "__main__":
    parser = c_parser.CParser()
    code = r'''
    const int ci;
    const int* pci;
    int* const pci;
    _Atomic(int) ai;
    _Atomic(int*) pai;
    _Atomic(_Atomic(int)*) ppai;
    '''

    print(code)
    ast = parser.parse(code, debug=False)
    ast.show(attrnames=True, nodenames=True)
    #print(ast.ext[0].__slots__)
    #print(dir(ast.ext[0]))

    #print("==== From C generator:")
    #generator = c_generator.CGenerator()
    #print(generator.visit(ast))
