# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys, os
import threading
import json

g_MaxSynthChildren = 1024
g_bRawSummary = threading.local()

def fg_WriteError(_String):
	try:
		os.write(2, _String.encode('utf-8', 'replace'))
	except Exception:
		pass

def fg_PrintException():
	fg_WriteError(traceback.format_exc())

def fg_PrintError(*p_Args):
	fg_WriteError(" ".join(str(Arg) for Arg in p_Args) + "\n")

def fg_AddSummary(_Debugger, _Function, _Type, _Regex = False, _Priority = 0):
	try:
		if _Regex:
			if _Priority == 0:
				_Debugger.HandleCommand('type summary add -F ' + _Function.__module__ + '.' + _Function.__name__ + ' -x "' + _Type + '" -w MibLLDB')
			else:
				_Debugger.HandleCommand('type summary add -F ' + _Function.__module__ + '.' + _Function.__name__ + ' -x "' + _Type + '" -w MibLLDB_' + str(_Priority))
		else:
			if _Priority == 0:
				_Debugger.HandleCommand('type summary add -F ' + _Function.__module__ + '.' + _Function.__name__ + ' "' + _Type + '" -w MibLLDB')
			else:
				_Debugger.HandleCommand('type summary add -F ' + _Function.__module__ + '.' + _Function.__name__ + ' "' + _Type + '" -w MibLLDB_' + str(_Priority))
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_AddSummary) error: ', error)
		return

def fg_AddSynth(_Debugger, _Class, _Type, _Regex = False, _Priority = 0):
	try:
		if _Regex:
			if _Priority == 0:
				_Debugger.HandleCommand('type synthetic add -l ' + _Class.__module__ + '.' + _Class.__name__ + ' -x "' + _Type + '" -w MibLLDB')
			else:
				_Debugger.HandleCommand('type synthetic add -l ' + _Class.__module__ + '.' + _Class.__name__ + ' -x "' + _Type + '" -w MibLLDB_' + str(_Priority))
		else:
			if _Priority == 0:
				_Debugger.HandleCommand('type synthetic add -l ' + _Class.__module__ + '.' + _Class.__name__ + ' "' + _Type + '" -w MibLLDB')
			else:
				_Debugger.HandleCommand('type synthetic add -l ' + _Class.__module__ + '.' + _Class.__name__ + ' "' + _Type + '" -w MibLLDB_' + str(_Priority))
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_AddSynth) error: ', error)
		return

def fg_RawSummary():
	global g_bRawSummary
	bRawSummary = getattr(g_bRawSummary, 'm_bRawSummary', None)
	if bRawSummary is None:
		return False
	return bRawSummary

def fg_SetRawSummary(_bRaw):
	bOld = fg_RawSummary()
	g_bRawSummary.m_bRawSummary = _bRaw
	return bOld

def fg_ParseTemplate(_String):
	stack = []
	lastStart = 0
	for i, c in enumerate(_String):
		if c == ',' and len(stack) == 1:
			yield _String[lastStart: i].strip()
			lastStart = i + 1
		if c == '<':
			stack.append(i)
			if len(stack) == 1:
				lastStart = i + 1
		elif c == '>' and stack:
			stack.pop()
			if len(stack) == 0:
				yield _String[lastStart: i].strip()

def fg_GetValueRawSummary(_Value):
	bOld = fg_SetRawSummary(True)
	Return = _Value.GetSummary()
	fg_SetRawSummary(bOld)
	return Return;

def fg_QuotedCString(_String):
	return json.dumps(_String)

def fg_GetStringValue(_ValueObject, _Name, _Value):
	Process = _ValueObject.GetProcess()
	String = str(_Value)
	StringLen = len(String)
	Data = lldb.SBData.CreateDataFromCString(Process.GetByteOrder(), Process.GetAddressByteSize(), String)
	Value = _ValueObject.CreateValueFromData(_Name, Data, _ValueObject.GetType().GetBasicType(lldb.eBasicTypeChar).GetArrayType(StringLen))
	Value.SetFormat(lldb.eFormatCharArray)
	return Value

def fg_GetEmptyValue(_ValueObject, _Value = "Empty"):
	return fg_GetStringValue(_ValueObject, "[Empty]", _Value)

def fg_GetUnsignedValue(_ValueObject, _Name, _Value):
	Process = _ValueObject.GetProcess()
	Data = lldb.SBData.CreateDataFromUInt64Array(Process.GetByteOrder(), Process.GetAddressByteSize(), [int(_Value)])
	return _ValueObject.CreateValueFromData(_Name, Data, _ValueObject.GetType().GetBasicType(lldb.eBasicTypeUnsignedLongLong))

def fg_GetDynamicType(_Value, _Type):
	Process = _Value.GetProcess()
	DataAddress = lldb.SBData.CreateDataFromUInt32Array(Process.GetByteOrder(), Process.GetAddressByteSize(), [0, 0])
	return _Value.CreateValueFromData("[Temp]", DataAddress, _Type.GetPointerType()).GetDynamicValue(lldb.eDynamicDontRunTarget).Dereference().GetType()

def fg_CreateDynamicValue(_Value, _Name, _Address, _Type):
	return _Value.CreateValueFromAddress(_Name, _Address, fg_GetDynamicType(_Value, _Type))

def fg_GetData(_Value):
	Type = _Value.GetType()
	if Type.IsReferenceType() or Type.IsPointerType():
		return _Value.Dereference().GetData()
	return _Value.GetData()

def fg_IsInteger(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()

def fg_GetValueAsUnsigned(_Value):
	AddressValue = _Value.GetValueAsUnsigned()
	if type(AddressValue) is int:
		return AddressValue

	return 0

def fg_IsArm64(_Value):
	Target = _Value.GetTarget()
	if Target is not None:
		if Target.GetTriple() == "arm64-apple-macosx11.0.0":
			return True
	return False

def fg_GetAddressOf(_Value):
	Address = _Value.GetAddress()
	Target = _Value.GetTarget()
	if Address is not None and Address.IsValid() and Target is not None:
		LoadAddress = Address.GetLoadAddress(Target)
		if type(LoadAddress) is int and LoadAddress != 0xffffffffffffffff:
			return LoadAddress

	AddressOf = _Value.AddressOf()
	AddressValue = AddressOf.GetValueAsUnsigned()
	if type(AddressValue) is int and AddressValue != 0xffffffffffffffff:
		return AddressValue

	return 0

def fg_GetValueAddress(_Value):
	Type = _Value.GetType()
	if Type.IsReferenceType() or Type.IsPointerType():
		return _Value.GetValueAsUnsigned()
	Value = fg_GetAddressOf(_Value)
	if Value == 0:
		return fg_GetValueAsUnsigned(_Value)
	return Value

def fg_GetPointerAddress(_Value):
	Type = _Value.GetType()
	if Type.IsReferenceType():
		return fg_GetValueAsUnsigned(_Value.GetNonSyntheticValue().GetChildAtIndex(0))
	return fg_GetValueAsUnsigned(_Value)

def fg_PrecacheType(_Type):
	# This seems to workaround bugs in llvm that prevents the type from working properly
	# str(_Type)
	return

def fg_GetCurrentTarget():
	Target = getattr(lldb, 'target', None)
	if Target is not None and Target.IsValid():
		return Target

	Debugger = getattr(lldb, 'debugger', None)
	if Debugger is not None:
		Target = Debugger.GetSelectedTarget()
		if Target is not None and Target.IsValid():
			return Target

	return None

def fg_TraceType(_Type):
	print('Fields')
	for iField in range(0, _Type.GetNumberOfFields()):
		print(str(_Type.GetFieldAtIndex(iField)))
	print('Member functions')
	for iField in range(0, _Type.GetNumberOfMemberFunctions()):
		MemberFunction = _Type.GetMemberFunctionAtIndex(iField);
		print(MemberFunction.GetName() + " " + str(_Type.GetMemberFunctionAtIndex(iField)))
	return

def fg_GetMemberFunction(_Type, _Name):
	for iField in range(0, _Type.GetNumberOfMemberFunctions()):
		MemberFunction = _Type.GetMemberFunctionAtIndex(iField);
		if MemberFunction.GetName() == _Name:
			return MemberFunction
	return None

def fg_GetInheritedType(_Type, _TypeName):
	Type = _Type.GetUnqualifiedType()
	if Type is None:
		return None
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
		if Type is None:
			return None
	Type = Type.GetUnqualifiedType()
	if Type is None:
		return None
	while Type is not None and Type.IsValid() and not Type.GetName().startswith(_TypeName):
		Type = Type.GetDirectBaseClassAtIndex(0).GetType().GetUnqualifiedType()
	return Type

def fg_TypeNameMatchesRoot(_TypeName, _TypeRoot):
	if _TypeName is None:
		return False
	if _TypeName == _TypeRoot:
		return True
	if not _TypeName.startswith(_TypeRoot + '<'):
		return False

	TemplateDepth = 0
	for iChar in range(len(_TypeRoot), len(_TypeName)):
		Char = _TypeName[iChar]
		if Char == '<':
			TemplateDepth += 1
		elif Char == '>':
			TemplateDepth -= 1
			if TemplateDepth == 0:
				return iChar == len(_TypeName) - 1

	return False

def fg_GetBaseValue(_Value, _TypeName):
	Value = _Value.GetNonSyntheticValue()
	while fg_IsValidSBValue(Value):
		TypeName = fg_GetValueType(Value).GetCanonicalType().GetName()
		if fg_TypeNameMatchesRoot(TypeName, _TypeName):
			break
		Value = Value.GetChildAtIndex(0)
	if not fg_IsValidSBValue(Value):
		return _Value.GetNonSyntheticValue()
	return Value.GetNonSyntheticValue()

def fg_GetValueType(_Value):
	Type = _Value.GetType().GetUnqualifiedType()
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
	Type = Type.GetUnqualifiedType()
	return Type

def fg_GetPointerValueType(_Value):
	Type = _Value.GetType().GetPointeeType().GetUnqualifiedType()
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
	Type = Type.GetUnqualifiedType()
	return Type

def fg_IsValidSBValue(_Value):
	if _Value is not None and _Value.IsValid() and _Value.GetError().Success():
		return True
	return False

def fg_SummaryProvider_ContainerShared(_Value, dict, _Options, _Name):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		Len = _Value.GetChildMemberWithName('[Length]')
		if not fg_IsValidSBValue(Len):
			if _Value.GetType().IsReferenceType():
				Deref = _Value.Dereference()
				if fg_IsValidSBValue(Deref):
					Summary = Deref.GetSummary()
					if Summary is not None:
						return Summary
			return None
		Value = str(Len.GetValueAsUnsigned()) + ' ' + _Name
		if Type.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Container) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_ContainerLimitedShared(_Value, dict, _Options, _Name):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		global g_MaxSynthChildren
		Len = _Value.GetChildMemberWithName('[Length]')
		if not fg_IsValidSBValue(Len):
			if _Value.GetType().IsReferenceType():
				Deref = _Value.Dereference()
				if fg_IsValidSBValue(Deref):
					Summary = Deref.GetSummary()
					if Summary is not None:
						return Summary
			return None
		LenValue = Len.GetValueAsUnsigned()
		if LenValue >= g_MaxSynthChildren:
			Value = 'At least ' + str(LenValue) + ' ' + _Name
		else:
			Value = str(LenValue) + ' ' + _Name

		if Type.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value

	except Exception as error:
		fg_PrintError('(fg_SummaryProvider_ContainerLimited) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_Container(_Value, dict):
	return fg_SummaryProvider_ContainerShared(_Value, dict, None, "elements")

def fg_SummaryProvider_ContainerLimited(_Value, dict):
	return fg_SummaryProvider_ContainerLimitedShared(_Value, dict, None, "elements")

def fg_SummaryProvider_ContainerMap(_Value, dict):
	return fg_SummaryProvider_ContainerShared(_Value, dict, None, "key-value pairs")

def fg_SummaryProvider_ContainerMapLimited(_Value, dict):
	return fg_SummaryProvider_ContainerLimitedShared(_Value, dict, None, "key-value pairs")

def fg_ChildPath(_Value, _Path):
	if _Value.GetType().IsPointerType():
		return _Value.GetValueForExpressionPath("->" + _Path)
	else:
		return _Value.GetValueForExpressionPath("." + _Path)

def fg_FindRawChild(_Value, _Name, _Depth = 8):
	if not fg_IsValidSBValue(_Value) or _Depth <= 0:
		return None

	Value = _Value.GetNonSyntheticValue()
	Child = Value.GetChildMemberWithName(_Name)
	if fg_IsValidSBValue(Child):
		return Child

	for iChild in range(Value.GetNumChildren()):
		Child = Value.GetChildAtIndex(iChild).GetNonSyntheticValue()
		if not fg_IsValidSBValue(Child):
			continue
		if Child.GetName() == _Name:
			return Child
		if Child.GetType().IsPointerType():
			continue

		Found = fg_FindRawChild(Child, _Name, _Depth - 1)
		if fg_IsValidSBValue(Found):
			return Found

	return None

def fg_GetValidCanonicalType(_Type):
	CanonicalType = _Type.GetCanonicalType()

	if CanonicalType.GetName() != "void":
		return CanonicalType

	Target = fg_GetCurrentTarget()
	if Target is not None:
		for Type in Target.FindTypes(_Type.GetName()):
			CanonicalType = Type.GetCanonicalType()
			if CanonicalType.GetName() != "void":
				break

	return CanonicalType

def fg_GetContainingType(_Type):
	if _Type is None or not _Type.IsValid() or not hasattr(_Type, 'GetContainingType'):
		return None

	Type = _Type.GetContainingType()
	if Type is None or not Type.IsValid():
		return None

	return fg_GetValidCanonicalType(Type)

def fg_GetValidTemplateArgumentType(_Type, _Index):
	if _Type is None or not _Type.IsValid() or _Type.GetNumberOfTemplateArguments() <= _Index:
		return None

	Type = fg_GetValidCanonicalType(_Type.GetTemplateArgumentType(_Index))
	if Type is None or not Type.IsValid():
		return None

	return Type

def fg_VariantMemberTypeInfo(_MemberType, _Target = None):
	if _MemberType is None or not _MemberType.IsValid():
		return None

	MemberType = _MemberType.GetUnqualifiedType()
	MemberTypeName = MemberType.GetName()
	if MemberTypeName is None or not MemberTypeName.startswith('NMib::NStorage::TCVariantMember<'):
		return None

	if MemberType.GetNumberOfTemplateArguments() < 3:
		return None

	ValueType = MemberType.GetTemplateArgumentType(1)
	if ValueType is None or not ValueType.IsValid():
		return None

	Target = _Target
	if Target is None or not Target.IsValid():
		Target = fg_GetCurrentTarget()
	if Target is None:
		return None
	MemberIndexValue = MemberType.GetTemplateArgumentValue(Target, 2)
	if not fg_IsValidSBValue(MemberIndexValue):
		return None

	return (fg_GetValueAsUnsigned(MemberIndexValue), fg_GetValidCanonicalType(ValueType))

def fg_VariantMemberTypesFromType(_Type, _Target = None):
	MemberTypes = {}
	Visited = set()

	def Visit(_CurrentType):
		if _CurrentType is None or not _CurrentType.IsValid():
			return

		RawType = _CurrentType.GetUnqualifiedType()
		RawTypeName = RawType.GetName() if RawType is not None and RawType.IsValid() else None
		CurrentType = fg_GetValidCanonicalType(_CurrentType).GetUnqualifiedType()
		TypeName = CurrentType.GetName()
		if TypeName is None or TypeName in Visited:
			return
		Visited.add(TypeName)

		if TypeName.startswith('NMib::NStorage::TCVariant<'):
			for iType in range(CurrentType.GetNumberOfTemplateArguments()):
				ValueType = fg_GetValidCanonicalType(CurrentType.GetTemplateArgumentType(iType))
				if ValueType.IsValid():
					MemberTypes.setdefault(iType, ValueType)

		if TypeName.startswith('NMib::NStorage::TCVariantCommon<'):
			if CurrentType.GetNumberOfTemplateArguments() > 1:
				for iType in range(1, CurrentType.GetNumberOfTemplateArguments()):
					MemberType = CurrentType.GetTemplateArgumentType(iType)
					MemberInfo = fg_VariantMemberTypeInfo(MemberType, _Target)
					if MemberInfo is not None:
						MemberTypes.setdefault(MemberInfo[0], MemberInfo[1])

		for iBase in range(CurrentType.GetNumberOfDirectBaseClasses()):
			Visit(CurrentType.GetDirectBaseClassAtIndex(iBase).GetType())

	Visit(_Type)
	return MemberTypes

def fg_GetLeafValue(_Value):
	Current = _Value
	Current.SetPreferSyntheticValue(True)
	NextLevel = Current.GetChildMemberWithName('[Value]')
	while fg_IsValidSBValue(NextLevel) and NextLevel.GetName() == '[Value]':
		Current = NextLevel
		NextLevel = Current.GetChildMemberWithName('[Value]')

	return Current

def fg_SummaryProvider_IteratorCommon(_Value, dict):
	try:
		_Value.SetPreferSyntheticValue(True)
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		ValueMember = _Value.GetChildMemberWithName('[Empty]')
		if ValueMember:
			return fg_GetValueRawSummary(ValueMember)

		Current = fg_GetLeafValue(_Value.GetChildMemberWithName('[Value]'))

		if not fg_IsValidSBValue(Current):
			Current = _Value.GetChildMemberWithName('[Invalid]')
			if fg_IsValidSBValue(Current):
				Value = "Invalid or uninitialized"
			else:
				return ""
		else:
			if Current.GetType().IsPointerType():
				PointerValue = Current.GetValueAsUnsigned()
				if PointerValue == 0:
					Value = "nullptr";
				else:
					CurrentDeref = Current.Dereference();
					Summary = CurrentDeref.GetSummary()
					if Summary is not None:
						Value = hex(PointerValue) + "   " + Summary
					else:
						Value = CurrentDeref.GetValue()
						if Value is not None:
							Value = hex(PointerValue) + "   " + str(Value)
			else:
				Summary = Current.GetSummary()
				if Summary is not None:
					Value = Summary
				else:
					Value = Current.GetValue()
					if Value is not None:
						Value = str(Value)

		if Value is not None:
			if Type.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Value
			return Value

		ReturnString = "{ "
		Overflow = False
		AddedFirst = False
		for iChild in range(Current.GetNumChildren()):
			Child = Current.GetChildAtIndex(iChild)
			Summary = Child.GetSummary()
			if not Summary:
				Summary = Child.GetValue()
				if Summary:
					Summary = str(Summary)
			if Summary:
				if len(ReturnString) > 64:
					Overflow = True
					break

				if AddedFirst:
					ReturnString += ", "

				AddedFirst = True
				ReturnString += Child.GetName() + " = " + Summary

		if Overflow:
			ReturnString += ", ... }"
		else:
			ReturnString += " }"

		return ReturnString;
	except Exception as error:
		fg_PrintException()
		fg_PrintError('common summary error: ', error)
		return None


class CSynthProvider_Common:
	def __init__(self, _ValueObject, _Dictionary, _ExpectedTypeName = None):
		self.m_ValueObject = _ValueObject
		if _ExpectedTypeName is not None:
			self.m_ValueObject = fg_GetBaseValue(self.m_ValueObject, _ExpectedTypeName)

		self.m_ValueObjectType = fg_GetValidCanonicalType(self.m_ValueObject.GetType())

		if self.m_ValueObjectType.IsPointerType():
			self.m_ValueObjectDeref = self.m_ValueObject.Dereference()
		else:
			self.m_ValueObjectDeref = self.m_ValueObject
		self.m_Count = None
		self.m_bValid = False
		self.m_bEmpty = False
		self.m_bUpdated = False
		self.m_OriginalNameMap = None
		self.m_bShowOriginalChildren = True

	def update(self):
		self.m_Count = None
		self.m_bUpdated = True
		self.m_bValid = False
		try:
			self.m_nOriginalChildren = self.m_ValueObject.GetNumChildren()
			self.m_OriginalNameMap = {};

			for iOriginalChild in range(0, self.m_nOriginalChildren):
				Child = self.m_ValueObject.GetChildAtIndex(iOriginalChild)
				if not Child.IsValid():
					self.m_nOriginalChildren = self.m_nOriginalChildren - 1
					continue
				self.m_OriginalNameMap[Child.GetName()] = iOriginalChild
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def has_children(self):
		return True

	def num_children(self):
		try:
			if not self.m_bUpdated:
				self.update()
			if self.m_Count is None:
				if not self.m_bValid:
					self.m_Count = 0
				else:
					try:
						self.m_Count = self.fp_NumChildren()
					except Exception as error:
						fg_PrintException()
						fg_PrintError('(' + self.__class__.__name__ + ') num_children error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
						self.m_Count = 0

			nOriginalChildren = self.m_nOriginalChildren if self.m_bShowOriginalChildren else 0
			return int(self.m_Count + nOriginalChildren)
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') num_children error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return 0

	def get_child_index(self, _Name):
		try:
			if self.m_OriginalNameMap is None or not self.m_bShowOriginalChildren:
				return -1
			OriginalIndex = self.m_OriginalNameMap.get(_Name)
			if OriginalIndex is not None:
				if self.m_Count is None:
					self.num_children()
				return int(self.m_Count + OriginalIndex)
			if self.m_bValid:
				Return = self.fp_GetChildIndex(_Name)
				if Return is not None:
					return int(Return)
			return -1
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') get_child_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return -1

	def fp_GetChildIndex(self, _Name):
		Stripped = _Name.lstrip('[').rstrip(']')
		if Stripped.isdigit():
			return int(Stripped)
		return -1

	def get_child_at_index(self, _iChild):
		try:
			nChildren = self.num_children()
			if nChildren < 0:
				return None
			if _iChild >= nChildren:
				return None
			if _iChild >= self.m_Count:
				if not self.m_bShowOriginalChildren:
					return None
				return self.m_ValueObject.GetChildAtIndex(_iChild - self.m_Count)
			if self.m_bValid:
				try:
					return self.fp_GetChildAtIndex(_iChild)
				except Exception as error:
					fg_PrintException()
					fg_PrintError('(' + self.__class__.__name__ + ') get_child_at_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
					return None
			return None
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') get_child_at_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return None

	def fp_GetChildAtIndex(self, _iChild):
		return None

	def fp_NumChildren(self):
		return 0


class CSynthProvider_Container(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary, _ExpectedTypeName = None):
		self.m_nElements = None
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, _ExpectedTypeName)

	def update(self):
		CSynthProvider_Common.update(self)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			if self.m_nElements is None:
				return None;
			return fg_GetUnsignedValue(self.m_ValueObject, "[Length]", self.m_nElements)
		if self.m_Error is not None:
			if _iChild == 1:
				return fg_GetStringValue(self.m_ValueObject, "[Error]", self.m_Error)
			return self.fp_ContainerGetChildAtIndex(_iChild - 2);
		else:
			return self.fp_ContainerGetChildAtIndex(_iChild - 1);

	def fp_ContainerChildAtIndex(self, _iChild):
		return 0;

	def fp_GetChildIndex(self, _Name):
		iChild = self.fp_ContainerGetChildIndex(_Name)
		if iChild >= 0:
			return iChild
		if _Name == '[Length]':
			return 0
		if _Name == '[Error]':
			return 1
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name) + 1

	def fp_ContainerGetChildIndex(self, _Name):
		return -1

	def fp_NumChildren(self):
		global g_MaxSynthChildren
		self.m_nElements = self.fp_ContainerNumChildren()
		self.m_Error = self.fp_ContainerGetError()
		Ret = self.m_nElements
		if Ret > g_MaxSynthChildren:
			Ret = g_MaxSynthChildren;
		if self.m_Error is not None:
			return Ret + 2
		else:
			return Ret + 1

	def fp_ContainerNumChildren(self):
		return 0

	def fp_ContainerGetError(self):
		return None


def fg_MibLLDBInit_Common(_Debugger):
	return
