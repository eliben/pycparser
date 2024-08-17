#!/usr/bin/env python3
import os, sys
assert os.path.isdir('./pycparser')
sys.path.insert(0, './pycparser')
import pycparser
from pycparser import c_generator

def parse(hc):
	print('parsing:', hc)
	ast = pycparser.parse_file( hc )
	print(ast)
	return ast

HW = r'''
U0 Hello(){
    "Hello World\n";
}
Hello;
Hello();
I32 add(I32 x="foooo", I32 y){
    return x+y;
}
I32 X;
X = add(8);
'''


if __name__=='__main__':
	test = None
	for arg in sys.argv:
		if arg.endswith( ('.HC', '.hc') ):
			test = arg

	if not test:
		test = '/tmp/hw.HC'
		open(test,'wb').write(HW.encode('utf-8'))

	ast = parse(test)
	gen = c_generator.CGenerator()
	print(gen)
	c = gen.visit(ast)
	print(c)
