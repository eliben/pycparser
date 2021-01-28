import os, sys
try:
    from setuptools import setup
    from setuptools.command.install import install as _install
    from setuptools.command.sdist import sdist as _sdist
except ImportError:
    from distutils.core import setup
    from distutils.command.install import install as _install
    from distutils.command.sdist import sdist as _sdist


def _run_build_tables(dir):
    from subprocess import check_call
    # This is run inside the install staging directory (that had no .pyc files)
    # We don't want to generate any.
    # https://github.com/eliben/pycparser/pull/135
    check_call([sys.executable, '-B', '_build_tables.py'],
               cwd=os.path.join(dir, 'pycparser'))


class install(_install):
    def run(self):
        _install.run(self)
        self.execute(_run_build_tables, (self.install_lib,),
                     msg="Build the lexing/parsing tables")


class sdist(_sdist):
    def make_release_tree(self, basedir, files):
        _sdist.make_release_tree(self, basedir, files)
        self.execute(_run_build_tables, (basedir,),
                     msg="Build the lexing/parsing tables")

if __name__ == "__main__":
    setup(
        cmdclass={'install': install, 'sdist': sdist},
    )
