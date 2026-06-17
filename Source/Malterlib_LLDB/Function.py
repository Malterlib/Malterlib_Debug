# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *

g_FunctionCallInfoCache = {}
g_FunctionLocationCache = {}
g_FunctionVTableCallCache = {}
g_FunctionGlobalVariableCache = {}

def fg_FunctionTypeName(_ValueObject):
	ValueType = fg_GetValueType(_ValueObject)
	if ValueType is None or not ValueType.IsValid():
		return ""
	TypeName = ValueType.GetName()
	if TypeName is None:
		return ""
	return TypeName

def fg_FunctionTemplateArgumentInt(_ValueObject, _Type, _iTemplateArg, _Default):
	if _Type is None or not _Type.IsValid():
		return _Default

	try:
		Value = _Type.GetTemplateArgumentValue(_ValueObject.GetTarget(), _iTemplateArg)
		if fg_IsValidSBValue(Value):
			ValueString = Value.GetValue()
			if ValueString is not None:
				return int(ValueString, 0)
	except Exception:
		pass

	return _Default

def fg_FunctionFindChild(_ValueObject, _Name, _MaxDepth = 8):
	if _ValueObject is None or _MaxDepth < 0:
		return None

	ValueObject = _ValueObject.GetNonSyntheticValue()
	if not fg_IsValidSBValue(ValueObject):
		return None

	Child = ValueObject.GetChildMemberWithName(_Name)
	if fg_IsValidSBValue(Child):
		return Child

	for iChild in range(ValueObject.GetNumChildren()):
		Child = ValueObject.GetChildAtIndex(iChild).GetNonSyntheticValue()
		if not fg_IsValidSBValue(Child):
			continue
		if Child.GetName() == _Name:
			return Child
		if Child.GetType().IsPointerType():
			continue

		Found = fg_FunctionFindChild(Child, _Name, _MaxDepth - 1)
		if fg_IsValidSBValue(Found):
			return Found

	return None

def fg_FunctionVTableAddressFromBitStorePointer(_ValueObject, _VTablePointer):
	RawPointer = _VTablePointer.GetNonSyntheticValue()
	PointTo = RawPointer.GetChildMemberWithName("mp_PointTo")
	if not fg_IsValidSBValue(PointTo):
		PointTo = _VTablePointer.GetChildMemberWithName("mp_PointTo")
	if not fg_IsValidSBValue(PointTo):
		return None

	PointToValue = fg_GetValueAsUnsigned(PointTo)
	if PointToValue == 0:
		return None

	nBits = fg_FunctionTemplateArgumentInt(_ValueObject, RawPointer.GetType(), 1, 2)
	return PointToValue << nBits

def fg_FunctionVTableBitsFromBitStorePointer(_VTablePointer):
	RawPointer = _VTablePointer.GetNonSyntheticValue()
	Bits = RawPointer.GetChildMemberWithName("mp_Bits")
	if not fg_IsValidSBValue(Bits):
		Bits = _VTablePointer.GetChildMemberWithName("mp_Bits")
	if not fg_IsValidSBValue(Bits):
		return None

	return fg_GetValueAsUnsigned(Bits)

def fg_FunctionVTableTypeFromBitStorePointer(_VTablePointer):
	VTablePointerType = _VTablePointer.GetNonSyntheticValue().GetType()
	VTableType = VTablePointerType.GetTemplateArgumentType(0)
	if VTableType is None or not VTableType.IsValid():
		VTableType = _VTablePointer.GetType().GetTemplateArgumentType(0)
	if VTableType is None or not VTableType.IsValid():
		return None
	if VTableType.IsPointerType():
		VTableType = VTableType.GetPointeeType()
	return VTableType

def fg_FunctionVTableFromPointer(_ValueObject, _VTablePointer):
	if not fg_IsValidSBValue(_VTablePointer):
		return None

	VTablePointerType = _VTablePointer.GetType()
	VTablePointerTypeName = VTablePointerType.GetName()
	if VTablePointerTypeName is not None and "TCBitStorePointer<" in VTablePointerTypeName:
		VTableAddress = fg_FunctionVTableAddressFromBitStorePointer(_ValueObject, _VTablePointer)
		if VTableAddress is None:
			return None
		VTableType = fg_FunctionVTableTypeFromBitStorePointer(_VTablePointer)
		if VTableType is None:
			return None
		return _ValueObject.CreateValueFromAddress("[VTable]", VTableAddress, VTableType)

	if VTablePointerType.IsPointerType():
		if _VTablePointer.GetValueAsUnsigned() == 0:
			return None
		return _VTablePointer.Dereference()

	return _VTablePointer

def fg_FunctionVTablePointer(_ValueObject):
	TypeName = fg_FunctionTypeName(_ValueObject)

	if TypeName.startswith("NMib::NFunction::TCFunctionSmall<"):
		Imp = fg_FunctionFindChild(_ValueObject, "m_pImp")
		if fg_IsValidSBValue(Imp) and Imp.GetType().IsPointerType() and Imp.GetValueAsUnsigned() != 0:
			return fg_FunctionFindChild(Imp.Dereference(), "m_pVTable", 2)
		return None

	return fg_FunctionFindChild(_ValueObject, "m_pVTable")

def fg_FunctionVTable(_ValueObject):
	return fg_FunctionVTableFromPointer(_ValueObject, fg_FunctionVTablePointer(_ValueObject))

def fg_FunctionVTableAddress(_ValueObject):
	VTablePointer = fg_FunctionVTablePointer(_ValueObject)
	if not fg_IsValidSBValue(VTablePointer):
		return None

	VTablePointerTypeName = VTablePointer.GetType().GetName()
	if VTablePointerTypeName is not None and "TCBitStorePointer<" in VTablePointerTypeName:
		return fg_FunctionVTableAddressFromBitStorePointer(_ValueObject, VTablePointer)
	if VTablePointer.GetType().IsPointerType():
		Address = VTablePointer.GetValueAsUnsigned()
		if Address != 0:
			return Address
		return None

	VTable = fg_FunctionVTableFromPointer(_ValueObject, VTablePointer)
	if not fg_IsValidSBValue(VTable):
		return None
	return fg_GetValueAddress(VTable)

def fg_FunctionSmallImp(_ValueObject):
	ValueObject = _ValueObject.GetNonSyntheticValue()
	Imp = ValueObject.GetValueForExpressionPath(".m_Data.m_pImp")
	if fg_IsValidSBValue(Imp):
		return Imp

	return fg_FunctionFindChild(_ValueObject, "m_pImp")

def fg_FunctionVTableBits(_ValueObject):
	VTablePointer = fg_FunctionVTablePointer(_ValueObject)
	if not fg_IsValidSBValue(VTablePointer):
		return None

	VTablePointerTypeName = VTablePointer.GetType().GetName()
	if VTablePointerTypeName is None or "TCBitStorePointer<" not in VTablePointerTypeName:
		return None

	return fg_FunctionVTableBitsFromBitStorePointer(VTablePointer)

def fg_FunctionReadMemoryBytes(_ValueObject, _Address, _Size):
	if _Address is None or _Size is None:
		return None

	Error = lldb.SBError()
	Data = _ValueObject.GetProcess().ReadMemory(_Address, _Size, Error)
	if Error.Success() and len(Data) == _Size:
		return bytes(Data)
	return None

def fg_FunctionReadPointer(_ValueObject, _Address):
	if _Address is None:
		return None

	PointerSize = _ValueObject.GetProcess().GetAddressByteSize()
	PointerBytes = fg_FunctionReadMemoryBytes(_ValueObject, _Address, PointerSize)
	if PointerBytes is None:
		return None

	ByteOrder = "little"
	if _ValueObject.GetProcess().GetByteOrder() == lldb.eByteOrderBig:
		ByteOrder = "big"

	Pointer = int.from_bytes(PointerBytes, byteorder = ByteOrder)
	if Pointer == 0:
		return None

	return Pointer

def fg_FunctionTargetKey(_ValueObject):
	Target = _ValueObject.GetTarget()
	if Target is None or not Target.IsValid():
		return None

	Executable = Target.GetExecutable()
	ExecutablePath = ""
	if Executable is not None and Executable.IsValid():
		ExecutablePath = Executable.fullpath

	return (Target.GetTriple(), ExecutablePath)

def fg_FunctionIsValidSBType(_Type):
	return _Type is not None and _Type.IsValid()

def fg_FunctionGetTypeName(_Type):
	if not fg_FunctionIsValidSBType(_Type):
		return ""

	TypeName = _Type.GetName()
	if TypeName is None:
		TypeName = _Type.GetDisplayTypeName()
	if TypeName is None:
		return ""
	return TypeName

def fg_FunctionCallAddressFromVTableAddress(_ValueObject, _VTableAddress):
	if _VTableAddress is None or _VTableAddress == 0:
		return None

	CacheKey = (fg_FunctionTargetKey(_ValueObject), _VTableAddress)
	if CacheKey in g_FunctionVTableCallCache:
		return g_FunctionVTableCallCache[CacheKey]

	CallAddress = fg_FunctionReadPointer(_ValueObject, _VTableAddress)
	g_FunctionVTableCallCache[CacheKey] = CallAddress
	return CallAddress

def fg_FunctionCallAddress(_ValueObject):
	Call = fg_FunctionFindChild(_ValueObject, "m_pCall")
	if fg_IsValidSBValue(Call):
		AddressValue = fg_GetValueAsUnsigned(Call)
		if AddressValue != 0:
			return AddressValue

	TypeName = fg_FunctionTypeName(_ValueObject)
	if TypeName.startswith("NMib::NFunction::TCFunctionSmall<"):
		Imp = fg_FunctionSmallImp(_ValueObject)
		if not fg_IsValidSBValue(Imp):
			return None
		ImpAddress = Imp.GetValueAsUnsigned()
		if ImpAddress == 0:
			return None
		VTableAddress = fg_FunctionReadPointer(_ValueObject, ImpAddress)
		return fg_FunctionCallAddressFromVTableAddress(_ValueObject, VTableAddress)

	VTablePointer = fg_FunctionVTablePointer(_ValueObject)
	if not fg_IsValidSBValue(VTablePointer):
		return None

	VTablePointerTypeName = VTablePointer.GetType().GetName()
	if VTablePointerTypeName is not None and "TCBitStorePointer<" in VTablePointerTypeName:
		VTableAddress = fg_FunctionVTableAddressFromBitStorePointer(_ValueObject, VTablePointer)
	elif VTablePointer.GetType().IsPointerType():
		VTableAddress = VTablePointer.GetValueAsUnsigned()
	else:
		VTable = fg_FunctionVTableFromPointer(_ValueObject, VTablePointer)
		if not fg_IsValidSBValue(VTable):
			return None
		VTableAddress = fg_GetValueAddress(VTable)

	return fg_FunctionCallAddressFromVTableAddress(_ValueObject, VTableAddress)

def fg_FunctionCallInfoCacheKey(_ValueObject):
	TargetKey = fg_FunctionTargetKey(_ValueObject)
	TypeName = fg_FunctionTypeName(_ValueObject)
	if TypeName.startswith("NMib::NFunction::TCFunctionSmall<"):
		Imp = fg_FunctionSmallImp(_ValueObject)
		if fg_IsValidSBValue(Imp):
			ImpAddress = Imp.GetValueAsUnsigned()
			if ImpAddress != 0:
				VTableAddress = fg_FunctionReadPointer(_ValueObject, ImpAddress)
				if VTableAddress is not None:
					return ((TargetKey, "VTable", VTableAddress), None)

	VTableAddress = fg_FunctionVTableAddress(_ValueObject)
	if VTableAddress is not None:
		return ((TargetKey, "VTable", VTableAddress), fg_FunctionCallAddress(_ValueObject))

	CallAddress = fg_FunctionCallAddress(_ValueObject)
	return ((TargetKey, "Call", CallAddress), CallAddress)

def fg_FunctionCallFunction(_ValueObject):
	AddressValue = fg_FunctionCallAddress(_ValueObject)
	if AddressValue is None:
		return None

	Target = _ValueObject.GetTarget()
	if Target is None or not Target.IsValid():
		return None

	Address = Target.ResolveLoadAddress(AddressValue)
	if not Address.IsValid():
		return None

	Function = Address.GetFunction()
	if Function.IsValid():
		return Function

	return None

def fg_FunctionTemplateArgumentValue(_ValueObject, _Type, _iTemplateArg, _Default):
	if not fg_FunctionIsValidSBType(_Type):
		return _Default

	try:
		Value = _Type.GetTemplateArgumentValue(_ValueObject.GetTarget(), _iTemplateArg)
		if fg_IsValidSBValue(Value):
			ValueString = Value.GetValue()
			if ValueString is not None:
				return ValueString
	except Exception:
		pass

	return _Default

def fg_FunctionIsUniquePointerType(_Type):
	return fg_FunctionGetTypeName(_Type).startswith("NMib::NStorage::TCUniquePointer<")

def fg_FunctionGlobalVariableAtAddress(_ValueObject, _Name, _Address):
	if _Address is None:
		return None

	CacheKey = (fg_FunctionTargetKey(_ValueObject), _Name, _Address)
	if CacheKey in g_FunctionGlobalVariableCache:
		return g_FunctionGlobalVariableCache[CacheKey]

	Target = _ValueObject.GetTarget()
	if Target is None or not Target.IsValid():
		return None

	if not hasattr(Target, "FindGlobalVariableByAddress"):
		return None

	Variable = Target.FindGlobalVariableByAddress(_Address)
	if fg_IsValidSBValue(Variable):
		g_FunctionGlobalVariableCache[CacheKey] = Variable
		return Variable

	g_FunctionGlobalVariableCache[CacheKey] = None
	return None

def fg_FunctionIsThisTagType(_Type):
	if not fg_FunctionIsValidSBType(_Type):
		return False

	Type = _Type
	if Type.IsReferenceType():
		Type = Type.GetDereferencedType()
	if not fg_FunctionIsValidSBType(Type):
		return False

	Type = Type.GetUnqualifiedType()
	if not fg_FunctionIsValidSBType(Type):
		return False

	Type = Type.GetCanonicalType()
	if not fg_FunctionIsValidSBType(Type):
		return False

	return fg_FunctionGetTypeName(Type) == "NMib::NFunction::CThisTag"

def fg_FunctionIsConstThisTagReference(_Type):
	if not fg_FunctionIsValidSBType(_Type) or not _Type.IsReferenceType():
		return False

	TypeName = fg_FunctionGetTypeName(_Type)
	return TypeName == "const NMib::NFunction::CThisTag &" or TypeName == "NMib::NFunction::CThisTag const &"

def fg_FunctionSignatureThisTagInfo(_SignatureType):
	if not fg_FunctionIsValidSBType(_SignatureType):
		return (0, "1")

	Arguments = _SignatureType.GetFunctionArgumentTypes()
	if not Arguments.IsValid() or Arguments.GetSize() == 0:
		return (0, "1")

	FirstArgumentType = Arguments.GetTypeAtIndex(0)
	if not fg_FunctionIsThisTagType(FirstArgumentType):
		return (0, "1")

	if fg_FunctionIsConstThisTagReference(FirstArgumentType):
		return (1, "1")

	return (1, "0")

def fg_FunctionCallInfoFromVTableDeclaringType(_ValueObject):
	VTableAddress = fg_FunctionVTableAddress(_ValueObject)
	VTableVariable = fg_FunctionGlobalVariableAtAddress(_ValueObject, "mc_VTable", VTableAddress)
	if not fg_IsValidSBValue(VTableVariable) or not hasattr(VTableVariable, "GetDeclaringType"):
		return None

	VTableType = VTableVariable.GetDeclaringType()
	if not fg_FunctionIsValidSBType(VTableType) or VTableType.GetNumberOfTemplateArguments() < 2:
		return None

	FunctorStorageType = VTableType.GetTemplateArgumentType(0)
	OptionsType = VTableType.GetTemplateArgumentType(1)
	if not fg_FunctionIsValidSBType(FunctorStorageType):
		return None

	FunctorStorageTypeName = fg_FunctionGetTypeName(FunctorStorageType)
	bIndirection = fg_FunctionIsUniquePointerType(FunctorStorageType)
	FunctorType = FunctorStorageType
	if bIndirection and FunctorStorageType.GetNumberOfTemplateArguments() > 0:
		UnwrappedType = FunctorStorageType.GetTemplateArgumentType(0)
		if fg_FunctionIsValidSBType(UnwrappedType):
			FunctorType = UnwrappedType

	SignatureType = None
	if fg_FunctionIsValidSBType(OptionsType) and OptionsType.GetNumberOfTemplateArguments() > 0:
		SignatureType = OptionsType.GetTemplateArgumentType(0)
	SignatureArgumentOffset, Qualifier = fg_FunctionSignatureThisTagInfo(SignatureType)

	return {
		"CallAddress": fg_FunctionCallAddress(_ValueObject),
		"CallType": VTableType,
		"ImplType": VTableType,
		"ImplTypeName": fg_FunctionGetTypeName(VTableType),
		"FunctorStorageType": FunctorStorageType,
		"FunctorStorageTypeName": FunctorStorageTypeName,
		"FunctorType": FunctorType,
		"FunctorTypeName": fg_FunctionGetTypeName(FunctorType),
		"SignatureType": SignatureType,
		"Signature": fg_FunctionGetTypeName(SignatureType),
		"SignatureArgumentOffset": SignatureArgumentOffset,
		"Qualifier": Qualifier,
		"bIndirection": bIndirection,
	}

def fg_FunctionCallInfo(_ValueObject):
	CacheKey, CallAddress = fg_FunctionCallInfoCacheKey(_ValueObject)
	if CacheKey in g_FunctionCallInfoCache:
		return g_FunctionCallInfoCache[CacheKey]

	if CallAddress is None:
		CallAddress = fg_FunctionCallAddress(_ValueObject)
	CallInfo = fg_FunctionCallInfoFromVTableDeclaringType(_ValueObject)
	if CallInfo is None:
		return None
	CallInfo["CallAddress"] = CallAddress

	g_FunctionCallInfoCache[CacheKey] = CallInfo
	return CallInfo

def fg_FunctionStorageAddress(_ValueObject, _TypeName):
	Storage = fg_FunctionStorage(_ValueObject, _TypeName)
	if not fg_IsValidSBValue(Storage):
		return None

	Address = fg_GetValueAddress(Storage)
	if Address == 0:
		return None

	if _TypeName.startswith("NMib::NFunction::TCFunctionSmall<"):
		PointeeType = Storage.GetType().GetPointeeType()
		if PointeeType is not None and PointeeType.IsValid():
			Address += PointeeType.GetByteSize()

	return Address

def fg_FunctionStoredFunctorAddress(_ValueObject, _TypeName, _CallInfo = None):
	Address = fg_FunctionStorageAddress(_ValueObject, _TypeName)
	if Address is None:
		return None

	if _CallInfo is not None and _CallInfo["bIndirection"]:
		FunctorStorageType = _CallInfo.get("FunctorStorageType", None)
		if fg_FunctionIsValidSBType(FunctorStorageType):
			StoredPointer = _ValueObject.CreateValueFromAddress("[TempData]", Address, FunctorStorageType)
			PointTo = fg_FunctionFindChild(StoredPointer, "m_pPointTo", 4)
			if fg_IsValidSBValue(PointTo):
				return fg_GetValueAsUnsigned(PointTo)

		return fg_FunctionReadPointer(_ValueObject, Address)

	if fg_FunctionVTableBits(_ValueObject) == 1:
		return fg_FunctionReadPointer(_ValueObject, Address)

	return Address

def fg_FunctionStoredFunctorValue(_ValueObject, _TypeName):
	CallInfo = fg_FunctionCallInfo(_ValueObject)
	if CallInfo is None:
		return None

	Type = CallInfo.get("FunctorType", None)
	if not fg_FunctionIsValidSBType(Type):
		return None

	Type = fg_GetValidCanonicalType(Type)
	if Type is None or not Type.IsValid():
		return None

	Address = fg_FunctionStoredFunctorAddress(_ValueObject, _TypeName, CallInfo)
	if Address is None or Address == 0:
		return None

	return _ValueObject.CreateValueFromAddress("[TempData]", Address, Type)

def fg_FunctionIsEmpty(_ValueObject):
	TypeName = fg_FunctionTypeName(_ValueObject)
	if TypeName.startswith("NMib::NFunction::TCFunctionSmall<"):
		Imp = fg_FunctionSmallImp(_ValueObject)
		return fg_IsValidSBValue(Imp) and Imp.GetType().IsPointerType() and Imp.GetValueAsUnsigned() == 0
	if TypeName.startswith("NMib::NFunction::TCFunctionFastCall<"):
		Imp = fg_FunctionFindChild(_ValueObject, "m_pImpl")
		return fg_IsValidSBValue(Imp) and Imp.GetType().IsPointerType() and Imp.GetValueAsUnsigned() == 0

	if fg_FunctionVTableBits(_ValueObject) == 2:
		return True

	return False

def fg_FunctionLocationFromDeclaration(_Declaration):
	if _Declaration is None or not _Declaration.IsValid():
		return None

	FileSpec = _Declaration.GetFileSpec()
	Line = _Declaration.GetLine()
	if not FileSpec.IsValid() or Line == 0 or Line == 0xffffffff:
		return None

	return "{}:{}".format(str(FileSpec), Line)

def fg_FunctionTypesEqual(_Left, _Right):
	if not fg_FunctionIsValidSBType(_Left) or not fg_FunctionIsValidSBType(_Right):
		return False

	Left = fg_GetValidCanonicalType(_Left)
	Right = fg_GetValidCanonicalType(_Right)
	if not fg_FunctionIsValidSBType(Left) or not fg_FunctionIsValidSBType(Right):
		return False

	return fg_FunctionGetTypeName(Left) == fg_FunctionGetTypeName(Right)

def fg_FunctionMemberFunctionIsConst(_MemberFunction):
	Type = _MemberFunction.GetType()
	if not fg_FunctionIsValidSBType(Type):
		return False

	TypeName = fg_FunctionGetTypeName(Type)
	return TypeName.endswith(" const") or TypeName.endswith(" const noexcept")

def fg_FunctionMemberFunctionMatchesSignature(_MemberFunction, _CallInfo, _bRequireExactMutableQualifier = True):
	SignatureType = _CallInfo.get("SignatureType", None)
	if not fg_FunctionIsValidSBType(SignatureType):
		return True

	MemberType = _MemberFunction.GetType()
	if not fg_FunctionIsValidSBType(MemberType):
		return True

	Qualifier = _CallInfo.get("Qualifier", None)
	if Qualifier == "0" or Qualifier == "1":
		bMemberConst = fg_FunctionMemberFunctionIsConst(_MemberFunction)
		if Qualifier == "1" and not bMemberConst:
			return False
		if Qualifier == "0" and _bRequireExactMutableQualifier and bMemberConst:
			return False

	if not fg_FunctionTypesEqual(MemberType.GetFunctionReturnType(), SignatureType.GetFunctionReturnType()):
		return False

	MemberArguments = MemberType.GetFunctionArgumentTypes()
	SignatureArguments = SignatureType.GetFunctionArgumentTypes()
	SignatureArgumentOffset = _CallInfo.get("SignatureArgumentOffset", 0)
	if MemberArguments.GetSize() != SignatureArguments.GetSize() - SignatureArgumentOffset:
		return False

	for iArgument in range(MemberArguments.GetSize()):
		if not fg_FunctionTypesEqual(MemberArguments.GetTypeAtIndex(iArgument), SignatureArguments.GetTypeAtIndex(iArgument + SignatureArgumentOffset)):
			return False

	return True

def fg_FunctionFunctorLocationFromMemberFunctionsImpl(_ValueObject, _CallInfo, _bRequireExactMutableQualifier):
	FunctorType = _CallInfo.get("FunctorType", None)
	if not fg_FunctionIsValidSBType(FunctorType):
		return None

	for iFunction in range(FunctorType.GetNumberOfMemberFunctions()):
		MemberFunction = FunctorType.GetMemberFunctionAtIndex(iFunction)
		if not MemberFunction.IsValid():
			continue
		if MemberFunction.GetName() != "operator()":
			continue
		if not fg_FunctionMemberFunctionMatchesSignature(MemberFunction, _CallInfo, _bRequireExactMutableQualifier):
			continue
		if not hasattr(MemberFunction, "GetDeclaration"):
			continue

		Location = fg_FunctionLocationFromDeclaration(MemberFunction.GetDeclaration())
		if Location is not None:
			return Location

	return None

def fg_FunctionFunctorLocationFromMemberFunctions(_ValueObject, _CallInfo):
	CacheKey = (fg_FunctionTargetKey(_ValueObject), _CallInfo.get("CallAddress", None), "MemberFunction")
	if CacheKey in g_FunctionLocationCache:
		return g_FunctionLocationCache[CacheKey]

	Location = fg_FunctionFunctorLocationFromMemberFunctionsImpl(_ValueObject, _CallInfo, True)
	if Location is not None:
		g_FunctionLocationCache[CacheKey] = Location
		return Location

	Location = fg_FunctionFunctorLocationFromMemberFunctionsImpl(_ValueObject, _CallInfo, False)
	if Location is not None:
		g_FunctionLocationCache[CacheKey] = Location
		return Location

	g_FunctionLocationCache[CacheKey] = None
	return None

def fg_FunctionFunctorLocationFromTypeDeclaration(_ValueObject, _CallInfo):
	FunctorType = _CallInfo.get("FunctorType", None)
	if not fg_FunctionIsValidSBType(FunctorType) or not hasattr(FunctorType, "GetDeclaration"):
		return None

	CacheKey = (fg_FunctionTargetKey(_ValueObject), _CallInfo.get("FunctorTypeName", None), "TypeDeclaration")
	if CacheKey in g_FunctionLocationCache:
		return g_FunctionLocationCache[CacheKey]

	Location = fg_FunctionLocationFromDeclaration(FunctorType.GetDeclaration())
	g_FunctionLocationCache[CacheKey] = Location
	return Location

def fg_FunctionFunctorLocation(_ValueObject):
	if fg_FunctionIsEmpty(_ValueObject):
		return None

	CallInfo = fg_FunctionCallInfo(_ValueObject)
	if CallInfo is None:
		return None

	Location = fg_FunctionFunctorLocationFromMemberFunctions(_ValueObject, CallInfo)
	if Location is not None:
		return Location

	Location = fg_FunctionFunctorLocationFromTypeDeclaration(_ValueObject, CallInfo)
	if Location is not None:
		return Location

	return CallInfo["FunctorTypeName"]

def fg_FunctionStorage(_ValueObject, _TypeName):
	if _TypeName.startswith("NMib::NFunction::TCFunctionFastCall<"):
		return fg_FunctionFindChild(_ValueObject, "m_pImpl")
	if _TypeName.startswith("NMib::NFunction::TCFunctionSmall<"):
		return fg_FunctionSmallImp(_ValueObject)
	return fg_FunctionFindChild(_ValueObject, "m_Storage")

def fg_SummaryProvider_TCFunction(_Value, dict):
	try:
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		if fg_FunctionIsEmpty(_Value):
			return "Empty"

		Summary = fg_FunctionFunctorLocation(_Value)
		if Summary is not None:
			return Summary

		return ""
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCFunction) error: ', error, ' path: ', _Value.get_expr_path())
		return ""

def fg_AddFunctionSummary(_Debugger, _Type):
	try:
		_Debugger.HandleCommand('type summary add -e -F ' + fg_SummaryProvider_TCFunction.__module__ + '.' + fg_SummaryProvider_TCFunction.__name__ + ' -x "' + _Type + '" -w MibLLDB')
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_AddFunctionSummary) error: ', error)
		return

class CSynthProvider_TCFunction(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return

			self.m_NumExtraChildren = 0
			self.m_Value = None
			self.m_bEmpty = False
			self.m_bShowOriginalChildren = True

			TypeName = self.m_ValueObjectType.GetName()

			if fg_FunctionIsEmpty(self.m_ValueObject):
				self.m_bEmpty = True
				self.m_bValid = True
				return

			StoredFunctorValue = fg_FunctionStoredFunctorValue(self.m_ValueObject, TypeName)
			if fg_IsValidSBValue(StoredFunctorValue):
				fg_PrecacheType(StoredFunctorValue.GetType())

				self.m_Value = fg_GetLeafValue(StoredFunctorValue)
				self.m_DataType = self.m_Value.GetType()
				fg_PrecacheType(self.m_DataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
				self.m_bValid = True
				return
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren and self.m_Value is not None:
			if self.m_bEmpty:
				return fg_GetEmptyValue(self.m_ValueObject)
			else:
				return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

def fg_MibLLDBInit_Function(_Debugger):

	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunction<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionMutable<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionMovable<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCMutableFunction<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCMovableFunction<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionFastCall<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionSmall<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionNoAlloc<.*>$", True)

	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCFunction<.*>$")
	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCFunctionMutable<.*>$")
	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCFunctionMovable<.*>$")
	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCMutableFunction<.*>$")
	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCMovableFunction<.*>$")
	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCFunctionFastCall<.*>$")
	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCFunctionSmall<.*>$")
	fg_AddFunctionSummary(_Debugger, "(^|^const )NMib::NFunction::TCFunctionNoAlloc<.*>$")

	return
