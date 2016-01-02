# Copyright © 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


def fg_SummaryProvider_fp32(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Current = _Value.CreateValueFromAddress("[TempData]", fg_GetValueAddress(_Value), _Value.GetType().GetBasicType(lldb.eBasicTypeFloat))
		Summary = Current.GetSummary()
		if Summary == None:
			Value = Current.GetValue()
			if Value != None:
				Summary = str(Value)
		
		if Summary != None:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Summary
			return Summary;
			
		return None
	except Exception as error:
		print '(fg_SummaryProvider_fp32) error: ', error, ' path: ', _Value.get_expr_path()
		return


def fg_SummaryProvider_fp64(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Current = _Value.CreateValueFromAddress("[TempData]", fg_GetValueAddress(_Value), _Value.GetType().GetBasicType(lldb.eBasicTypeDouble))
		
		Summary = Current.GetSummary()
		if Summary == None:
			Value = Current.GetValue()
			if Value != None:
				Summary = str(Value)
		if Summary != None:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Summary
			return Summary;

		return None
	except Exception as error:
		print '(fg_SummaryProvider_fp64) error: ', error, ' path: ', _Value.get_expr_path()
		return

#template <aint t_SignBits, aint t_ExponentBits, aint t_MantissaBits, typename t_CImplicitFloat = CNoImplicit, bint t_bDummyOptimize = true, typename t_CIntegerStorage = typename NTraits::TCIntFromSizeLarger<(t_SignBits + t_ExponentBits + t_MantissaBits + 7)/8>::CType>
def fg_SummaryProvider_TCFloat(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		ExpressionPath = "ms_pHelper->fs_GetAsDouble((void *)(size_t)" + hex(fg_GetValueAddress(_Value)) + ")";
		ValueType = fg_GetValueType(_Value)
		Current = fg_GetStaticFromSBValue(_Value, ExpressionPath, ValueType)
		if not fg_IsValidSBValue(Current):
			return None
		Summary = Current.GetSummary()
		if Summary == None:
			Value = Current.GetValue()
			if Value != None:
				Summary = str(Value)
		
		if Summary != None:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Summary
			return Summary;

		return None
	except Exception as error:
		print '(fg_SummaryProvider_TCFloat) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_MibLLDBInit_Float(_Debugger):
	
	fg_AddSummary(_Debugger, fg_SummaryProvider_fp32, "(^|^const )NMib::NMath::TCFloat<1, 8, 23, float, 1, int>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_fp64, "(^|^const )NMib::NMath::TCFloat<1, 11, 52, double, 1, long long>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCFloat, "(^|^const )NMib::NMath::TCFloat<.*>$", True)
	
	return