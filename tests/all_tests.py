#!/usr/bin/env python

import unittest


suite = unittest.TestLoader().loadTestsFromNames(
    [
        'test_c_lexer',
        'test_c_ast',
        'test_general',
        'test_c_parser',
    ]
)
    
unittest.TextTestRunner(verbosity=1).run(suite)
