===============
pycparser v2.06
===============

:Author: `Eli Bendersky <http://eli.thegreenplace.net>`_


.. contents::
    :backlinks: none

.. sectnum::


Introduction
============

What is pycparser?
------------------

``pycparser`` is a parser for the C language, written in pure Python. It is a module designed to be easily integrated into applications that need to parse C source code.

What is it good for?
--------------------

Anything that needs C code to be parsed. The following are some uses for ``pycparser``, taken from real user reports:

* C code obfuscator
* Front-end for various specialized C compilers
* Static code checker
* Automatic unit-test discovery
* Adding specialized extensions to the C language

``pycparser`` is unique in the sense that it's written in pure Python - a very high level language that's easy to experiment with and tweak. To people familiar with Lex and Yacc, ``pycparser``'s code will be simple to understand.


Which version of C does pycparser support?
------------------------------------------

``pycparser`` aims to support the full C99 language (according to the standard ISO/IEC 9899). This is a new feature in the version 2.x series - earlier versions only supported C89. For more information on the change, read `this wiki page <http://code.google.com/p/pycparser/wiki/C99support>`_.

``pycparser`` doesn't support any GCC extensions. See the `FAQ <http://code.google.com/p/pycparser/wiki/FAQ>`_ for more details.

What grammar does pycparser follow?
-----------------------------------

``pycparser`` very closely follows the C grammar provided in the end of the C99 standard document

How is pycparser licensed?
--------------------------

`New BSD License <http://www.opensource.org/licenses/bsd-license.php>`_

Contact details
---------------

Drop me an email to eliben@gmail.com for any questions regarding ``pycparser``. For reporting problems with ``pycparser`` or submitting feature requests, the best way is to open an issue on the `pycparser page at Google Code <http://code.google.com/p/pycparser/>`_.


Installing
==========

Prerequisites
-------------

* ``pycparser`` was tested on Python 2.6 and 3.2, on both Linux and Windows. It should work on any later version (in both the 2.x and 3.x lines) as well.
* ``pycparser`` uses the PLY module for the actual lexer and parser construction. Install PLY from `its website <http://www.dabeaz.com/ply/>`_.

Installation process
--------------------

Installing ``pycparser`` is very simple. Once you download it from its `website <http://code.google.com/p/pycparser/>`_ and unzip the package, you just have to execute the standard ``python setup.py install``. The setup script will then place the ``pycparser`` module into ``site-packages`` in your Python's installation library.

Alternatively, since ``pycparser`` is listed in the `Python Package Index <http://pypi.python.org/pypi/pycparser>`_ (PyPI), you can install it using your favorite Python packaging/distribution tool, for example with::

    > pip install pycparser

It's recommended to run ``_build_tables.py`` in the ``pycparser`` code directory after installation to make sure the parsing tables of PLY are pre-generated. This can make your code run faster.

Known problems
--------------

* Some users who've installed a new version of ``pycparser`` over an existing version ran into a problem using the newly installed library. This has to do with parse tables staying around as ``.pyc`` files from the older version. If you see unexplained errors from ``pycparser`` after an upgrade, remove it (by deleting the ``pycparser`` directory in your Python's ``site-packages``, or wherever you installed it) and install again.

Using
=====

Interaction with the C preprocessor
-----------------------------------

In order to be compilable, C code must be preprocessed by the C preprocessor - ``cpp``. ``cpp`` handles preprocessing directives like ``#include`` and ``#define``, removes comments, and does other minor tasks that prepare the C code for compilation.

For all but the most trivial snippets of C code, ``pycparser``, like a C compiler, must receive preprocessed C code in order to function correctly. If you import the top-level ``parse_file`` function from the ``pycparser`` package, it will interact with ``cpp`` for you, as long as it's in your PATH, or you provide a path to it. 

On the vast majority of Linux systems, ``cpp`` is installed and is in the PATH. If you're on Windows and don't have ``cpp`` somewhere, you can use the one provided in the ``utils`` directory in ``pycparser``'s distribution. This ``cpp`` executable was compiled from the `LCC distribution <http://www.cs.princeton.edu/software/lcc/>`_, and is provided under LCC's license terms.

What about the standard C library headers?
------------------------------------------

C code almost always includes various header files from the standard C library, like ``stdio.h``. While, with some effort, ``pycparser`` can be made to parse the standard headers from any C compiler, it's much simpler to use the provided "fake" standard  includes in ``utils/fake_libc_include``. These are standard C header files that contain only the bare necessities to allow valid parsing of the files that use them. As a bonus, since they're minimal, it can significantly improve the performance of parsing C files.

See the ``using_cpp_libc.py`` example for more details.

Basic usage
-----------

Take a look at the ``examples`` directory of the distribution for a few examples of using ``pycparser``. These should be enough to get you started.

Advanced usage
--------------

The public interface of ``pycparser`` is well documented with comments in ``pycparser/c_parser.py``. For a detailed overview of the various AST nodes created by the parser, see ``pycparser/_c_ast.cfg``.

There's also a `FAQ available here <http://code.google.com/p/pycparser/wiki/FAQ>`_. In any case, you can always drop me an `email <eliben@gmail.com>`_ for help.

Modifying
=========

There are a few points to keep in mind when modifying ``pycparser``:

* The code for ``pycparser``'s AST nodes is automatically generated from a configuration file - ``_c_ast.cfg``, by ``_ast_gen.py``. If you modify the AST configuration, make sure to re-generate the code.
* Make sure you understand the optimized mode of ``pycparser`` - for that you must read the docstring in the constructor of the ``CParser`` class. For development you should create the parser without optimizations, so that it will regenerate the Yacc and Lex tables when you change the grammar.


Package contents
================

Once you unzip the ``pycparser`` package, you'll see the following files and directories:

README.txt/html:
  This README file.

setup.py:
  Installation script

examples/:
  A directory with some examples of using ``pycparser``

pycparser/:
  The ``pycparser`` module source code.

tests/:
  Unit tests.

utils/cpp.exe:
  A Windows executable of the C pre-processor suitable for working with pycparser

utils/fake_libc_include:
  Minimal standard C library include files that should allow to parse any C code.

utils/internal/:
  Internal utilities for my own use. You probably don't need them.

Contributors
============

Some people have contributed to ``pycparser`` by opening issues on bugs they've found and/or submitting patches. The list of contributors is at `this pycparser Wiki page <http://code.google.com/p/pycparser/wiki/Contributors>`_.

Changelog
=========

+ Version 2.06 (04.02.2012)

  - Issue 48: gracefully handle parsing of empty files
  - Issues 49 & 50: handle more escaped chars in paths to #line - "..\..\test.h".
  - Support for C99 _Complex type.
  - CGenerator moves from examples/ to pycparser/ as a first-class citizen, and
    added some fixes to it. examples/c-to-c.py still stays as a convenience
    wrapper.
  - Fix problem with parsing a file in which the first statement is just a
    semicolon.
  - Improved the AST created for switch statements, making it closer to the
    semantic meaning than to the grammar.

+ Version 2.05 (16.10.2011)

  - Added support for the C99 ``_Bool`` type and ``stdbool.h`` header file
  - Expanded ``examples/explore_ast.py`` with more details on working with the 
    AST
  - Relaxed the rules on parsing unnamed struct members (helps parse ``windows.h``)
  - Bug fixes:
  
    * Fixed spacing issue for some type declarations
    * Issue 47: display empty statements (lone ';') correctly after parsing

+ Version 2.04 (21.05.2011)

  - License changed from LGPL to BSD
  - Bug fixes:
  
    * Issue 31: constraining the scope of typedef definitions
    * Issues 33, 35: fixes for the c-to-c.py example
  
  - Added C99 integer types to fake headers
  - Added unit tests for the c-to-c.py example

+ Version 2.03 (06.03.2011)

  - Bug fixes:
  
    * Issue 17: empty file-level declarations
    * Issue 18: empty statements and declarations in functions
    * Issue 19: anonymous structs & union fields
    * Issue 23: fix coordinates of Cast nodes
  
  - New example added (``examples/c-to-c.py``) for translating ASTs generated by ``pycparser`` back into C code.
  - ``pycparser`` is now on PyPI (Python Package Index)
  - Created `FAQ <http://code.google.com/p/pycparser/wiki/FAQ>`_ on the ``pycparser`` project page 
  - Removed support for Python 2.5. ``pycparser`` supports Python 2 from 2.6 and on, and Python 3.

+ Version 2.02 (10.12.2010)

  * The name of a ``NamedInitializer`` node was turned into a sequence of nodes 
    instead of an attribute, to make it discoverable by the AST node visitor.  
  * Documentation updates

+ Version 2.01 (04.12.2010)

  * Removed dependency on YAML. Parsing of the AST node configuration file is done with a simple parser.
  * Fixed issue 12: installation problems

+ Version 2.00 (31.10.2010)

  * Support for C99 (read `this wiki page <http://code.google.com/p/pycparser/wiki/C99support>`_ for more information).

+ Version 1.08 (09.10.2010)

  * Bug fixes:

    + Correct handling of ``do{} ... while`` statements in some cases
    + Issues 6 & 7: Concatenation of string literals
    + Issue 9: Support for unnamed bitfields in structs

+ Version 1.07 (18.05.2010)

  * Python 3.1 compatibility: ``pycparser`` was modified to run on Python 3.1 as well as 2.6

+ Version 1.06 (10.04.2010)

  * Bug fixes: 

    + coord not propagated to FuncCall nodes
    + lexing of the ^= token (XOREQUALS)
    + parsing failed on some abstract declarator rules

  * Linux compatibility: fixed end-of-line and ``cpp`` path issues to allow all tests and examples run on Linux


+ Version 1.05 (16.10.2009)

  * Fixed the ``parse_file`` auxiliary function to handle multiple arguments to ``cpp`` correctly

+ Version 1.04 (22.05.2009)

  * Added the ``fake_libc_include`` directory to allow parsing of C code that uses standard C library include files without dependency on a real C library.
  * Tested with Python 2.6 and PLY 3.2

+ Version 1.03 (31.01.2009)

  * Accept enumeration lists with a comma after the last item (C99 feature).

+ Version 1.02 (16.01.2009)

  * Fixed problem of parsing struct/enum/union names that were named similarly to previously defined ``typedef`` types. 

+ Version 1.01 (09.01.2009)

  * Fixed subprocess invocation in the helper function parse_file - now it's more portable

+ Version 1.0 (15.11.2008)

  * Initial release
  * Support for ANSI C89




