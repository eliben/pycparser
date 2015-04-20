#!/usr/bin/env python

import sys
sys.path[0:0] = ['.', '..']

import unittest


suite = unittest.TestLoader().loadTestsFromNames(
    [
        'test_c_lexer',
        'test_c_ast',
        'test_general',
        'test_c_parser',
        'test_c_generator',
    ]
)

testresult = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if testresult.wasSuccessful() else 1)
