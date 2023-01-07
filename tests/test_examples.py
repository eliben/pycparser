import os
import sys
import time
import unittest

sys.path.insert(0, '.')
from tests.test_util import run_exe, cpp_supported

# Runs all pycparser examples with no command-line arguments and makes sure they
# run successfully (return code = 0), without actually verifying their output.
class TestExamplesSucceed(unittest.TestCase):
    @unittest.skipUnless(cpp_supported(), 'cpp only works on Unix')
    def test_all_examples(self):
        root = './examples'
        for filename in os.listdir(root):
            if os.path.splitext(filename)[1] == '.py':
                with self.subTest(name=filename):
                    path = os.path.join(root, filename)
                    rc, stdout, stderr = run_exe(path)
                    self.assertEqual(
                        rc, 0, f'example "{filename}" failed with stdout =\n{stdout}\nstderr =\n{stderr}')

if __name__ == '__main__':
    unittest.main()
