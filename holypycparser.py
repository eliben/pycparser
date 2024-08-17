#!/usr/bin/env python3
import os, sys, subprocess
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
I32 add(U8 *x="foooo", I32 y, I32 z){
    return y+z;
}
I32 X;
X = add(1,2);
X = add("bar", 3,4);
'''

HOLYCTYPES = '''
#define U0 void
#define U8 unsigned char
#define I32 int
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

	tmp = '/tmp/test.c'
	open(tmp,'wb').write( (HOLYCTYPES + c).encode('utf-8') )
	cmd = ['gcc', '-o', '/tmp/test.exe', tmp]
	print(cmd)
	subprocess.check_call(cmd)
