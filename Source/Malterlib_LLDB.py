# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb

def fg_ImportModule(_Debugger, _Module):
	ModuleName = __name__ + '_LLDBLib.' + _Module
	exec ('from %s import *' % (ModuleName)) in globals()
	FunctionName = 'fg_MibLLDBInit_' + _Module
	globals()[FunctionName](_Debugger)

def __lldb_init_module(_Debugger,dict):

	#try:
		Module = __import__(__name__ + '_LLDBLib')
		
		fg_ImportModule(_Debugger, 'Common')
		fg_SetModuleName(__name__)
		
		fg_ImportModule(_Debugger, 'StringHelpers')
		fg_ImportModule(_Debugger, 'String')
		fg_ImportModule(_Debugger, 'AOCC')
		fg_ImportModule(_Debugger, 'AVLTree')
		fg_ImportModule(_Debugger, 'Aggregate')
		fg_ImportModule(_Debugger, 'Atomic')
		fg_ImportModule(_Debugger, 'AutoClear')
		fg_ImportModule(_Debugger, 'Exception')
		fg_ImportModule(_Debugger, 'Float')
		fg_ImportModule(_Debugger, 'LinkedList')
		fg_ImportModule(_Debugger, 'Pointer')
		fg_ImportModule(_Debugger, 'Registry')
		fg_ImportModule(_Debugger, 'StackTrace')
		fg_ImportModule(_Debugger, 'ThreadLocal')
		fg_ImportModule(_Debugger, 'Time')
		fg_ImportModule(_Debugger, 'Variant')
		fg_ImportModule(_Debugger, 'Json')
		fg_ImportModule(_Debugger, 'Vector')
		fg_ImportModule(_Debugger, 'Iterator')
		fg_ImportModule(_Debugger, 'Function')

		
		# Enable
		_Debugger.HandleCommand("type category enable MibLLDB")
		_Debugger.HandleCommand("type category enable MibLLDB_1") # This category is for higher prio

		# TODO:
		# TCActor
		# TCAsyncResult

	#except Exception as error:
	#	print 'Error initializing Malterlib lldb script: ', error

