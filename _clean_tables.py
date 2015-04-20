# Cleanup all tables and PYC files to ensure no PLY stuff is cached
from __future__ import print_function
import fnmatch
import os, shutil

file_patterns = ('yacctab.*', 'lextab.*', '*.pyc', '__pycache__')


def do_cleanup(root):
    for path, dirs, files in os.walk(root):
        for file in files:
            try:
                for pattern in file_patterns:
                    if fnmatch.fnmatch(file, pattern):
                        fullpath = os.path.join(path, file)
                        os.remove(fullpath)
                        print('Deleted', fullpath)
            except OSError:
                pass


if __name__ == "__main__":
    do_cleanup('.')
