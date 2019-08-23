import os
import statistics
import sys
import time

sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast


def measure_parse(text, n, progress_cb):
    times = []
    for i in range(n):
        parser = c_parser.CParser()
        t1 = time.time()
        ast = parser.parse(text, '')
        elapsed = time.time() - t1
        assert isinstance(ast, c_ast.FileAST)
        times.append(elapsed)
        progress_cb(i)
    return times


def measure_file(filename, n):
    progress_cb = lambda i: print('.', sep='', end='', flush=True)
    with open(filename) as f:
        print('%-20s' % os.path.basename(filename), end='', flush=True)
        text = f.read()
        times = measure_parse(text, n, progress_cb)
    print('    Mean: %.3f  Stddev: %.3f' % (statistics.mean(times),
                                            statistics.stdev(times)))


if __name__ == '__main__':
    for i in range(1, len(sys.argv)):
        measure_file(sys.argv[i], 5)
