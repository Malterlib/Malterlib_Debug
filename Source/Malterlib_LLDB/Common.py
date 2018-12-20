# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
import threading
import json

g_MaxSynthChildren = 1024
g_bRawSummary = threading.local()

g_ModuleName = ""

def fg_SetModuleName(_Name):
	global g_ModuleName
	g_ModuleName = _Name


def fg_AddSummary(_Debugger, _Function, _Type, _Regex = False, _Priority = 0):
	global g_ModuleName
	if _Regex:
		if _Priority == 0:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' -x "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' -x "' + _Type + '" -w MibLLDB_' + str(_Priority))
	else:
		if _Priority == 0:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type summary add -F ' + g_ModuleName + '.' + _Function.__name__ + ' "' + _Type + '" -w MibLLDB_' + str(_Priority))

def fg_AddSynth(_Debugger, _Class, _Type, _Regex = False, _Priority = 0):
	global g_ModuleName
	if _Regex:
		if _Priority == 0:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' -x "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' -x "' + _Type + '" -w MibLLDB_' + str(_Priority))
	else:
		if _Priority == 0:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' "' + _Type + '" -w MibLLDB')
		else:
			_Debugger.HandleCommand('type synthetic add -l ' + g_ModuleName + '.' + _Class.__name__ + ' "' + _Type + '" -w MibLLDB_' + str(_Priority))

def fg_RawSummary():
	global g_bRawSummary
	bRawSummary = getattr(g_bRawSummary, 'm_bRawSummary', None)
	if bRawSummary == None:
		return False
	return bRawSummary

def fg_SetRawSummary(_bRaw):
	bOld = fg_RawSummary()
	g_bRawSummary.m_bRawSummary = _bRaw
	return bOld

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
	Value = _ValueObject.GetProcess().GetSelectedThread().GetSelectedFrame().EvaluateExpression(fg_QuotedCString(String))
	StringLen = len(String) + 1
	Data = Value.GetPointeeData(0, StringLen)
	return _ValueObject.CreateValueFromData(_Name, Data, _ValueObject.GetType().GetBasicType(lldb.eBasicTypeChar).GetArrayType(StringLen))

def fg_GetEmptyValue(_ValueObject, _Value = "Empty"):
	return fg_GetStringValue(_ValueObject, "[Empty]", _Value)

def fg_GetDynamicType(_Value, _Type, _Address):
	Process = _Value.GetProcess()
	if type(_Address) is not int:
		_Address = 0
	DataAddress = lldb.SBData.CreateDataFromUInt64Array(Process.GetByteOrder(), Process.GetAddressByteSize(), [_Address])
	return _Value.CreateValueFromData("[Temp]", DataAddress, _Type.GetPointerType()).GetDynamicValue(lldb.eDynamicDontRunTarget).Dereference().GetType()

def fg_CreateDynamicValue(_Value, _Name, _Address, _Type):
	return _Value.CreateValueFromAddress(_Name, _Address, fg_GetDynamicType(_Value, _Type, _Address))

def fg_IsInteger(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()

def fg_GetValueAsUnsigned(_Value):
	AddressValue = _Value.GetValueAsUnsigned()
	if type(AddressValue) is int:
		return AddressValue

	return 0

def fg_GetAddressOf(_Value):
	Address = _Value.GetAddress()
	if Address.IsValid():
		LoadAddress = Address.load_addr
		if type(LoadAddress) is int:
			return LoadAddress

	AddressOf = _Value.AddressOf()
	AddressValue = AddressOf.GetValueAsUnsigned()
	if type(AddressValue) is int:
		return AddressOf.GetValueAsUnsigned()

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

def fg_TraceType(_Type):
	print 'Fields'
	for iField in range(0, _Type.GetNumberOfFields()):
		print str(_Type.GetFieldAtIndex(iField))
	print 'Member functions'
	for iField in range(0, _Type.GetNumberOfMemberFunctions()):
		MemberFunction = _Type.GetMemberFunctionAtIndex(iField);
		print MemberFunction.GetName() + " " + str(_Type.GetMemberFunctionAtIndex(iField))
	return

def fg_GetMemberFunction(_Type, _Name):
	for iField in range(0, _Type.GetNumberOfMemberFunctions()):
		MemberFunction = _Type.GetMemberFunctionAtIndex(iField);
		if MemberFunction.GetName() == _Name:
			return MemberFunction
	return None

def fg_GetInheritedType(_Type, _TypeName):
	Type = _Type.GetUnqualifiedType()
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
	Type = Type.GetUnqualifiedType()
	while Type != None and Type.IsValid() and not Type.GetName().startswith(_TypeName):
		Type = Type.GetDirectBaseClassAtIndex(0).GetType().GetUnqualifiedType()
	return Type

def fg_GetBaseValue(_Value, _TypeName):
	Value = _Value.GetNonSyntheticValue()
	while Value != None and Value.IsValid() and not Value.GetType().GetCanonicalType().GetName().startswith(_TypeName):
		Value = Value.GetChildAtIndex(0)
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
	if _Value != None and _Value.IsValid() and _Value.GetError().Success():
		return True
	return False

def fg_SummaryProvider_ContainerShared(_Value, dict, _Name):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return None # Pointer to pointer we don't want to provide summary for

		Len = _Value.GetChildMemberWithName('[Length]')
		if not fg_IsValidSBValue(Len):
			return None
		Value = str(Len.GetValueAsUnsigned()) + ' ' + _Name
		if Type.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print '(fg_SummaryProvider_Container) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_SummaryProvider_ContainerLimitedShared(_Value, dict, _Name):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return None # Pointer to pointer we don't want to provide summary for
		
		global g_MaxSynthChildren
		Len = _Value.GetChildMemberWithName('[Length]')
		if not fg_IsValidSBValue(Len):
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
		print '(fg_SummaryProvider_ContainerLimited) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_SummaryProvider_Container(_Value, dict):
	return fg_SummaryProvider_ContainerShared(_Value, dict, "elements")

def fg_SummaryProvider_ContainerLimited(_Value, dict):
	return fg_SummaryProvider_ContainerLimitedShared(_Value, dict, "elements")

def fg_SummaryProvider_ContainerMap(_Value, dict):
	return fg_SummaryProvider_ContainerShared(_Value, dict, "key-value pairs")

def fg_SummaryProvider_ContainerMapLimited(_Value, dict):
	return fg_SummaryProvider_ContainerLimitedShared(_Value, dict, "key-value pairs")

def fg_ChildPath(_Value, _Path):
	if _Value.GetType().IsPointerType():
		return _Value.GetValueForExpressionPath("->" + _Path)
	else:
		return _Value.GetValueForExpressionPath("." + _Path)

def fg_GetValidCanonicalType(_Type):
	CanonicalType = _Type.GetCanonicalType()

	if CanonicalType.GetName() != "void":
		return CanonicalType

	for Type in lldb.target.FindTypes(_Type.GetName()):
		CanonicalType = Type.GetCanonicalType()
		if CanonicalType.GetName() != "void":
			break

	return CanonicalType

def fg_GetLeafValue(_Value):
	Current = _Value
	NextLevel = Current.GetChildMemberWithName('[Value]')
	while fg_IsValidSBValue(NextLevel) and NextLevel.GetName() == '[Value]':
		Current = NextLevel
		NextLevel = Current.GetChildMemberWithName('[Value]')

	return Current

def fg_SummaryProvider_IteratorCommon(_Value, dict):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return "" # Pointer to pointer we don't want to provide summary for

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
					if Summary != None:
						Value = hex(PointerValue) + "   " + Summary
					else:
						Value = CurrentDeref.GetValue()
						if Value != None:
							Value = hex(PointerValue) + "   " + str(Value)
			else:
				Summary = Current.GetSummary()
				if Summary != None:
					Value = Summary
				else:
					Value = Current.GetValue()
					if Value != None:
						Value = str(Value)
					
		if Value != None:
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
		traceback.print_exc(file=sys.stdout)
		print 'common summary error: ', error
		return None


class CSynthProvider_Common:
	def __init__(self, _ValueObject, _Dictionary, _ExpectedTypeName = None):
		self.m_ValueObject = _ValueObject
		if _ExpectedTypeName != None:
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
			traceback.print_exc(file=sys.stdout)
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def has_children(self):
		return True
				
	def num_children(self):
		try:
			if not self.m_bUpdated:
				self.update()
			if self.m_Count == None:
				if not self.m_bValid:
					self.m_Count = 0
				else:
					try:
						self.m_Count = self.fp_NumChildren()
					except Exception as error:
						traceback.print_exc(file=sys.stdout)
						print '(' + self.__class__.__name__ + ') num_children error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
						self.m_Count = 0
			
			return int(self.m_Count + self.m_nOriginalChildren)
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print '(' + self.__class__.__name__ + ') num_children error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return 0

	def get_child_index(self, _Name):
		try:
			if self.m_OriginalNameMap == None:
				return -1
			OriginalIndex = self.m_OriginalNameMap.get(_Name)
			if OriginalIndex != None:
				if self.m_Count == None:
					self.num_children()
				return int(self.m_Count + OriginalIndex)
			if self.m_bValid:
				Return = self.fp_GetChildIndex(_Name)
				if Return != None:
					return int(Return)
			return -1
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print '(' + self.__class__.__name__ + ') get_child_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
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
				return self.m_ValueObject.GetChildAtIndex(_iChild - self.m_Count)
			if self.m_bValid:
				try:
					return self.fp_GetChildAtIndex(_iChild)
				except Exception as error:
					traceback.print_exc(file=sys.stdout)
					print '(' + self.__class__.__name__ + ') get_child_at_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
					return None
			return None
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print '(' + self.__class__.__name__ + ') get_child_at_index error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
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
			if self.m_nElements == None:
				return None;
			return self.m_ValueObject.CreateValueFromExpression("[Length]", str(self.m_nElements))
		if self.m_Error != None:
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
		if self.m_Error != None:
			return Ret + 2
		else:
			return Ret + 1

	def fp_ContainerNumChildren(self):
		return 0

	def fp_ContainerGetError(self):
		return None


def fg_MibLLDBInit_Common(_Debugger):
	return
