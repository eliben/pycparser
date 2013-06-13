=================
pycparser v2.09.1
=================

:Author: `Eli Bendersky <http://eli.thegreenplace.net>`_


.. contents::
    :backlinks: none

.. sectnum::


Introduction
============

What is pycparser?
------------------

**pycparser** is a parser for the C language, written in pure Python. It is a
module designed to be easily integrated into applications that need to parse
C source code.

What is it good for?
--------------------

Anything that needs C code to be parsed. The following are some uses for **pycparser**, taken from real user reports:

* C code obfuscator
* Front-end for various specialized C compilers
* Static code checker
* Automatic unit-test discovery
* Adding specialized extensions to the C language

**pycparser** is unique in the sense that it's written in pure Python - a very high level language that's easy to experiment with and tweak. To people familiar with Lex and Yacc, **pycparser**'s code will be simple to understand.


Which version of C does pycparser support?
------------------------------------------

**pycparser** aims to support the full C99 language (according to the standard ISO/IEC 9899). This is a new feature in the version 2.x series - earlier versions only supported C89.

**pycparser** doesn't support any GCC extensions. See the `FAQ <https://github.com/eliben/pycparser/wiki/FAQ>`_ for more details.

What grammar does pycparser follow?
-----------------------------------

**pycparser** very closely follows the C grammar provided in the end of the C99 standard document

How is pycparser licensed?
--------------------------

`New BSD License <http://www.opensource.org/licenses/bsd-license.php>`_

Contact details
---------------

Drop me an email to eliben@gmail.com for any questions regarding **pycparser**. For reporting problems with **pycparser** or submitting feature requests, the best way is to open an issue on the `pycparser project page <https://github.com/eliben/pycparser/>`_.


Installing
==========

Prerequisites
-------------

* **pycparser** was tested on Python 2.6, 2.7 and 3.2, on both Linux and Windows. It should work on any later version (in both the 2.x and 3.x lines) as well.

**pycparser** has no external dependencies. The only non-stdlib library it uses is PLY, which is bundled in ``pycparser/ply``. The current PLY version is 3.4

Installation process
--------------------

Installing **pycparser** is very simple. Once you download and unzip the package, you just have to execute the standard ``python setup.py install``. The setup script will then place the ``pycparser`` module into ``site-packages`` in your Python's installation library.

Alternatively, since **pycparser** is listed in the `Python Package Index <http://pypi.python.org/pypi/pycparser>`_ (PyPI), you can install it using your favorite Python packaging/distribution tool, for example with::

    > pip install pycparser

It's recommended to run ``_build_tables.py`` in the **pycparser** code directory after installation to make sure the parsing tables are pre-generated. This can make your code run faster.

Known problems
--------------

* Some users who've installed a new version of **pycparser** over an existing version ran into a problem using the newly installed library. This has to do with parse tables staying around as ``.pyc`` files from the older version. If you see unexplained errors from **pycparser** after an upgrade, remove it (by deleting the ``pycparser`` directory in your Python's ``site-packages``, or wherever you installed it) and install again.

Using
=====

Interaction with the C preprocessor
-----------------------------------

In order to be compilable, C code must be preprocessed by the C preprocessor - ``cpp``. ``cpp`` handles preprocessing directives like ``#include`` and ``#define``, removes comments, and does other minor tasks that prepare the C code for compilation.

For all but the most trivial snippets of C code, **pycparser**, like a C compiler, must receive preprocessed C code in order to function correctly. If you import the top-level ``parse_file`` function from the **pycparser** package, it will interact with ``cpp`` for you, as long as it's in your PATH, or you provide a path to it.

On the vast majority of Linux systems, ``cpp`` is installed and is in the PATH. If you're on Windows and don't have ``cpp`` somewhere, you can use the one provided in the ``utils`` directory in **pycparser**'s distribution. This ``cpp`` executable was compiled from the `LCC distribution <http://www.cs.princeton.edu/software/lcc/>`_, and is provided under LCC's license terms.

What about the standard C library headers?
------------------------------------------

C code almost always includes various header files from the standard C library, like ``stdio.h``. While, with some effort, **pycparser** can be made to parse the standard headers from any C compiler, it's much simpler to use the provided "fake" standard  includes in ``utils/fake_libc_include``. These are standard C header files that contain only the bare necessities to allow valid parsing of the files that use them. As a bonus, since they're minimal, it can significantly improve the performance of parsing large C files.

The key point to understand here is that **pycparser** doesn't really care about the semantics of types. It only needs to know whether some token encountered in the source is a previously defined type. This is essential in order to be able to parse C correctly.

See the ``using_cpp_libc.py`` example for more details.

Basic usage
-----------

Take a look at the ``examples`` directory of the distribution for a few examples of using **pycparser**. These should be enough to get you started.

Advanced usage
--------------

The public interface of **pycparser** is well documented with comments in ``pycparser/c_parser.py``. For a detailed overview of the various AST nodes created by the parser, see ``pycparser/_c_ast.cfg``.

There's also a `FAQ available here <https://github.com/eliben/pycparser/wiki/FAQ>`_. In any case, you can always drop me an `email <eliben@gmail.com>`_ for help.

Modifying
=========

There are a few points to keep in mind when modifying **pycparser**:

* The code for **pycparser**'s AST nodes is automatically generated from a configuration file - ``_c_ast.cfg``, by ``_ast_gen.py``. If you modify the AST configuration, make sure to re-generate the code.
* Make sure you understand the optimized mode of **pycparser** - for that you must read the docstring in the constructor of the ``CParser`` class. For development you should create the parser without optimizations, so that it will regenerate the Yacc and Lex tables when you change the grammar.


Package contents
================

Once you unzip the ``pycparser`` package, you'll see the following files and directories:

README.rst:
  This README file.

setup.py:
  Installation script

examples/:
  A directory with some examples of using **pycparser**

pycparser/:
  The **pycparser** module source code.

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

Some people have contributed to **pycparser** by opening issues on bugs they've
found and/or submitting patches. The list of contributors is in the CONTRIBUTORS
file in the source distribution.

CI Status
=========

**pycparser** has automatic testing enabled through the convenient
`Travis CI project <https://travis-ci.org>`_. Here is the latest build status:

.. image:: https://travis-ci.org/eliben/pycparser.png?branch=master
  :align: center
  :target: https://travis-ci.org/eliben/pycparser

