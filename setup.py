import os, sys
from distutils.core import setup

version25 = False
if sys.version_info[0] < 2 or (sys.version_info[0] == 2 and sys.version_info[1] < 6):
    print "Generating Python 2.5-compatible version"
    version25 = True
    import shutil
    source_path = r'pycparser'
    save_path = r'pycparser-2.5'
    if os.path.isdir(save_path):
        shutil.rmtree(save_path)
    shutil.copytree(source_path, save_path)
    for dir_path, dir_names, file_names in os.walk(save_path):
        for file_name in file_names:
          if not file_name.endswith('.py'):
              continue
          file_path = os.path.join(dir_path, file_name)
          new_file_path = file_path + '.revised'
          new_file = open(new_file_path, 'w')
          wrote_with_import = False
          for line in open(file_path):
              stripped_line = line.strip()
              if not wrote_with_import and not stripped_line.startswith('#'):
                  new_file.write('\nfrom __future__ import with_statement\n\n')
                  wrote_with_import = True
              elif stripped_line.startswith('except') and ' as ' in line:
                  new_file.write(line.replace(' as ', ', '))
              else:
                  new_file.write(line)
          new_file.close()
          os.remove(file_path)
          os.rename(new_file_path, file_path)

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
    version='2.09.1',
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
    package_dir={'pycparser' : 'pycparser-2.5' if version25 else 'pycparser'},
)

if version25:
    shutil.rmtree('pycparser-2.5')
    print "Removing Python 2.5-compatible version"

