#-----------------------------------------------------------------
# pycparser: __init__.py
#
# This package file exports some convenience functions for
# interacting with pycparser
#
# Copyright (C) 2008-2015, Eli Bendersky
# License: BSD
#-----------------------------------------------------------------
__all__ = ['c_lexer', 'c_parser', 'c_ast']
__version__ = '2.14'

from subprocess import Popen, PIPE
from .c_parser import CParser


def preprocess_file(filename, cpp_path='cpp', cpp_args=''):
    """ Preprocess a file using cpp.

        filename:
            Name of the file you want to preprocess.

        cpp_path:
        cpp_args:
            Refer to the documentation of parse_file for the meaning of these
            arguments.

        When successful, returns the preprocessed file's contents.
        Errors from cpp will be printed out.
    """
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

    return text


def parse_file(filename, use_cpp=False, cpp_path='cpp', cpp_args='',
               parser=None):
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
            If use_cpp is True, set this to the command line arguments strings
            to cpp. Be careful with quotes - it's best to pass a raw string
            (r'') here. For example:
            r'-I../utils/fake_libc_include'
            If several arguments are required, pass a list of strings.

        parser:
            Optional parser object to be used instead of the default CParser

        When successful, an AST is returned. ParseError can be
        thrown if the file doesn't parse successfully.

        Errors from cpp will be printed out.
    """
    if use_cpp:
        text = preprocess_file(filename, cpp_path, cpp_args)
    else:
        with open(filename, 'rU') as f:
            text = f.read()

    if parser is None:
        parser = CParser()
    return parser.parse(text, filename)

def clean_code(code, comments=True, macros=False):
    """ Naive comment and macro striping from source code

        comments:
            If True, all comments are stripped from code

        macros:
            If True, all macros are stripped from code

        Returns cleaned code. Line numbers are preserved with blank lines,
        and multiline comments and macros are supported. BUT comments-like
        strings are (wrongfuly) treated as comments.
    """
    if macros:
        lines = code.split('\n')
        in_macro = False
        for i in range(len(lines)):
            l = lines[i].strip()

            if l.startswith('#') or in_macro:
                lines[i] = ''
                in_macro = l.endswith('\\')
        code = '\n'.join(lines)
    
    if comments:
        idx = 0
        comment_start = None
        while idx < len(code)-1:
            if comment_start is None and code[idx:idx+2] == '//':
                end_idx = code.find('\n', idx)
                code = code[:idx]+code[end_idx:]
                idx -= end_idx - idx
            elif comment_start is None and code[idx:idx+2] == '/*':
                comment_start = idx
            elif comment_start is not None and code[idx:idx+2] == '*/':
                code = code[:comment_start]+'\n'*code[comment_start:idx].count('\n')+code[idx+2:]
                idx -= idx - comment_start
                comment_start = None
            idx += 1
    
    return code
