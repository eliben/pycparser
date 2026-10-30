Run these examples from the root directory of pycparser.

Please note that most realistic C code samples would require running the C
preprocessor before passing the code to **pycparser**; see the `README file
<https://github.com/eliben/pycparser/blob/main/README.rst>`_ and
`this blog post
<https://eli.thegreenplace.net/2015/on-parsing-c-type-declarations-and-fake-headers>`_
more details.

Graphviz AST diagrams
--------------------

``dump_ast_dot.py`` exports a parsed AST as UTF-8 DOT on standard output. Each node
shows its class and named attributes; edges show the child field name (including
list indexes). IDs follow a deterministic preorder traversal. ``--coord`` adds
existing source coordinates, without changing their meaning. For example::

    python examples/dump_ast_dot.py examples/c_files/basic.c > ast.dot
    dot -Tsvg ast.dot -o ast.svg

Graphviz is only needed for the second command, not for exporting DOT. With no
filename the example uses ``examples/c_files/basic.c``. Like ``dump_ast.py``, it
expects C that does not require preprocessing (or has already been preprocessed).
Input defaults to UTF-8; ``--encoding`` selects another input encoding.
The script writes no files itself: shell redirection and Graphviz's ``-o`` choose
the output destinations. File and parsing errors go to standard error with exit
status 1 and no DOT output; invalid command-line arguments use argparse's exit
status 2.
