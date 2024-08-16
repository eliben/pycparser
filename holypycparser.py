#!/usr/bin/env python3
import os, sys
assert os.path.isdir('./pycparser')
sys.path.insert(0, './pycparser')
import pycparser
print(pycparser)

def parse(hc):
	print('parsing:', hc)
	ast = pycparser.parse_file( hc )
	print(ast)

HW_JIT = r'''
U0 Hello(){
    "Hello World\n";
}
Hello;
'''

HW = r'''
U0 Hello(){
    "Hello World\n";
}
'''

if __name__=='__main__':
	test = None
	for arg in sys.argv:
		if arg.endswith( ('.HC', '.hc') ):
			test = arg

	if not test:
		test = '/tmp/hw.HC'
		open(test,'wb').write(HW.encode('utf-8'))

	parse(test)