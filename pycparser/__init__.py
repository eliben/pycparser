#-----------------------------------------------------------------
# pycparser: __init__.py
#
# This package file exports some convenience functions for 
# interacting with pycparser
#
# Copyright (C) 2008-2011, Eli Bendersky
# License: BSD
#-----------------------------------------------------------------

__all__ = ['c_lexer', 'c_parser', 'c_ast']
__version__ = '2.06'

from subprocess import Popen, PIPE

from .c_parser import CParser


def parse_file( filename, use_cpp=False, 
                cpp_path='cpp', cpp_args=''):
    """ Parse a C file using pycparser.
    
        filename:
            Name of the file you want to parse.
        
        use_cpp:
            Set to True if you want to execute the C pre-processor
            on the file prior to parsing it.
        
        cpp_path:
            If use_cpp is True, this is the path to 'cpp' on your
            system. If no path is provided, it attempts to just
            execute 'cpp', so it must be in your PATH.
        
        cpp_args:
            If use_cpp is True, set this to the command line 
            arguments strings to cpp. Be careful with quotes - 
            it's best to pass a raw string (r'') here. 
            For example:
            r'-I../utils/fake_libc_include'
            If several arguments are required, pass a list of 
            strings.
        
        When successful, an AST is returned. ParseError can be 
        thrown if the file doesn't parse successfully.
        
        Errors from cpp will be printed out. 
    """
    if use_cpp:
        path_list = [cpp_path]
        if isinstance(cpp_args, list):
            path_list += cpp_args
        elif cpp_args != '': 
            path_list += [cpp_args]
        path_list += [filename]
        
        try:
            # Note the use of universal_newlines to treat all newlines
            # as \n for Python's purpose
            #
            pipe = Popen(   path_list, 
                            stdout=PIPE, 
                            universal_newlines=True)
            text = pipe.communicate()[0]
        except OSError as e:
            raise RuntimeError("Unable to invoke 'cpp'.  " +
                'Make sure its path was passed correctly\n' +
                ('Original error: %s' % e))
    else:
        text = open(filename, 'rU').read()
    
    parser = CParser()
    return parser.parse(text, filename)
    

if __name__ == "__main__":
    pass
    

