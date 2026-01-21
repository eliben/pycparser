# -----------------------------------------------------------------
# Benchmarking utility for internal use.
#
# Use with Python 3.6+
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
# -----------------------------------------------------------------
import os
import statistics
import sys
import time

sys.path.extend([".", ".."])

from pycparser import c_parser, c_ast


def measure_parse(text, n, progress_cb):
    """Measure the parsing of text with pycparser.

    text should represent a full file. n is the number of iterations to measure.
    progress_cb will be called with the iteration number each time one is done.

    Returns a list of elapsed times, one per iteration.
    """
    times = []
    for i in range(n):
        parser = c_parser.CParser()
        t1 = time.time()
        ast = parser.parse(text, "")
        elapsed = time.time() - t1
        assert isinstance(ast, c_ast.FileAST)
        times.append(elapsed)
        progress_cb(i)
    return times


def measure_file(filename, n):
    def progress_cb(i):
        print(".", sep="", end="", flush=True)

    with open(filename) as f:
        print(f"{os.path.basename(filename):<25}", end="", flush=True)
        text = f.read()
        times = measure_parse(text, n, progress_cb)
    mean = statistics.mean(times)
    stdev = statistics.stdev(times)
    print(f"    Mean: {mean:.3f}  Stddev: {stdev:.3f}")


NUM_RUNS = 5


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dir with input files>")
        sys.exit(1)
    for filename in os.listdir(sys.argv[1]):
        filename = os.path.join(sys.argv[1], filename)
        measure_file(filename, NUM_RUNS)
