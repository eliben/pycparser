#!/usr/bin/env python3
import os, sys, subprocess, json, ctypes
assert os.path.isdir('./pycparser')
sys.path.insert(0, './pycparser')
import pycparser
from pycparser import c_generator

def parse(hc):
	ast = pycparser.parse_file( hc )
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

class holywrapper(object):
	def __init__(self, f, meta):
		self.func = f
		self.name = meta['name']
		cargs = []
		for arg in meta['args']:
			if arg.startswith('U8'):
				if '*' in arg:
					cargs.append(ctypes.c_char_p)
				else:
					cargs.append(ctypes.c_char)
			elif arg.startswith('F64'):
				cargs.append(ctypes.c_double)
			elif arg.startswith('U'):
				cargs.append(ctypes.c_uint)
			else:
				cargs.append(ctypes.c_int)
		if cargs:
			f.argtypes = tuple(cargs)

		if meta['returns'] == 'I32':
			f.restype = ctypes.c_int
		elif meta['returns'] == 'F64':
			f.restype = ctypes.c_double

	def __call__(self, *args):
		cargs = []
		for a in args:
			if type(a) is str: a = a.encode('utf-8')
			cargs.append(a)
		return self.func(*cargs)

def holyjit( h, output='/tmp/holyjit.so', debug=False ):
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

	if debug:
		print('='*80)
		print('\n'.join(c))
		print('-'*80)
		print('\n'.join(py))
		print('_'*80)
		print(funcs)

	tmp = '/tmp/holyjit.c'
	open(tmp, 'wb').write('\n'.join(c).encode("utf-8"))
	cmd = ['gcc', '-fPIC', '-shared', '-o', output, tmp]
	print(cmd)
	subprocess.check_call(cmd)
	lib = ctypes.CDLL(output)
	print(lib)

	scope = {}
	errors = []
	for fn in funcs:
		try:
			f = getattr(lib, fn['name'])
		except AttributeError:
			errors.append(fn['name'])
		if debug: print(f)
		scope[fn['name']] = holywrapper(f, fn)

	if errors:
		os.system('nm -g %s' % output)
		print('WARN: missing functions', errors)
	else:
		exec('\n'.join(py), scope, scope)
	if debug: print(scope)
	return scope

def holyc_to_c(hc):
	tmp = '/tmp/hc2c.HC'
	if type(hc) is list:
		hc = '\n'.join(hc)
	open(tmp,'wb').write(hc.encode('utf-8'))
	ast = parse(tmp)
	gen = c_generator.CGenerator()
	c = gen.visit(ast)
	return c

def c_to_holyc(c, defines=None):
	tmp = '/tmp/c2hc.c'
	if type(c) is list:
		c = '\n'.join(c)
	open(tmp,'wb').write(c.encode('utf-8'))
	if '#ifdef' in c or defines:
		cmd = ['gcc', '-E']
		if defines:
			for d in defines:
				cmd.append('-D%s' % d)
		cmd.append(tmp)
		print(cmd)
		c = subprocess.check_output(cmd).decode('utf-8')
		open(tmp,'wb').write(c.encode('utf-8'))

	ast = parse(tmp)
	gen = c_generator.CGenerator( make_holy=True )
	hc = gen.visit(ast)
	return hc

TEST = '''
#ifdef FOO
void main(unsigned char c){printf("foo", c);}
#endif
'''

def main():
	hc = None
	c  = None
	out = None
	for arg in sys.argv:
		if arg.endswith( ('.HC', '.hc') ):
			hc = arg
		elif arg.endswith( ('.c', '.h') ):
			c = arg
		elif arg.startswith('--out='):
			out = arg.split('=')[-1]

	if hc:
		c = holyc_to_c(open(hc,'rb').read().decode('utf-8'))
		if out: open(out, 'wb').write(c.encode('utf-8'))
		else: print(c)
	elif c:
		hc = c_to_holyc(open(c,'rb').read().decode('utf-8'))
		if out: open(out, 'wb').write(hc.encode('utf-8'))
		else: print(hc)
	else:
		print('no input files given:')
		print('arguments: [FILE.c] | [FILE.hc] --out=OUTPUT.c|hc')


if __name__=='__main__':
	if '--test-c' in sys.argv:
		hc = c_to_holyc(TEST, defines=['FOO'])
		print(hc)
		print('✝'*80)
		c = holyc_to_c(hc)
		print(c)
	elif '--test-holyc' in sys.argv:
		test = None
		for arg in sys.argv:
			if arg.endswith( ('.HC', '.hc') ):
				test = arg

		if not test:
			test = '/tmp/hw.HC'
			open(test,'wb').write(HW.encode('utf-8'))

		ast = parse(test)
		gen = c_generator.CGenerator()
		c = gen.visit(ast)
		holyjit(c)
	else:
		main()
