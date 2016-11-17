"""
Created on 25.10.2016

Creates Python 2.7-style stubfiles from Python 3.5-style stubfiles.
Conversion process needs Python 3.5, but resulting files can be
distributed for use with Python 2.7.
Only works if no Python 3.5 specific code was used to construct
type variables and such.

So far the conversion is somewhat naive and a hand-crafted
Python 2.7. stub-file might be required for advanced use-cases.
Such a file should be stored like the usual stub-file, but
using the suffix 'pyi2'. If such a file exists, pytypes will take
it as override of the pyi-file when running on Python 2.7.

@author: Stefan Richthofer
"""

import sys, os, imp, inspect, numbers, typing
import typechecker as tpc
from typing import Any


silent = False
indent = '\t'
stub_open_mode = "U"
stub_descr = (".pyi", stub_open_mode, imp.PY_SOURCE)


def _print(line):
	if not silent:
		print(line)

def _typestring(_types):
	if _types[0] is Any:
		argstr = '...'
	else:
		argstr = ', '.join([tpc._type_str(tp) for tp in _types[0].__tuple_params__])
	retstr = tpc._type_str(_types[1])
	return '('+argstr+') -> '+retstr

def _typecomment(_types):
	return '# type: '+_typestring(_types)

def typecomment(func):
	return _typecomment(tpc.get_types(func))

def signature(func):
	argstr = ', '.join(tpc.getargspecs(func)[0])
	return 'def '+func.__name__+'('+argstr+'):'

def _write_func(func, lines, inc = 0, decorators = None):
	if not decorators is None:
		for dec in decorators:
			lines.append(inc*indent+'@'+dec)
	lines.append(inc*indent+signature(func))
	lines.append((inc+1)*indent+typecomment(func))
	lines.append((inc+1)*indent+'pass')

def signature_class(clss):
	base_names = [base.__name__ for base in clss.__bases__]
	return 'class '+clss.__name__+'('+', '.join(base_names)+'):'

def _write_class(clss, lines, inc = 0):
	_print("write class: "+str(clss))
	anyElement = False
	lines.append(signature_class(clss))
	mb = inspect.getmembers(clss, lambda t: inspect.isfunction(t) or \
			inspect.isclass(t) or inspect.ismethoddescriptor(t))
	# todo: Care for overload-decorator
	for elem in mb:
		if elem[0] in clss.__dict__:
			el = clss.__dict__[elem[0]]
			if inspect.isfunction(el):
				lines.append('')
				_write_func(el, lines, inc+1)
				anyElement = True
			elif inspect.isclass(el):
				lines.append('')
				_write_class(el, lines, inc+1)
				anyElement = True
			elif inspect.ismethoddescriptor(el) and type(el) is staticmethod:
				lines.append('')
				_write_func(el.__func__, lines, inc+1, ['staticmethod'])
				anyElement = True

	# classmethods are not obtained via inspect.getmembers.
	# We have to look into __dict__ for that.
	for key in clss.__dict__:
		attr = getattr(clss, key)
		if inspect.ismethod(attr):
			lines.append('')
			_write_func(attr, lines, inc+1, ['classmethod'])
			anyElement = True

	if not anyElement:
		lines.append((inc+1)*indent+'pass')

def convert(in_file, out_file = None):
	_print('in_file: '+in_file)
	assert(os.path.isfile(in_file))
	checksum = tpc._md5(in_file)
	if out_file is None:
		out_file = in_file+'2'
	_print('out_file: '+out_file)

	with open(in_file, stub_open_mode) as module_file:
		module_name = os.path.basename(in_file)
		stub_module = imp.load_module(
				module_name, module_file, in_file, stub_descr)

	funcs = [func[1] for func in inspect.getmembers(stub_module, inspect.isfunction)]
	cls = [cl[1] for cl in inspect.getmembers(stub_module, inspect.isclass)]

	directory = os.path.dirname(out_file)
	if not os.path.exists(directory):
		os.makedirs(directory)

	with open(out_file, 'w') as out_file_handle:
		lines = ["'''",
				'Python 2.7-compliant stubfile of ',
				in_file,
				'with MD5-Checksum: '+checksum,
				'This file was generated by pytypes. Do not edit directly.',
				"'''",
				'',
				'import typing',
				'from typing import Any, Tuple, List, Union, Generic, Optional, \\',
				2*indent+'TypeVar, Set, FrozenSet, Dict, Generator',
				'import numbers']
		for func in funcs:
			lines.append('')
			_write_func(func, lines)

		for cl in cls:
			if not (hasattr(numbers, cl.__name__) or hasattr(typing, cl.__name__)):
				lines.append('\n')
				_write_class(cl, lines)

		for i in range(len(lines)):
			_print(lines[i])
			lines[i] = lines[i]+'\n'
		lines.append('\n')
		out_file_handle.writelines(lines)

def err_no_in_file():
	print("Error: No in_file given! Use -h for help.")
	sys.exit(os.EX_USAGE)

def print_usage():
	print("stubfile_2_converter usage:")
	print("(python|python3) stubfile_2_converter.py [options/flags] [in_file]")
	print("Supported options/flags:")
	print("-o [out_file] : custom output-file")
	print("-s            : silent mode")
	print("-h            : usage")

if __name__ == '__main__':
	if '-h' in sys.argv:
		print_usage()
		sys.exit(0)
	in_file = sys.argv[-1]
	if len(sys.argv) < 2 or in_file.startswith('-'):
		err_no_in_file()
	out_file = None
	if '-s' in sys.argv:
		silent = True
	try:
		index_o = sys.argv.index('-o')
		if index_o == len(sys.argv)-2:
			err_no_in_file()
		out_file = sys.argv[index_o+1]
	except ValueError:
		pass
	convert(in_file, out_file)
