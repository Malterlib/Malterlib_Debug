# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb
from timeit import default_timer as timer
from importlib import reload, import_module

def fg_ImportModule(_Debugger, _Module):
	reload(import_module("." + _Module, __name__))
	FunctionName = 'fg_MibLLDBInit_' + _Module
	getattr(globals().get(_Module), FunctionName)(_Debugger)

def __lldb_init_module(_Debugger,dict):
	StartTime = timer()
	g_bHasInitialized = True

	_Debugger.HandleCommand('type summary clear MibLLDB')
	_Debugger.HandleCommand('type summary clear MibLLDB_1')

	_Debugger.HandleCommand('type synthetic clear MibLLDB')
	_Debugger.HandleCommand('type synthetic clear MibLLDB_1')

	fg_ImportModule(_Debugger, 'Common')
	fg_ImportModule(_Debugger, 'StringHelpers')
	fg_ImportModule(_Debugger, 'String')
	fg_ImportModule(_Debugger, 'AOCC')
	fg_ImportModule(_Debugger, 'AVLTree')
	fg_ImportModule(_Debugger, 'Aggregate')
	fg_ImportModule(_Debugger, 'Atomic')
	fg_ImportModule(_Debugger, 'AutoClear')
	fg_ImportModule(_Debugger, 'Exception')
	fg_ImportModule(_Debugger, 'Float')
	fg_ImportModule(_Debugger, 'Numeric')
	fg_ImportModule(_Debugger, 'LinkedList')
	fg_ImportModule(_Debugger, 'Pointer')
	fg_ImportModule(_Debugger, 'Registry')
	fg_ImportModule(_Debugger, 'StackTrace')
	fg_ImportModule(_Debugger, 'ThreadLocal')
	fg_ImportModule(_Debugger, 'Time')
	fg_ImportModule(_Debugger, 'Variant')
	fg_ImportModule(_Debugger, 'Json')
	fg_ImportModule(_Debugger, 'Vector')
	fg_ImportModule(_Debugger, 'Function')
	fg_ImportModule(_Debugger, 'Concurrency')

	# Enable
	_Debugger.HandleCommand("type category enable MibLLDB")
	_Debugger.HandleCommand("type category enable MibLLDB_1") # This category is for higher prio

	# TODO:
	# TCActor
	# TCAsyncResult

	EndTime = timer()

	print ("Initializing Malterlib lldb helpers took", EndTime - StartTime, "seconds")
