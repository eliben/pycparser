#!/usr/bin/env python3
import os, sys, subprocess, json, ctypes, code
import holypycparser
print(holypycparser)

scope = {}

HOLYC = None
def holyc_compile(hc):
	c = holypycparser.holyc_to_c(hc)
	jit = holypycparser.holyjit(c)
	for name in jit:
		f = jit[name]
		if isinstance(f, holypycparser.holywrapper):
			print('new holyc function:', name, f)
			scope[name] = f

TEST = '''
I32 add(I32 y, I32 z){
    return y+z;
}
'''

holyc_compile(TEST)
for arg in sys.argv:
	if arg.endswith(('.HC', '.hc')):
		holyc_compile(arg)

def pymode():
	global HOLYC
	sys.ps1 = 'python>>>'
	sys.ps2 = '... '
	HOLYC = None

com = {
	'holyc' : holyc_compile,
	'python': pymode,
	'exit': pymode,
}
console = code.InteractiveConsole(locals=scope)
__runsource = console.runsource
def run(co, filename=None, symbol=None):
	global HOLYC
	if type(HOLYC) is list:
		if co in ('python', 'exit'):
			print('-'*80)
			print('\n'.join(HOLYC))
			print('-'*80)
			pymode()
		else:
			HOLYC.append(co)
			#print(co)
		if co == '}':
			holyc_compile(HOLYC)
			HOLYC = None

	elif co in com:
		com[co]()
	elif co.endswith('{'):
		if HOLYC is None:
			HOLYC = [co]
	elif co in scope:
		print(scope[co])
	else:
		__runsource(co)
	return False

sys.ps1 = 'holysh>>>'
sys.ps2 = '... '

console.runsource = run
console.interact(banner="holysh: press Ctrl+D to exit")