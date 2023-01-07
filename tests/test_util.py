#------------------------------------------------------------------------------
# pycparser: test_util.py
#
# Utility code for tests.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# This file contributed by vit9696@users.noreply.github.com
# License: BSD
#------------------------------------------------------------------------------
import os
import platform
import subprocess
import sys


def cpp_supported():
    """Is cpp (the C preprocessor) supported as a native command?"""
    return platform.system() == 'Linux'


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

def _bytes2str(b):
    return b.decode('latin-1')

def run_exe(exe_path, args=[], echo=False):
    """ Runs the given executable as a subprocess, given the
        list of arguments. Captures its return code (rc) and stdout and
        returns a tuple: rc, stdout, stderr
    """
    popen_cmd = [exe_path] + args
    if os.path.splitext(exe_path)[1] == '.py':
        popen_cmd.insert(0, sys.executable)
    if echo:
      print('[cmd]', ' '.join(popen_cmd))
    proc = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    return proc.returncode, _bytes2str(stdout), _bytes2str(stderr)
