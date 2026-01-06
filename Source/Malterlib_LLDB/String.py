# Copyright (C) 2015 Hansoft AB
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_BoundStrLen(_StrLen):
	if _StrLen > 4096:
		return 4096
	return _StrLen

def fg_GetStringType(_Value, _Default = 2):
	Type = _Value.GetType()
	if Type.IsPointerType():
		Type = _Value.Dereference().GetType()
	StrType = fg_GetInheritedType(fg_GetValidCanonicalType(Type), "NMib::NStr::TCStrAggregate")
	if StrType is None:
		return _Default
	MemberFunctionHelper = fg_GetMemberFunction(StrType, 'fs_TypeDebugHelper')
	if not MemberFunctionHelper:
		return _Default
	DataType = MemberFunctionHelper.GetReturnType()
	if DataType is None:
		return _Default
	return int(fg_GetValidCanonicalType(DataType).GetName().split('<')[1].split('>')[0])

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

		Data = pData.Dereference()

		Len = Data.GetChildMemberWithName('m_Len').GetValueAsUnsigned()
		Type = fg_GetStringType(_Value)
		StrLen = fg_BoundStrLen(Data.GetChildMemberWithName('m_StrLen').GetValueAsUnsigned())

		DataType = Data.GetType()
		pStrData = pData.CreateValueFromAddress("[TempData]", DataAddress + DataType.GetByteSize(), DataType.GetBasicType(lldb.eBasicTypeChar).GetPointerType()).AddressOf()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch8_Raw(pStrData.GetPointeeData(0, StrLen + 1), StrLen, Type)
		else:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch8(pStrData.GetPointeeData(0, StrLen + 1), StrLen, Type)
			else:
				return fg_MakeStringFromData_ch8(pStrData.GetPointeeData(0, StrLen + 1), StrLen, Type)

	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Dynamic_ch8) error: ', error, ' path: ', _Value.get_expr_path())
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

		Data = pData.Dereference()

		Len = Data.GetChildMemberWithName('m_Len').GetValueAsUnsigned()
		Type = fg_GetStringType(_Value)
		StrLen = fg_BoundStrLen(Data.GetChildMemberWithName('m_StrLen').GetValueAsUnsigned())

		DataType = Data.GetType()
		pStrData = pData.CreateValueFromAddress("[TempData]", DataAddress + DataType.GetByteSize(), DataType.GetBasicType(lldb.eBasicTypeChar).GetPointerType()).AddressOf()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch16_Raw(pStrData.GetPointeeData(0, (StrLen + 1)*2), StrLen, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch16(pStrData.GetPointeeData(0, (StrLen + 1)*2), StrLen, Type)
		return fg_MakeStringFromData_ch16(pStrData.GetPointeeData(0, (StrLen + 1)*2), StrLen, Type)
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Dynamic_ch16) error: ', error, ' path: ', _Value.get_expr_path())
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

		Data = pData.Dereference()

		Len = Data.GetChildMemberWithName('m_Len').GetValueAsUnsigned()
		Type = fg_GetStringType(_Value)
		StrLen = fg_BoundStrLen(Data.GetChildMemberWithName('m_StrLen').GetValueAsUnsigned())

		DataType = Data.GetType()
		pStrData = pData.CreateValueFromAddress("[TempData]", DataAddress + DataType.GetByteSize(), DataType.GetBasicType(lldb.eBasicTypeChar).GetPointerType()).AddressOf()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch32_Raw(pStrData.GetPointeeData(0, (StrLen + 1) * 4), StrLen, Type)
		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + fg_MakeStringFromData_ch32(pStrData.GetPointeeData(0, (StrLen + 1) * 4), StrLen, Type)
		return fg_MakeStringFromData_ch32(pStrData.GetPointeeData(0, (StrLen + 1) * 4), StrLen, Type)
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Dynamic_ch32) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Fixed_ch8) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Fixed_ch16) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Fixed_ch32) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Ptr_ch8) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Ptr_ch16) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Ptr_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Array_ch8(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		Len = _Value.GetNumChildren()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch8_Raw(fg_GetData(_Value), Len, 2)
		Value = '"' + fg_MakeStringFromData_ch8_Raw(fg_GetData(_Value), Len, 2) + '"'

		if ValueType.IsPointerType():
			Value = Value + "   " + hex(_Value.GetValueAsUnsigned());

		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Array_ch8) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Array_ch16(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Len = _Value.GetNumChildren()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch16_Raw(fg_GetData(_Value), Len, 2)
		Value = '"' + fg_MakeStringFromData_ch16_Raw(fg_GetData(_Value), Len, 2) + '"'

		if ValueType.IsPointerType():
			Value = Value + "   " + hex(_Value.GetValueAsUnsigned());

		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Array_ch16) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Str_Array_ch32(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Len = _Value.GetNumChildren()

		if fg_RawSummary():
			return fg_MakeStringFromData_ch32_Raw(fg_GetData(_Value), Len, 2)

		Value = '"' + fg_MakeStringFromData_ch32_Raw(fg_GetData(_Value), Len, 2) + '"'

		if ValueType.IsPointerType():
			Value = Value + "   " + hex(_Value.GetValueAsUnsigned());

		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_Array_ch32) error: ', error, ' path: ', _Value.get_expr_path())
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
		pStrData = _Value.CreateValueFromAddress("[TempData]", Address, _Value.GetType().GetBasicType(lldb.eBasicTypeChar).GetPointerType()).AddressOf()
		if fg_RawSummary():
			return fg_MakeStringFromData_ch8_Raw(pStrData.GetPointeeData(0, (Len + 1)*1), Len, 2)
		return hex(Address) + '   "' + fg_MakeStringFromData_ch8_Raw(pStrData.GetPointeeData(_Offset, (Len + 1)*1), Len, 2) + '"'
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_ArrayPtr_ch8) error: ', error, ' path: ', _Value.get_expr_path())
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
		pStrData = _Value.CreateValueFromAddress("[TempData]", Address, _Value.GetType().GetBasicType(lldb.eBasicTypeChar).GetPointerType()).AddressOf()
		if fg_RawSummary():
			return fg_MakeStringFromData_ch16_Raw(pStrData.GetPointeeData(0, (Len + 1)*2), Len, 2)
		return hex(Address) + '   "' + fg_MakeStringFromData_ch16_Raw(pStrData.GetPointeeData(_Offset, (Len + 1)*2), Len, 2) + '"'
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_ArrayPtr_ch16) error: ', error, ' path: ', _Value.get_expr_path())
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
		pStrData = _Value.CreateValueFromAddress("[TempData]", Address, _Value.GetType().GetBasicType(lldb.eBasicTypeChar).GetPointerType()).AddressOf()
		if fg_RawSummary():
			return fg_MakeStringFromData_ch32_Raw(pStrData.GetPointeeData(0, (Len + 1)*4), Len, 2)
		return hex(Address) + '   "' + fg_MakeStringFromData_ch32_Raw(pStrData.GetPointeeData(_Offset, (Len + 1)*4), Len, 2) + '"'
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Str_ArrayPtr_ch32) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Char_ch8) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Char_ch16) error: ', error, ' path: ', _Value.get_expr_path())
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
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Char_ch32) error: ', error, ' path: ', _Value.get_expr_path())
		return

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

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "char *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "char *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "const char *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch8, "const char *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "char \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch8, "char const\\[[0-9]+]", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "ch16 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "ch16 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const ch16 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const ch16 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "ch16 \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "ch16 const\\[[0-9]+]", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "char16_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "char16_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const char16_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch16, "const char16_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "char16_t \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch16, "char16_t const\\[[0-9]+]", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "ch32 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "ch32 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const ch32 *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const ch32 *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "ch32 \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "ch32 const\\[[0-9]+]", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "char32_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "char32_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const char32_t *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_ArrayPtr_ch32, "const char32_t *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "char32_t \\[[0-9]+]", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Array_ch32, "char32_t const\\[[0-9]+]", True)

	# Ptr
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch8, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)CStrTraitsPtr_CStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraitsPtr_CStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch8, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams> > > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams> > > >$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch16, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)CStrTraitsPtr_CWStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraitsPtr_CWStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch16, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams> > > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams> > > >$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch32, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)CStrTraitsPtr_CUStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraitsPtr_CUStr>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch32, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams> > > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Ptr_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Ptr<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams> > > >$", True)


	# Dynamic
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)CStrTraits_CStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraits_CStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*> > > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*> > > >$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch16, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)CStrTraits_CWStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraits_CWStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch16, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*> > > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*> > > >$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch32, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)CStrTraits_CUStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)CStrTraits_CUStr[a-zA-Z]*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch32, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*> > > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*>, (NMib::NStr::)TCStrImp_Dynamic<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CStrImp_Dynamic_[a-zA-Z]*> > > >$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )NMib::NStr::CMStrDeprecated$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Dynamic_ch8, "(^|^const )NMib::NStr::CMStrPreserve$", True)

	# Fixed
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch8, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*> > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch8, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*> > >$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch16, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*> > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch16, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char16_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*> > >$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch32, "(^|^const )(NMib::NStr::)TCStrAggregate<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*> > >$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Str_Fixed_ch32, "(^|^const )(NMib::NStr::)TCStr<(NMib::NStr::)TCTCStrTraits<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, (NMib::NStr::)TCStrImp_Fixed<(NMib::NStr::)TCStrTraits<char32_t, [0-9]*, (NMib::NStr::)CDefaultStrParams>, [0-9]*> > >$", True)

	return
