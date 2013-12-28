import os, sys
from distutils.core import setup


setup(
    # metadata
    name='pycparser',
    description='C parser in Python',
    long_description="""
        pycparser is a complete parser of the C language, written in
        pure Python using the PLY parsing library.
        It parses C code into an AST and can serve as a front-end for
        C compilers or analysis tools.
    """,
    license='BSD',
    version='2.10',
    author='Eli Bendersky',
    maintainer='Eli Bendersky',
    author_email='eliben@gmail.com',
    url='https://github.com/eliben/pycparser',
    platforms='Cross Platform',
    classifiers = [
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',],
    packages=['pycparser', 'pycparser.ply'],
    package_data={'pycparser': ['*.cfg']},
)


