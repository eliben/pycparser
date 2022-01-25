import os
import sys
import time
import unittest

sys.path.insert(0, '.')
from tests.test_util import run_exe, cpp_supported

EMIT_ELAPSED_TIME = False

# Runs all pycparser examples with no command-line arguments and makes sure they
# run successfully (return code = 0), without actually verifying their output.
class TestExamplesSucceed(unittest.TestCase):
    @unittest.skipUnless(cpp_supported(), 'cpp only works on Unix')
    def test_all_examples(self):
        root = './examples'
        for filename in os.listdir(root):
            if os.path.splitext(filename)[1] == '.py':
                # TODO: It would be nice to use subTest here, but that's not
                # available in Python 2.7
                # Use it when we finally drop Python 2...
                path = os.path.join(root, filename)
                t1 = time.time()
                rc, stdout, stderr = run_exe(path)
                elapsed = time.time() - t1
                if EMIT_ELAPSED_TIME:
                    print('{}... elapsed: {}'.format(filename, elapsed))
                self.assertEqual(
                    rc, 0, 'example "{}" failed with stdout =\n{}\nstderr =\n{}'.format(filename, stdout, stderr))


if __name__ == '__main__':
    EMIT_ELAPSED_TIME = True
    unittest.main()
