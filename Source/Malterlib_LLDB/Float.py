# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

#template <aint t_SignBits, aint t_ExponentBits, aint t_MantissaBits, aint t_PaddingBits, typename t_CImplicitFloat = CNoImplicit, bool t_bDummyOptimize = true, typename t_CIntegerStorage = NTraits::TCIntFromSizeLarger<(t_SignBits + t_ExponentBits + t_MantissaBits + 7)/8>>
def fg_SummaryProvider_TCFloat(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		ImplicitData = _Value.GetChildMemberWithName("m_DataStorage")
		ImplicitName = fg_GetValidCanonicalType(fg_GetValueType(ImplicitData)).GetName()

		if ImplicitName == "float" or ImplicitName == "double" or ImplicitName == "long double":
			Summary = ImplicitData.GetSummary()
			if Summary is None:
				Value = ImplicitData.GetValue()
				if Value is not None:
					Summary = str(Value)

			if Summary is not None:
				if ValueType.IsPointerType():
					return hex(_Value.GetValueAsUnsigned()) + "   " + Summary
				return Summary;
			return None

		Stream = lldb.SBStream()
		_Value.GetExpressionPath(Stream, True)

		ExpressionPath = Stream.GetData() + ".f_Debug_GetAsDouble()";

		Frame = _Value.GetProcess().GetSelectedThread().GetSelectedFrame()

		Current = Frame.EvaluateExpression(ExpressionPath)
		if not fg_IsValidSBValue(Current):
			ExpressionPath = "((" + ValueType.GetName() + " *)" + hex(fg_GetValueAddress(_Value)) + ")->f_Debug_GetAsDouble()";
			Current = Frame.EvaluateExpression(ExpressionPath)
			if not fg_IsValidSBValue(Current):
				return None

		Summary = Current.GetSummary()
		if Summary is None:
			Value = Current.GetValue()
			if Value is not None:
				Summary = str(Value)

		if Summary is not None:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Summary
			return Summary;

		return None
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCFloat) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_Float(_Debugger):

	fg_AddSummary(_Debugger, fg_SummaryProvider_TCFloat, "(^|^const )NMib::NNumeric::TCFloat<.*>$", True)

	return
