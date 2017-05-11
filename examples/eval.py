#-----------------------------------------------------------------
# pycparser: ceval.py
#
# Interactive definition explorer - loads a source file,
# then accepts type snippets on input which are parsed
#
# Takes source filename as command line argument
#-----------------------------------------------------------------

import sys
sys.path.extend(['.', '..'])

from pycparser import parse_file, c_parser
import readline

if __name__ == "__main__":
    filename = sys.argv[1]

    parser = c_parser.CParser()
    ast = parse_file(use_cpp = True, filename = filename, parser = parser)
    # ast is not used, but the parser retains its list of typenames

    argparser = parser.get_parameter_parser()

    while True:
        line = raw_input('> ')
        try:
            decl = argparser.parse(line)
            decl.show()
        except:
            sys.excepthook(*sys.exc_info())

