# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import decimal, lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_GetDisplayValue(_Value):
	if _Value.GetType().IsReferenceType():
		return _Value.Dereference()
	return _Value

def fg_GetIntegerFromData(_Value):
	Data = _Value.GetData()
	Bytes = list(Data.uint8)
	nBytes = int(_Value.GetType().GetByteSize())
	if nBytes <= 0 or len(Bytes) < nBytes:
		Value = _Value.GetValueAsUnsigned()
		if type(Value) is int:
			return Value
		return None

	Bytes = Bytes[:nBytes]
	Process = _Value.GetProcess()
	if Process is not None and Process.GetByteOrder() == lldb.eByteOrderBig:
		Bytes = list(reversed(Bytes))

	Value = 0
	for iByte, Byte in enumerate(Bytes):
		Value |= int(Byte) << (iByte * 8)
	return Value

def fg_GetDecimalPrecision(_nMantissaBits):
	return max(32, (((_nMantissaBits + 1) * 30103 + 99999) // 100000) + 8)

def fg_FormatTCFloatNan(_Sign, _Mantissa, _nMantissaBits):
	Prefix = "-" if _Sign else ""
	if _nMantissaBits > 0 and (_Mantissa & (1 << (_nMantissaBits - 1))) != 0:
		return Prefix + "QNaN"
	return Prefix + "SNaN"

def fg_FormatTCFloatBinary(_Sign, _Mantissa, _BinaryExponent):
	Prefix = "-" if _Sign else ""
	return "{}{} * 2^{}".format(Prefix, _Mantissa, _BinaryExponent)

def fg_FormatTCFloatDecimal(_Sign, _Mantissa, _BinaryExponent, _nMantissaBits):
	if _Mantissa == 0:
		return "-0.0" if _Sign else "0.0"

	Precision = fg_GetDecimalPrecision(_nMantissaBits)
	if abs(_BinaryExponent) > 1000000:
		return fg_FormatTCFloatBinary(_Sign, _Mantissa, _BinaryExponent)

	try:
		with decimal.localcontext() as Context:
			Context.prec = Precision
			ExponentLimit = abs(_BinaryExponent) + Precision + len(str(_Mantissa)) + 16
			Context.Emax = min(decimal.MAX_EMAX, max(Context.Emax, ExponentLimit))
			Context.Emin = max(decimal.MIN_EMIN, min(Context.Emin, -ExponentLimit))

			Value = decimal.Decimal(_Mantissa)
			if _BinaryExponent >= 0:
				Value *= decimal.Decimal(2) ** _BinaryExponent
			else:
				Value /= decimal.Decimal(2) ** (-_BinaryExponent)
			if _Sign:
				Value = -Value
			return str(Value)
	except (decimal.DecimalException, OverflowError, ValueError):
		return fg_FormatTCFloatBinary(_Sign, _Mantissa, _BinaryExponent)

def fg_DecodeTCFloat(_Value, _ValueType, _ImplicitData):
	TemplateArguments = list(fg_ParseTemplate(_ValueType.GetName()))
	if len(TemplateArguments) < 4:
		TemplateArguments = list(fg_ParseTemplate(fg_GetValidCanonicalType(_ValueType).GetName()))
		if len(TemplateArguments) < 4:
			return None
	if not fg_IsInteger(TemplateArguments[0]) or not fg_IsInteger(TemplateArguments[1]) or not fg_IsInteger(TemplateArguments[2]) or not fg_IsInteger(TemplateArguments[3]):
		return None

	nSignBits = int(TemplateArguments[0])
	nExponentBits = int(TemplateArguments[1])
	nMantissaBits = int(TemplateArguments[2])
	nPaddingBits = int(TemplateArguments[3])
	if nSignBits < 0 or nSignBits > 1 or nExponentBits <= 0 or nMantissaBits < 0 or nPaddingBits < 0:
		return None

	Storage = fg_GetIntegerFromData(_ImplicitData)
	if Storage is None:
		return None

	nStorageBits = int(_ImplicitData.GetType().GetByteSize()) * 8
	nUnusedBits = nStorageBits - (nSignBits + nExponentBits + nMantissaBits + nPaddingBits)
	if nUnusedBits < 0:
		return None

	MantissaMask = (1 << nMantissaBits) - 1
	ExponentMask = (1 << nExponentBits) - 1
	Mantissa = Storage & MantissaMask
	Exponent = (Storage >> (nMantissaBits + nUnusedBits)) & ExponentMask
	Sign = 0
	if nSignBits != 0:
		Sign = (Storage >> (nMantissaBits + nUnusedBits + nExponentBits)) & 1
	Bias = (1 << (nExponentBits - 1)) - 1

	if Exponent == ExponentMask:
		if Mantissa == 0:
			return "-Inf" if Sign else "Inf"
		return fg_FormatTCFloatNan(Sign, Mantissa, nMantissaBits)

	if Exponent == 0:
		DecodedMantissa = Mantissa
		BinaryExponent = 1 - Bias - nMantissaBits
	else:
		DecodedMantissa = (1 << nMantissaBits) | Mantissa
		BinaryExponent = Exponent - Bias - nMantissaBits

	Summary = fg_FormatTCFloatDecimal(Sign, DecodedMantissa, BinaryExponent, nMantissaBits)
	if Exponent == 0 and Mantissa != 0:
		Summary += "#denorm"
	return Summary

#template <aint t_SignBits, aint t_ExponentBits, aint t_MantissaBits, aint t_PaddingBits, typename t_CImplicitFloat = CNoImplicit, bool t_bDummyOptimize = true, typename t_CIntegerStorage = NTraits::TCIntFromSizeLarger<(t_SignBits + t_ExponentBits + t_MantissaBits + 7)/8>>
def fg_SummaryProvider_TCFloat(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		ValueObject = fg_GetDisplayValue(_Value)
		ImplicitData = ValueObject.GetChildMemberWithName("m_DataStorage")
		if not fg_IsValidSBValue(ImplicitData):
			return None

		Summary = fg_DecodeTCFloat(_Value, ValueType, ImplicitData)

		if Summary is not None:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Summary
			return Summary;

		return None
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_TCFloat) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_Float(_Debugger):

	fg_AddSummary(_Debugger, fg_SummaryProvider_TCFloat, "(^|^const )NMib::NNumeric::TCFloat<.*>$", True)

	return
