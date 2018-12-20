# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from Common import *
from StringHelpers import *



def fg_SummaryProvider_CTime(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Current = _Value.CreateValueFromExpression("[TempData]", "NMib::NTime::CTime::fsp_DebugStr((void*)(size_t)" + hex(fg_GetValueAddress(_Value)) + ")")
		Value = fg_MakeStringFromData_ch8_Raw(Current.GetPointeeData(0, 256), 256, 1)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print '(fg_SummaryProvider_CTime) error: ', error, ' path: ', _Value.get_expr_path()
		return


def fg_SummaryProvider_CTimeSpan(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Current = _Value.CreateValueFromExpression("[TempData]", "NMib::NTime::CTimeSpan::fsp_DebugStr((void*)(size_t)" + hex(fg_GetValueAddress(_Value)) + ")")
		Value = fg_MakeStringFromData_ch8_Raw(Current.GetPointeeData(0, 256), 256, 1)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print '(fg_SummaryProvider_CTimeSpan) error: ', error, ' path: ', _Value.get_expr_path()
		return


def fg_MibLLDBInit_Time(_Debugger):
	
	fg_AddSummary(_Debugger, fg_SummaryProvider_CTime, "(^|^const )NMib::NTime::CTime$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CTimeSpan, "(^|^const )NMib::NTime::CTimeSpan$", True)
	
	return
