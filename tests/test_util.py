#------------------------------------------------------------------------------
# pycparser: test_util.py
#
# Utility code for tests.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# This file contributed by vit9696@users.noreply.github.com
# License: BSD
#------------------------------------------------------------------------------
import platform


def cpp_supported():
    """Is cpp (the C preprocessor) supported as a native command?"""
    return platform.system() == 'Linux' or platform.system() == 'Darwin'


def cpp_path():
    """Path to cpp command."""
    if platform.system() == 'Darwin':
        return 'gcc'
    return 'cpp'


def cpp_args(args=[]):
    """Turn args into a suitable format for passing to cpp."""
    if isinstance(args, str):
        args = [args]
    if platform.system() == 'Darwin':
        return ['-E'] + args
    return args
