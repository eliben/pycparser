from __future__ import print_function
import sys
import time

sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file


if __name__ == '__main__':
  filename = sys.argv[1]
  t1 = time.time()
  ast = parse_file(filename)
  print('Elapsed: %.4f' % (time.time() - t1))
  assert ast is not None
