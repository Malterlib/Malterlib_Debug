# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_BoundStrLen(_StrLen):
	if _StrLen > 4096:
		return 4096
	return _StrLen

def fg_FindStringTraitsType(_Type, _Depth = 0):
	if _Type is None or not _Type.IsValid() or _Depth >= 8:
		return None

	Type = fg_GetValidCanonicalType(_Type).GetUnqualifiedType()
	TypeName = Type.GetName()
	if TypeName is None:
		return None

	if TypeName.startswith("NMib::NStr::TCStrTraits<") and Type.GetNumberOfTemplateArguments() >= 2:
		return Type

	if TypeName.startswith("NMib::NStr::TCTCStrTraits<"):
		StrTraits = fg_GetValidTemplateArgumentType(Type, 0)
		StrTraits = fg_FindStringTraitsType(StrTraits, _Depth + 1)
		if StrTraits is not None:
			return StrTraits

	for iBase in range(Type.GetNumberOfDirectBaseClasses()):
		BaseTraits = fg_FindStringTraitsType(Type.GetDirectBaseClassAtIndex(iBase).GetType(), _Depth + 1)
		if BaseTraits is not None:
			return BaseTraits

	return None

def fg_GetStringType(_Value, _Default = 2):
	Type = _Value.GetType()
	if Type.IsPointerType():
		Type = _Value.Dereference().GetType()
	StrType = fg_GetInheritedType(fg_GetValidCanonicalType(Type), "NMib::NStr::TCStr")
	if StrType is None:
		return _Default

	CTStrTraits = fg_GetValidTemplateArgumentType(StrType, 0)
	if CTStrTraits is None:
		return _Default

	StrTraits = fg_FindStringTraitsType(CTStrTraits)
	if StrTraits is None or StrTraits.GetNumberOfTemplateArguments() < 2:
		return _Default

	Target = _Value.GetTarget()
	if Target is None:
		return _Default

	TypeValue = StrTraits.GetTemplateArgumentValue(Target, 1)
	if fg_IsValidSBValue(TypeValue) and TypeValue.GetValue() is not None:
		return int(TypeValue.GetValueAsUnsigned())

	return _Default

def fg_GetAddressMask(_Value):
	Process = _Value.GetProcess()
	return (1 << (Process.GetAddressByteSize() * 8)) - 1

def fg_IsInvalidStringAddress(_Value, _Address):
	if type(_Address) is not int:
		return True
	Mask = fg_GetAddressMask(_Value)
	return _Address < 0 or _Address > Mask or _Address == Mask

def fg_AddStringAddress(_Value, _Address, _Offset):
	if fg_IsInvalidStringAddress(_Value, _Address):
		return None
	Address = _Address + _Offset
	if fg_IsInvalidStringAddress(_Value, Address):
		return None
	return Address

def fg_InvalidStringSummary(_Value, _ValueType, _Address = None):
	if fg_RawSummary():
		return ""

	Value = '<invalid string data>'
	if type(_Address) is int:
		Value += ' ' + hex(_Address)
	if _ValueType.IsPointerType():
		return hex(_Value.GetValueAsUnsigned()) + "   " + Value
	return Value

def fg_CreateStringDataPointer(_Value, _Address, _Type):
	if fg_IsInvalidStringAddress(_Value, _Address):
		return None

	try:
		Value = _Value.CreateValueFromAddress("[TempData]", _Address, _Type.GetBasicType(lldb.eBasicTypeChar).GetPointerType()).AddressOf()
		if fg_IsValidSBValue(Value):
			return Value
	except Exception:
		pass

	return None

def fg_GetDynamicStringDisplayLen(_Value, _Data):
	Len = fg_GetValueAsUnsigned(_Data.GetChildMemberWithName('m_Len'))
	StrLen = fg_GetValueAsUnsigned(_Data.GetChildMemberWithName('m_StrLen'))
	if type(Len) is not int or type(StrLen) is not int or Len == 0:
		return None

	InvalidStrLen = (1 << (_Value.GetProcess().GetAddressByteSize() * 8 - 2)) - 1
	if StrLen == InvalidStrLen:
		return fg_BoundStrLen(Len - 1)
	if StrLen >= Len:
		return None
	return fg_BoundStrLen(StrLen)

def fg_SummaryProvider_Str_Dynamic_ch8(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		pData = _Value.GetChildMemberWithName('m_pData')

		DataAddress = pData.GetValueAsUnsigned()
		if DataAddress == 0:
			if fg_RawSummary():
				return ""
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + '   "" nullptr 8'
			return '"" nullptr 8'
		if fg_IsInvalidStringAddress(_Value, DataAddress):
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		Data = pData.Dereference()
		if not fg_IsValidSBValue(Data):
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		Type = fg_GetStringType(_Value)
		StrLen = fg_GetDynamicStringDisplayLen(_Value, Data)
		if StrLen is None:
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		DataType = Data.GetType()
		pStrData = fg_CreateStringDataPointer(pData, fg_AddStringAddress(_Value, DataAddress, DataType.GetByteSize()), DataType)
		if pStrData is None:
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		if fg_RawSummary():
			return fg_MakeStringFromData_ch8_Raw(pStrData.GetPointeeData(0, StrLen + 1), StrLen, Type)
		else:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch8(pStrData.GetPointeeData(0, StrLen + 1), StrLen, Type)
			else:
				return fg_MakeStringFromData_ch8(pStrData.GetPointeeData(0, StrLen + 1), StrLen, Type)

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Dynamic_ch8) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Dynamic_ch16(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		pData = _Value.GetChildMemberWithName('m_pData')

		DataAddress = pData.GetValueAsUnsigned()
		if DataAddress == 0:
			if fg_RawSummary():
				return ""
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + '   "" nullptr 16'
			return '"" nullptr 16'
		if fg_IsInvalidStringAddress(_Value, DataAddress):
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		Data = pData.Dereference()
		if not fg_IsValidSBValue(Data):
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		Type = fg_GetStringType(_Value)
		StrLen = fg_GetDynamicStringDisplayLen(_Value, Data)
		if StrLen is None:
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		DataType = Data.GetType()
		pStrData = fg_CreateStringDataPointer(pData, fg_AddStringAddress(_Value, DataAddress, DataType.GetByteSize()), DataType)
		if pStrData is None:
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		if fg_RawSummary():
			return fg_MakeStringFromData_ch16_Raw(pStrData.GetPointeeData(0, (StrLen + 1)*2), StrLen, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch16(pStrData.GetPointeeData(0, (StrLen + 1)*2), StrLen, Type)
		return fg_MakeStringFromData_ch16(pStrData.GetPointeeData(0, (StrLen + 1)*2), StrLen, Type)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Dynamic_ch16) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Dynamic_ch32(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		pData = _Value.GetChildMemberWithName('m_pData')

		DataAddress = pData.GetValueAsUnsigned()
		if DataAddress == 0:
			if fg_RawSummary():
				return ""
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + '   "" nullptr 32'
			return '"" nullptr 32'
		if fg_IsInvalidStringAddress(_Value, DataAddress):
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		Data = pData.Dereference()
		if not fg_IsValidSBValue(Data):
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		Type = fg_GetStringType(_Value)
		StrLen = fg_GetDynamicStringDisplayLen(_Value, Data)
		if StrLen is None:
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		DataType = Data.GetType()
		pStrData = fg_CreateStringDataPointer(pData, fg_AddStringAddress(_Value, DataAddress, DataType.GetByteSize()), DataType)
		if pStrData is None:
			return fg_InvalidStringSummary(_Value, ValueType, DataAddress)

		if fg_RawSummary():
			return fg_MakeStringFromData_ch32_Raw(pStrData.GetPointeeData(0, (StrLen + 1) * 4), StrLen, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch32(pStrData.GetPointeeData(0, (StrLen + 1) * 4), StrLen, Type)
		return fg_MakeStringFromData_ch32(pStrData.GetPointeeData(0, (StrLen + 1) * 4), StrLen, Type)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Dynamic_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return


def fg_SummaryProvider_Str_Fixed_ch8(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		Len = fg_BoundStrLen(_Value.GetChildMemberWithName('m_Len').GetValueAsUnsigned())
		Type = fg_GetStringType(_Value)
		lData = _Value.GetChildMemberWithName('m_lData')
		if fg_RawSummary():
			return fg_MakeStringFromData_ch8_Raw(lData.GetData(), Len, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch8(lData.GetData(), Len, Type)
		return fg_MakeStringFromData_ch8(lData.GetData(), Len, Type)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Fixed_ch8) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Fixed_ch16(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Len = fg_BoundStrLen(_Value.GetChildMemberWithName('m_Len').GetValueAsUnsigned())
		Type = fg_GetStringType(_Value)
		lData = _Value.GetChildMemberWithName('m_lData')
		if fg_RawSummary():
			return fg_MakeStringFromData_ch16_Raw(lData.GetData(), Len, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch16(lData.GetData(), Len, Type)
		return fg_MakeStringFromData_ch16(lData.GetData(), Len, Type)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Fixed_ch16) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Fixed_ch32(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Len = fg_BoundStrLen(_Value.GetChildMemberWithName('m_Len').GetValueAsUnsigned())
		Type = fg_GetStringType(_Value, 1)
		lData = _Value.GetChildMemberWithName('m_lData')
		if fg_RawSummary():
			return fg_MakeStringFromData_ch32_Raw(lData.GetData(), Len, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch32(lData.GetData(), Len, Type)
		return fg_MakeStringFromData_ch32(lData.GetData(), Len, Type)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Fixed_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Ptr_ch8(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		Len = fg_BoundStrLen(_Value.GetChildMemberWithName('m_Len').GetValueAsUnsigned())
		Type = fg_GetStringType(_Value)
		lData = _Value.GetChildMemberWithName('m_pData')
		Error = lldb.SBError()
		if lData.GetValueAsUnsigned() == 0:
			if fg_RawSummary():
				return ""
			Value = '""'
		else:
			if fg_RawSummary():
				return fg_MakeStringFromData_ch8_Raw(lData.GetPointeeData(0, Len + 1), Len, Type)
			Value = fg_MakeStringFromData_ch8(lData.GetPointeeData(0, Len + 1), Len, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Ptr_ch8) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Ptr_ch16(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Len = fg_BoundStrLen(_Value.GetChildMemberWithName('m_Len').GetValueAsUnsigned())
		Type = fg_GetStringType(_Value)
		lData = _Value.GetChildMemberWithName('m_pData')
		Error = lldb.SBError()
		if lData.GetValueAsUnsigned() == 0:
			if fg_RawSummary():
				return ""
			Value = '""'
		else:
			if fg_RawSummary():
				return fg_MakeStringFromData_ch16_Raw(lData.GetPointeeData(0, (Len + 1)*2), Len, Type)
			Value = fg_MakeStringFromData_ch16(lData.GetPointeeData(0, (Len + 1)*2), Len, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Ptr_ch16) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Ptr_ch32(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Len = fg_BoundStrLen(_Value.GetChildMemberWithName('m_Len').GetValueAsUnsigned())
		Type = fg_GetStringType(_Value, 1)
		lData = _Value.GetChildMemberWithName('m_pData')
		if lData.GetValueAsUnsigned() == 0:
			if fg_RawSummary():
				return ""
			Value = '""'
		else:
			if fg_RawSummary():
				return fg_MakeStringFromData_ch32_Raw(lData.GetPointeeData(0, (Len + 1)*4), Len, Type)
			Value = fg_MakeStringFromData_ch32(lData.GetPointeeData(0, (Len + 1)*4), Len, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Ptr_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Array_ch8(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Address = None
		if ValueType.IsPointerType():
			Address = fg_GetValueAsUnsigned(_Value)
			if Address == 0:
				if fg_RawSummary():
					return ""
				return "nullptr"

		Len = _Value.GetNumChildren()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch8_Raw(fg_GetData(_Value), Len, 2)
		Value = '"' + fg_MakeStringFromData_ch8_Raw(fg_GetData(_Value), Len, 2) + '"'

		return Value
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Array_ch8) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Array_ch16(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Address = None
		if ValueType.IsPointerType():
			Address = fg_GetValueAsUnsigned(_Value)
			if Address == 0:
				if fg_RawSummary():
					return ""
				return "nullptr"
		Len = _Value.GetNumChildren()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch16_Raw(fg_GetData(_Value), Len, 2)
		Value = '"' + fg_MakeStringFromData_ch16_Raw(fg_GetData(_Value), Len, 2) + '"'

		return Value
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Array_ch16) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Array_ch32(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Address = None
		if ValueType.IsPointerType():
			Address = fg_GetValueAsUnsigned(_Value)
			if Address == 0:
				if fg_RawSummary():
					return ""
				return "nullptr"
		Len = _Value.GetNumChildren()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch32_Raw(fg_GetData(_Value), Len, 2)

		Value = '"' + fg_MakeStringFromData_ch32_Raw(fg_GetData(_Value), Len, 2) + '"'

		return Value
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_Array_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_ArrayPtr_ch8(_Value, dict, _Options, _Len = None, _Offset = 0):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned());
		if _Len is not None:
			Len = int(_Len)
		else:
			Len = 2048
		Address = fg_GetPointerAddress(_Value)
		if Address == 0:
			if fg_RawSummary():
				return ""
			return 'nullptr'
		if fg_IsInvalidStringAddress(_Value, Address):
			return fg_InvalidStringSummary(_Value, Type, Address)
		pStrData = fg_CreateStringDataPointer(_Value, Address, _Value.GetType())
		if pStrData is None:
			return fg_InvalidStringSummary(_Value, Type, Address)
		if fg_RawSummary():
			return fg_MakeStringFromData_ch8_Raw(pStrData.GetPointeeData(0, (Len + 1)*1), Len, 2)
		return hex(Address) + '   "' + fg_MakeStringFromData_ch8_Raw(pStrData.GetPointeeData(_Offset, (Len + 1)*1), Len, 2) + '"'
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_ArrayPtr_ch8) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_ArrayPtr_ch16(_Value, dict, _Options, _Len = None, _Offset = 0):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned());
		if _Len is not None:
			Len = int(_Len)
		else:
			Len = 2048
		Address = fg_GetPointerAddress(_Value)
		if Address == 0:
			if fg_RawSummary():
				return ""
			return 'nullptr'
		if fg_IsInvalidStringAddress(_Value, Address):
			return fg_InvalidStringSummary(_Value, Type, Address)
		pStrData = fg_CreateStringDataPointer(_Value, Address, _Value.GetType())
		if pStrData is None:
			return fg_InvalidStringSummary(_Value, Type, Address)
		if fg_RawSummary():
			return fg_MakeStringFromData_ch16_Raw(pStrData.GetPointeeData(0, (Len + 1)*2), Len, 2)
		return hex(Address) + '   "' + fg_MakeStringFromData_ch16_Raw(pStrData.GetPointeeData(_Offset, (Len + 1)*2), Len, 2) + '"'
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_ArrayPtr_ch16) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_ArrayPtr_ch32(_Value, dict, _Options, _Len = None, _Offset = 0):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned());
		if _Len is not None:
			Len = int(_Len)
		else:
			Len = 2048
		Address = fg_GetPointerAddress(_Value)
		if Address == 0:
			if fg_RawSummary():
				return ""
			return 'nullptr'
		if fg_IsInvalidStringAddress(_Value, Address):
			return fg_InvalidStringSummary(_Value, Type, Address)
		pStrData = fg_CreateStringDataPointer(_Value, Address, _Value.GetType())
		if pStrData is None:
			return fg_InvalidStringSummary(_Value, Type, Address)
		if fg_RawSummary():
			return fg_MakeStringFromData_ch32_Raw(pStrData.GetPointeeData(0, (Len + 1)*4), Len, 2)
		return hex(Address) + '   "' + fg_MakeStringFromData_ch32_Raw(pStrData.GetPointeeData(_Offset, (Len + 1)*4), Len, 2) + '"'
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Str_ArrayPtr_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Char_ch8(_Value, dict):
	try:
		if _Value.GetType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Ret = ''
		Value = _Value.GetValueAsUnsigned()
		if Value == 0:
			Ret += "\\0";
		if Value < 32:
			Ret += "\\" + hex(Value)
		else:
			Ret += unichr(Value);
		return "'" + Ret + "'   " + str(Value)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Char_ch8) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Char_ch16(_Value, dict):
	try:
		if _Value.GetType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Ret = ''
		Value = _Value.GetValueAsUnsigned()
		Ret += unichr(Value);
		return "'" + Ret + "' = " + str(Value)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Char_ch16) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Char_ch32(_Value, dict):
	try:
		if _Value.GetType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Ret = ''
		Value = _Value.GetValueAsUnsigned()
		Ret += unichr(Value);
		return "'" + Ret + "' = " + str(Value)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Char_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_AddRawStringArrayReferenceSummary(_Debugger, _Provider, _Type):
	fg_AddSummary(_Debugger, _Provider, "(^|^const |^volatile |^const volatile )" + _Type + "( const| volatile| const volatile)? \\(&\\)\\[[0-9]+\\]$", True)

def fg_AddRawStringArrayPointerSummary(_Debugger, _Provider, _Type):
	fg_AddSummary(_Debugger, _Provider, "(^|^const |^volatile |^const volatile )" + _Type + "( const| volatile| const volatile)? \\(\\*( const| volatile| const volatile)?\\)\\[[0-9]+\\]$", True)

def fg_MibLLDBInit_String(_Debugger):

	#
	# String Formatters
	#

	# Array

	#fg_AddSummary(_Debugger, fg_SummaryProvider_Char_ch8 "char")
	#fg_AddSummary(_Debugger, fg_SummaryProvider_Char_ch8 "unsigned char")
	#fg_AddSummary(_Debugger, fg_SummaryProvider_Char_ch8 "signed char")
	#fg_AddSummary(_Debugger, fg_SummaryProvider_Char_ch8 "ch8")

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "ch8 *");
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "ch8 *const");
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "const ch8 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "const ch8 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "ch8 \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "ch8 const\\[[0-9]+]", True)
	fg_AddRawStringArrayReferenceSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "ch8")
	fg_AddRawStringArrayPointerSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "ch8")

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "char *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "char *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "const char *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "const char *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "char \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "char const\\[[0-9]+]", True)
	fg_AddRawStringArrayReferenceSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "char")
	fg_AddRawStringArrayPointerSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "char")

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "ch16 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "ch16 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const ch16 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const ch16 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "ch16 \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "ch16 const\\[[0-9]+]", True)
	fg_AddRawStringArrayReferenceSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "ch16")
	fg_AddRawStringArrayPointerSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "ch16")

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "char16_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "char16_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const char16_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const char16_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "char16_t \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "char16_t const\\[[0-9]+]", True)
	fg_AddRawStringArrayReferenceSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "char16_t")
	fg_AddRawStringArrayPointerSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "char16_t")

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "wchar_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "wchar_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const wchar_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const wchar_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "wchar_t \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "wchar_t const\\[[0-9]+]", True)
	fg_AddRawStringArrayReferenceSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "wchar_t")
	fg_AddRawStringArrayPointerSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "wchar_t")

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "ch32 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "ch32 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const ch32 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const ch32 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "ch32 \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "ch32 const\\[[0-9]+]", True)
	fg_AddRawStringArrayReferenceSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "ch32")
	fg_AddRawStringArrayPointerSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "ch32")

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "char32_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "char32_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const char32_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const char32_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "char32_t \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "char32_t const\\[[0-9]+]", True)
	fg_AddRawStringArrayReferenceSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "char32_t")
	fg_AddRawStringArrayPointerSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "char32_t")

	# Ptr
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraitsPtr_CStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>[[:space:]]*>[[:space:]]*>[[:space:]]*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraitsPtr_CWStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<(char16_t|wchar_t), [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<(char16_t|wchar_t), [0-9]*, (NMib::NStr::)CDefaultStrParams>[[:space:]]*>[[:space:]]*>[[:space:]]*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraitsPtr_CUStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>[[:space:]]*>[[:space:]]*>[[:space:]]*>$", True)


	# Dynamic
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraits_CStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>[[:space:]]*>[[:space:]]*>[[:space:]]*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraits_CWStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<(char16_t|wchar_t), [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<(char16_t|wchar_t), [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>[[:space:]]*>[[:space:]]*>[[:space:]]*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraits_CUStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>[[:space:]]*>[[:space:]]*>[[:space:]]*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )NMib::NStr::CMStrDeprecated$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )NMib::NStr::CMStrPreserve$", True)

	# Fixed
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*>[[:space:]]*>[[:space:]]*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<(char16_t|wchar_t), [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<(char16_t|wchar_t), [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*>[[:space:]]*>[[:space:]]*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*>[[:space:]]*>[[:space:]]*>$", True)

	return
