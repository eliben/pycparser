#!/usr/bin/env python3
import os, sys, subprocess, json, ctypes
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

def holyjit( h ):
	py = []
	c  = [HOLYCTYPES]
	js = []
	funcs = []
	for ln in h.splitlines():
		if ln.startswith('//JIT//'):
			py.append(ln[len('//JIT//'):])
		elif ln.startswith('//JSON//'):
			f = json.loads(ln[len('//JSON//'):])
			funcs.append(f)
		else:
			c.append(ln)

	print('='*80)
	print('\n'.join(c))
	print('-'*80)
	print('\n'.join(py))
	print('_'*80)
	print(funcs)

	tmp = '/tmp/holyjit.c'
	open(tmp, 'wb').write('\n'.join(c).encode("utf-8"))
	cmd = ['gcc', '-fPIC', '-shared', '-o', '/tmp/holyjit.so', tmp]
	print(cmd)
	subprocess.check_call(cmd)
	lib = ctypes.CDLL('/tmp/holyjit.so')
	print(lib)

	scope = {}

	for fn in funcs:
		f = getattr(lib, fn['name'])
		print(f)
		scope[fn['name']] = f

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
	holyjit(c)
	sys.exit()

	tmp = '/tmp/test.c'
	open(tmp,'wb').write( (HOLYCTYPES + c).encode('utf-8') )
	cmd = ['gcc', '-o', '/tmp/test.exe', tmp]
	print(cmd)
	subprocess.check_call(cmd)
