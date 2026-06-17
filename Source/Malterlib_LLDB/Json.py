# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *
from .AVLTree import CSynthProvider_TCAVLTreeAggregate_Node, CSynthProvider_TCAVLTreeAggregate_Iterator, fg_GetAVLTreeOffset

g_JsonCurrentTypeCache = {}
g_JsonVariantTypeCache = {}
g_JsonVariantValueCache = {}
g_JsonVariantActiveValueCache = {}
g_JsonDisplayChildrenCache = {}

gc_EJsonType_Invalid = 0
gc_EJsonType_Object = 6
gc_EJsonType_Array = 7

def fg_JsonIsValidValue(_Value):
	return _Value is not None and _Value.IsValid()

def fg_JsonStructuredPlaceholder(_CurrentType):
	if _CurrentType == gc_EJsonType_Object:
		return "{...}"
	if _CurrentType == gc_EJsonType_Array:
		return "[...]"
	return None

def fg_JsonDisplayChildren(_Value, _bAllowValueChild = False):
	CacheKey = fg_JsonCurrentTypeCacheKey(_Value)
	if CacheKey is not None:
		CacheKey = (CacheKey, _bAllowValueChild)
		Children = g_JsonDisplayChildrenCache.get(CacheKey)
		if Children is not None:
			return Children

	Children = []
	for iChild in range(_Value.GetNumChildren()):
		Child = _Value.GetChildAtIndex(iChild)
		if not fg_JsonIsValidValue(Child):
			continue

		Name = Child.GetName()
		if Name is None or Name == "" or Name == "[Length]" or (Name == "[Value]" and not _bAllowValueChild):
			continue

		Children.append(Child)

	if CacheKey is not None:
		if len(g_JsonDisplayChildrenCache) > 4096:
			g_JsonDisplayChildrenCache.clear()
		g_JsonDisplayChildrenCache[CacheKey] = Children

	return Children

def fg_JsonChildIndex(_Children, _Name):
	for iChild in range(len(_Children)):
		if _Children[iChild].GetName() == _Name:
			return iChild
	return None

def fg_JsonHasStructuredChildren(_Children):
	for Child in _Children:
		Name = Child.GetName()
		if Name is not None and Name.startswith("[") and Name != "[Value]":
			return True
	return False

def fg_JsonDirectChild(_Value, _Name):
	if not fg_JsonIsValidValue(_Value):
		return None

	Value = _Value.GetNonSyntheticValue()
	return Value.GetChildMemberWithName(_Name)

def fg_JsonDirectOrBaseChild(_Value, _Name):
	Child = fg_JsonDirectChild(_Value, _Name)
	if fg_JsonIsValidValue(Child):
		return Child

	Value = _Value.GetNonSyntheticValue()
	if Value.GetNumChildren() == 0:
		return None

	Child = fg_JsonDirectChild(Value.GetChildAtIndex(0), _Name)
	if fg_JsonIsValidValue(Child):
		return Child

	return None

def fg_JsonTypeName(_Value):
	if not fg_JsonIsValidValue(_Value):
		return None

	return _Value.GetTypeName()

def fg_JsonLooksLikeValueType(_TypeName):
	if _TypeName is None:
		return False

	return _TypeName.startswith("NMib::NEncoding::CJson") or _TypeName.startswith("NMib::NEncoding::CEJson") or _TypeName.startswith("NMib::NEncoding::TCJsonValue<") or _TypeName.startswith("NMib::NEncoding::TCEJsonValue<")

def fg_JsonIsValueBaseTypeName(_TypeName):
	return _TypeName is not None and _TypeName.startswith("NMib::NEncoding::NPrivate::TCJsonValueBase<")

def fg_JsonValueBase(_Value):
	if not fg_JsonIsValidValue(_Value):
		return _Value

	TypeName = fg_JsonTypeName(_Value)
	if not fg_JsonLooksLikeValueType(TypeName):
		return _Value

	ValueBase = _Value.GetNonSyntheticValue()
	for iDepth in range(4):
		if not fg_JsonIsValidValue(ValueBase):
			break
		if fg_JsonIsValueBaseTypeName(ValueBase.GetTypeName()):
			return ValueBase
		if ValueBase.GetNumChildren() != 1:
			break
		ValueBase = ValueBase.GetChildAtIndex(0)

	return _Value

def fg_JsonVariantValue(_Value, _Depth = 8):
	if not fg_JsonIsValidValue(_Value) or _Depth <= 0:
		return None

	CacheKey = None
	if _Depth == 8:
		CacheKey = fg_JsonCurrentTypeCacheKey(_Value)
		if CacheKey is not None:
			VariantValue = g_JsonVariantValueCache.get(CacheKey)
			if VariantValue is not None:
				return VariantValue

	Value = fg_JsonValueBase(_Value).GetNonSyntheticValue()
	Storage = fg_JsonDirectChild(Value, 'mp_Storage')
	CurrentType = fg_JsonDirectChild(Storage, 'm_CurrentType')
	if fg_JsonIsValidValue(Storage) and fg_JsonIsValidValue(CurrentType):
		if CacheKey is not None:
			if len(g_JsonVariantValueCache) > 4096:
				g_JsonVariantValueCache.clear()
			g_JsonVariantValueCache[CacheKey] = Value
		return Value

	ValueMember = fg_JsonDirectChild(Value, 'mp_Value')
	if fg_JsonIsValidValue(ValueMember):
		VariantValue = fg_JsonVariantValue(ValueMember, _Depth - 1)
		if fg_JsonIsValidValue(VariantValue):
			if CacheKey is not None:
				if len(g_JsonVariantValueCache) > 4096:
					g_JsonVariantValueCache.clear()
				g_JsonVariantValueCache[CacheKey] = VariantValue
			return VariantValue

	return None

def fg_JsonCurrentType(_Value):
	_Value = fg_JsonValueBase(_Value)
	CacheKey = fg_JsonCurrentTypeCacheKey(_Value)
	if CacheKey is not None:
		CurrentType = g_JsonCurrentTypeCache.get(CacheKey)
		if CurrentType is not None:
			return CurrentType

	VariantValue = fg_JsonVariantValue(_Value)
	if not fg_JsonIsValidValue(VariantValue):
		return None

	Storage = fg_JsonDirectChild(VariantValue, 'mp_Storage')
	CurrentType = fg_JsonDirectChild(Storage, 'm_CurrentType')
	if not fg_JsonIsValidValue(CurrentType):
		return None

	CurrentTypeValue = CurrentType.GetValueAsUnsigned()
	if CacheKey is not None:
		if len(g_JsonCurrentTypeCache) > 4096:
			g_JsonCurrentTypeCache.clear()
		g_JsonCurrentTypeCache[CacheKey] = CurrentTypeValue
	return CurrentTypeValue

def fg_JsonCurrentTypeCacheKey(_Value):
	if not fg_JsonIsValidValue(_Value):
		return None

	Address = fg_GetAddressOf(_Value.GetNonSyntheticValue())
	if Address == 0:
		return None

	Process = _Value.GetProcess()
	ProcessID = Process.GetUniqueID() if Process is not None and Process.IsValid() else 0
	StopID = 0
	if Process is not None and Process.IsValid():
		GetStopID = getattr(Process, "GetStopID", None)
		if GetStopID is not None:
			StopID = GetStopID()

	return (ProcessID, StopID, Address, _Value.GetTypeName())

def fg_JsonVariantTypeCacheKey(_Type):
	if _Type is None or not _Type.IsValid():
		return None

	CanonicalType = _Type.GetCanonicalType()
	if CanonicalType is not None and CanonicalType.IsValid():
		TypeName = CanonicalType.GetName()
		if TypeName is not None:
			return TypeName

	return _Type.GetName()

def fg_JsonVariantIsVoidType(_Type):
	if _Type is None or not _Type.IsValid():
		return False

	CanonicalType = _Type.GetCanonicalType()
	return CanonicalType.IsValid() and CanonicalType.GetName() == "void"

def fg_JsonVariantMemberTypes(_Type):
	CacheKey = fg_JsonVariantTypeCacheKey(_Type)
	if CacheKey is not None:
		MemberTypes = g_JsonVariantTypeCache.get(CacheKey)
		if MemberTypes is not None:
			return MemberTypes

	MemberTypes = fg_VariantMemberTypesFromType(_Type)

	if CacheKey is not None:
		if len(g_JsonVariantTypeCache) > 512:
			g_JsonVariantTypeCache.clear()
		g_JsonVariantTypeCache[CacheKey] = MemberTypes

	return MemberTypes

def fg_JsonVariantStorageAddress(_VariantValue):
	Storage = fg_JsonDirectChild(_VariantValue, 'mp_Storage')
	if not fg_JsonIsValidValue(Storage):
		return 0

	AlignedStorage = fg_JsonDirectChild(Storage, 'm_Aligned')
	if fg_JsonIsValidValue(AlignedStorage):
		return fg_GetAddressOf(AlignedStorage)

	RawStorage = fg_JsonDirectChild(Storage, 'm_Storage')
	if fg_JsonIsValidValue(RawStorage):
		return fg_GetAddressOf(RawStorage)

	return 0

def fg_JsonVariantActiveValue(_Value, _Name = '[TempData]'):
	VariantValue = fg_JsonVariantValue(_Value)
	if not fg_JsonIsValidValue(VariantValue):
		return None

	CacheKey = fg_JsonCurrentTypeCacheKey(VariantValue)
	if CacheKey is not None:
		CacheKey = (CacheKey, _Name)
		Value = g_JsonVariantActiveValueCache.get(CacheKey)
		if Value is not None:
			return Value

	Storage = fg_JsonDirectChild(VariantValue, 'mp_Storage')
	CurrentType = fg_JsonDirectChild(Storage, 'm_CurrentType')
	if not fg_JsonIsValidValue(CurrentType):
		return None

	CurrentTypeValue = CurrentType.GetValueAsUnsigned()
	ValueType = fg_JsonVariantMemberTypes(VariantValue.GetType()).get(CurrentTypeValue)
	if ValueType is None or not ValueType.IsValid() or fg_JsonVariantIsVoidType(ValueType):
		return None

	DataAddress = fg_JsonVariantStorageAddress(VariantValue)
	if DataAddress == 0:
		return None

	Value = VariantValue.CreateValueFromAddress(_Name, DataAddress, ValueType)
	if CacheKey is not None:
		if len(g_JsonVariantActiveValueCache) > 4096:
			g_JsonVariantActiveValueCache.clear()
		g_JsonVariantActiveValueCache[CacheKey] = Value
	return Value

def fg_JsonSummaryFromValue(_Value, _OpenBracket = "{", _CloseBracket = "}"):
	if not fg_JsonIsValidValue(_Value):
		return None

	if _Value.GetType().IsPointerType():
		PointerValue = _Value.GetValueAsUnsigned()
		if PointerValue == 0:
			return "nullptr"

		Deref = _Value.Dereference()
		Summary = Deref.GetSummary()
		if Summary is not None:
			return hex(PointerValue) + '   ' + Summary

		Value = Deref.GetValue()
		if Value is not None:
			return hex(PointerValue) + '   ' + str(Value)
	else:
		Summary = _Value.GetSummary()
		if Summary is not None:
			return Summary

		Value = _Value.GetValue()
		if Value is not None:
			return str(Value)

	ReturnString = _OpenBracket + ' '
	Overflow = False
	AddedFirst = False
	for iChild in range(_Value.GetNumChildren()):
		Child = _Value.GetChildAtIndex(iChild)
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
				ReturnString += ', '

			AddedFirst = True
			ReturnString += Child.GetName() + ' = ' + Summary

	if not AddedFirst:
		return _OpenBracket + _CloseBracket

	if Overflow:
		ReturnString += ', ... ' + _CloseBracket
	else:
		ReturnString += ' ' + _CloseBracket

	return ReturnString

def fg_JsonNormalizedTypeName(_Value):
	TypeName = fg_JsonTypeName(_Value)
	if TypeName is not None and TypeName.startswith("const "):
		return TypeName[6:]
	return TypeName

def fg_JsonPreviewValueSummary(_Value):
	TypeName = fg_JsonNormalizedTypeName(_Value)
	if TypeName is not None:
		if (TypeName.startswith("NMib::NContainer::TCMapNode<") or TypeName.startswith("NMib::NContainer::TCDestructiveMapNode<")) and "NMib::NEncoding::NPrivate::TCObjectEntry<" in TypeName:
			return fg_SummaryProvider_TCJsonObjectMapNode(_Value, {})
		if TypeName.startswith("NMib::NEncoding::NPrivate::TCObjectEntry<"):
			return fg_SummaryProvider_TCObjectEntry(_Value, {})

	return _Value.GetSummary()

def fg_JsonCollectionPreviewFromValues(_Values, _bMayHaveMore, _OpenBracket, _CloseBracket):
	Parts = []
	for Value in _Values:
		if not fg_JsonIsValidValue(Value):
			continue

		Summary = fg_JsonPreviewValueSummary(Value)
		if Summary == "":
			Summary = fg_JsonStructuredPlaceholder(fg_JsonCurrentType(Value))
		if Summary is None:
			Summary = Value.GetValue()
		if Summary == "None":
			Summary = "..."
		if Summary is None:
			continue

		Parts.append(str(Summary))

	if not Parts:
		if _bMayHaveMore:
			return _OpenBracket + "..." + _CloseBracket
		return _OpenBracket + _CloseBracket

	Summary = _OpenBracket + " " + ", ".join(Parts)
	if _bMayHaveMore:
		Summary += ", ..."
	Summary += " " + _CloseBracket
	return Summary

def fg_JsonObjectPreviewFromValues(_Values, _bMayHaveMore):
	return fg_JsonCollectionPreviewFromValues(_Values, _bMayHaveMore, "{", "}")

def fg_JsonArrayPreviewFromValues(_Values, _bMayHaveMore):
	return fg_JsonCollectionPreviewFromValues(_Values, _bMayHaveMore, "[", "]")

def fg_JsonVectorPreview(_VectorValue, _MaxEntries, _OpenBracket, _CloseBracket, _bNullDataIsEmpty = False):
	if not fg_JsonIsValidValue(_VectorValue):
		return None

	VectorValue = _VectorValue.GetNonSyntheticValue()
	VectorType = fg_GetValueType(VectorValue)
	VectorTypeName = VectorType.GetName()
	if VectorTypeName is None or not VectorTypeName.startswith("NMib::NContainer::TCVector<"):
		return None
	if VectorType.GetNumberOfTemplateArguments() == 0:
		return None

	DataType = fg_GetValidCanonicalType(VectorType.GetTemplateArgumentType(0))
	if not DataType.IsValid():
		return None

	StaticData = fg_JsonDirectChild(VectorValue, 'mp_StaticData')
	pData = fg_JsonDirectChild(StaticData, 'm_pData')
	if not fg_JsonIsValidValue(pData):
		return None
	if pData.GetValueAsUnsigned() == 0:
		if _bNullDataIsEmpty:
			return fg_JsonCollectionPreviewFromValues([], False, _OpenBracket, _CloseBracket)
		return None

	Data = pData.Dereference()
	LengthValue = fg_JsonDirectChild(Data, 'm_Length')
	if not fg_JsonIsValidValue(LengthValue):
		return None

	nEntries = LengthValue.GetValueAsUnsigned()
	pDataAddress = pData.GetValueAsUnsigned() + pData.GetType().GetPointeeType().GetByteSize()
	DataSize = DataType.GetByteSize()
	Values = []
	for iEntry in range(min(_MaxEntries, nEntries)):
		Values.append(VectorValue.CreateValueFromAddress('[' + str(iEntry) + ']', pDataAddress + DataSize * iEntry, DataType))

	return fg_JsonCollectionPreviewFromValues(Values, nEntries > _MaxEntries, _OpenBracket, _CloseBracket)

def fg_JsonObjectVectorPreview(_VectorValue, _MaxEntries):
	return fg_JsonVectorPreview(_VectorValue, _MaxEntries, "{", "}", True)

def fg_JsonArrayVectorPreview(_VectorValue, _MaxEntries):
	return fg_JsonVectorPreview(_VectorValue, _MaxEntries, "[", "]", True)

def fg_JsonArraySummary(_JsonValue, _MaxEntries):
	ArraySummary = fg_JsonArrayVectorPreview(fg_JsonVariantActiveValue(_JsonValue, '[Value]'), _MaxEntries)
	if ArraySummary is not None:
		return ArraySummary
	return fg_JsonStructuredPlaceholder(gc_EJsonType_Array)

def fg_JsonObjectSummaryFromRoot(_Root):
	if not fg_JsonIsValidValue(_Root):
		return None
	if _Root.GetValueAsUnsigned() == 0:
		return "{}"
	return "{...}"

def fg_JsonObjectTreePreview(_TreeValue, _MaxEntries):
	if not fg_JsonIsValidValue(_TreeValue):
		return None

	TreeValue = _TreeValue.GetNonSyntheticValue()
	TreeType = fg_GetValueType(TreeValue)
	if TreeType.GetNumberOfTemplateArguments() < 4:
		return None

	Root = fg_JsonDirectChild(TreeValue, 'm_Root')

	DataType = fg_GetValidCanonicalType(TreeType.GetTemplateArgumentType(3))
	return fg_JsonObjectAVLPreview(TreeValue, Root, TreeType, DataType, _MaxEntries)

def fg_JsonObjectAVLPreview(_Value, _Root, _TreeType, _DataType, _MaxEntries):
	RootSummary = fg_JsonObjectSummaryFromRoot(_Root)
	if RootSummary is None:
		return None
	if RootSummary == "{}":
		return RootSummary
	if _MaxEntries == 0:
		return RootSummary

	NodeType = _Root.GetType().GetPointeeType().GetUnqualifiedType()
	NodeType = fg_GetValidCanonicalType(NodeType)
	Offset = fg_GetAVLTreeOffset(_TreeType, _DataType, NodeType)
	if Offset is None:
		return None

	RootNode = _Value.CreateValueFromAddress('[TempData]', (_Root.GetValueAsUnsigned() >> 2) << 2, NodeType).AddressOf()
	Iterator = CSynthProvider_TCAVLTreeAggregate_Iterator(CSynthProvider_TCAVLTreeAggregate_Node(RootNode, NodeType))
	Values = []
	Max = [_MaxEntries * 8 + 8]
	while Iterator.f_IsValid() and len(Values) < _MaxEntries:
		Address = Iterator.f_Node().m_Value
		if Address is not None and Address >= Offset:
			Values.append(fg_CreateDynamicValue(_Value, '[' + str(len(Values)) + ']', Address - Offset, _DataType))
		if not Iterator.f_Next(Max):
			break

	return fg_JsonObjectPreviewFromValues(Values, Iterator.f_IsValid())

def fg_JsonObjectMapPreview(_MapValue, _MaxEntries):
	if not fg_JsonIsValidValue(_MapValue):
		return None

	MapValue = _MapValue.GetNonSyntheticValue()
	Tree = fg_JsonDirectChild(MapValue, 'mp_Tree')
	if not fg_JsonIsValidValue(Tree):
		return None

	Root = fg_JsonDirectChild(Tree, 'm_Root')
	TreeType = fg_GetInheritedType(fg_GetValueType(Tree), 'NMib::NIntrusive::TCAVLTreeAggregate')
	if TreeType is None or not TreeType.IsValid() or TreeType.GetNumberOfTemplateArguments() < 4:
		return fg_JsonObjectSummaryFromRoot(Root)

	DataType = fg_GetValidCanonicalType(TreeType.GetTemplateArgumentType(3))
	return fg_JsonObjectAVLPreview(MapValue, Root, TreeType, DataType, _MaxEntries)

def fg_JsonObjectMapPlaceholder(_MapValue):
	if not fg_JsonIsValidValue(_MapValue):
		return None

	Tree = fg_JsonDirectChild(_MapValue, 'mp_Tree')
	Root = fg_JsonDirectChild(Tree, 'm_Root')
	return fg_JsonObjectSummaryFromRoot(Root)

def fg_JsonObjectSummaryFromObject(_ObjectValue, _MaxEntries):
	if not fg_JsonIsValidValue(_ObjectValue):
		return None

	ObjectsMember = fg_JsonDirectChild(_ObjectValue, 'mp_Objects')
	if fg_JsonIsValidValue(ObjectsMember):
		ObjectsSummary = fg_JsonObjectVectorPreview(ObjectsMember, _MaxEntries)
		if ObjectsSummary is not None:
			return ObjectsSummary
		ObjectsSummary = fg_JsonObjectMapPreview(ObjectsMember, _MaxEntries)
		if ObjectsSummary is not None:
			return ObjectsSummary
		ObjectsSummary = fg_JsonObjectMapPlaceholder(ObjectsMember)
		if ObjectsSummary is not None:
			return ObjectsSummary

	ObjectsMember = fg_JsonDirectChild(_ObjectValue, 'mp_ObjectTree')
	if fg_JsonIsValidValue(ObjectsMember):
		ObjectsSummary = fg_JsonObjectTreePreview(ObjectsMember, _MaxEntries)
		if ObjectsSummary is not None:
			return ObjectsSummary

	return None

def fg_JsonObjectSummary(_JsonValue, _MaxEntries):
	ObjectSummary = fg_JsonObjectSummaryFromObject(fg_JsonVariantActiveValue(_JsonValue, '[Value]'), _MaxEntries)
	if ObjectSummary is not None:
		return ObjectSummary
	return fg_JsonStructuredPlaceholder(gc_EJsonType_Object)

def fg_JsonMapNodeMember(_Value, _Name):
	return fg_JsonDirectOrBaseChild(_Value, _Name)

def fg_JsonObjectEntryMember(_Value, _Name):
	return fg_JsonDirectOrBaseChild(_Value, _Name)

class CSynthProvider_TCJsonObjectMapNode(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_bHasKey = False
		self.m_bHasValue = False
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return

			self.m_Key = fg_JsonMapNodeMember(self.m_ValueObject, 'mp_Key')
			if not fg_JsonIsValidValue(self.m_Key):
				self.m_Key = fg_JsonMapNodeMember(self.m_ValueObject, 'm_Key')
			self.m_bHasKey = fg_JsonIsValidValue(self.m_Key)
			if self.m_bHasKey:
				self.m_KeyType = self.m_Key.GetType()

			ValueEntry = fg_JsonMapNodeMember(self.m_ValueObject, 'mp_Value')
			if not fg_JsonIsValidValue(ValueEntry):
				ValueEntry = fg_JsonMapNodeMember(self.m_ValueObject, 'm_Value')
			self.m_Value = fg_JsonDirectChild(ValueEntry, 'mp_Value')
			if not fg_JsonIsValidValue(self.m_Value):
				self.m_Value = ValueEntry
			self.m_bHasValue = fg_JsonIsValidValue(self.m_Value)
			if self.m_bHasValue:
				self.m_ValueType = self.m_Value.GetType()

			self.m_bValid = self.m_bHasKey or self.m_bHasValue
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if self.m_bHasKey and _Name == '[Key]':
			return 0
		if self.m_bHasValue and _Name == '[Value]':
			return 1 if self.m_bHasKey else 0
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0 and self.m_bHasKey:
			return self.m_ValueObject.CreateValueFromAddress('[Key]', fg_GetAddressOf(self.m_Key), self.m_KeyType)
		elif _iChild == (1 if self.m_bHasKey else 0) and self.m_bHasValue:
			return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_ValueType)
		return None

	def fp_NumChildren(self):
		return (1 if self.m_bHasKey else 0) + (1 if self.m_bHasValue else 0)

def fg_SummaryProvider_TCJsonObjectMapNode(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		KeyMember = fg_JsonMapNodeMember(_Value, 'mp_Key')
		if not fg_JsonIsValidValue(KeyMember):
			KeyMember = fg_JsonMapNodeMember(_Value, 'm_Key')

		KeySummary = None
		if fg_JsonIsValidValue(KeyMember):
			KeySummary = KeyMember.GetSummary()
			if KeySummary is None:
				KeySummary = KeyMember.GetValue()

		ValueEntry = fg_JsonMapNodeMember(_Value, 'mp_Value')
		if not fg_JsonIsValidValue(ValueEntry):
			ValueEntry = fg_JsonMapNodeMember(_Value, 'm_Value')

		ValueSummary = None
		if fg_JsonIsValidValue(ValueEntry):
			ValueSummary = fg_JsonPreviewValueSummary(ValueEntry)
			if ValueSummary is None:
				ValueSummary = ValueEntry.GetValue()
			if ValueSummary == "None":
				ValueSummary = "..."

		if KeySummary is None:
			return ValueSummary
		if ValueSummary is None:
			return KeySummary
		return KeySummary + ' > ' + ValueSummary

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_TCJsonObjectMapNode) error: ', error, ' path: ', _Value.get_expr_path())
		return

class CSynthProvider_TCJsonValueBase(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		self.m_Children = []
		self.m_bShowValueChild = True
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NEncoding::NPrivate::TCJsonValueBase")

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return
			self.m_NumExtraChildren = 0

			self.m_Value = self.m_ValueObject.GetChildMemberWithName('mp_Value')
			CurrentType = fg_JsonCurrentType(self.m_ValueObject)

			if CurrentType == gc_EJsonType_Invalid:
				self.m_bEmpty = True
				self.m_bValid = True
				return;

			self.m_bEmpty = False

			self.m_Value = fg_JsonVariantActiveValue(self.m_ValueObject)
			if not fg_JsonIsValidValue(self.m_Value):
				return
			self.m_DataType = self.m_Value.GetType()
			fg_PrecacheType(self.m_DataType)

			if CurrentType == gc_EJsonType_Object or CurrentType == gc_EJsonType_Array:
				self.m_Children = fg_JsonDisplayChildren(self.m_Value)
				self.m_bShowValueChild = False
				self.m_NumExtraChildren = len(self.m_Children)
				self.m_bValid = True
				return

			self.m_Children = fg_JsonDisplayChildren(self.m_Value, True)
			self.m_bShowValueChild = not fg_JsonHasStructuredChildren(self.m_Children)
			if self.m_bShowValueChild:
				self.m_Children = []
			self.m_NumExtraChildren = len(self.m_Children)
			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if not self.m_bEmpty and self.m_bShowValueChild and _Name == '[Value]':
			return self.m_NumExtraChildren
		ChildIndex = fg_JsonChildIndex(self.m_Children, _Name)
		if ChildIndex is not None:
			return ChildIndex
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren and not self.m_bEmpty and self.m_bShowValueChild:
			return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Children[_iChild]
		return None

	def fp_NumChildren(self):
		if not self.m_bEmpty and self.m_bShowValueChild:
			return 1 + self.m_NumExtraChildren
		return self.m_NumExtraChildren

class CSynthProvider_TCJsonObject(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		self.m_Children = None
		self.m_bShowValueChild = True
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NEncoding::TCJsonObject")

	def fp_EnsureChildren(self):
		if self.m_Children is not None:
			return

		self.m_Children = fg_JsonDisplayChildren(self.m_Value)
		self.m_NumExtraChildren = len(self.m_Children)
		self.m_bShowValueChild = self.m_NumExtraChildren == 0

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return
			self.m_NumExtraChildren = 0

			self.m_Value = self.m_ValueObject.GetChildMemberWithName('mp_Objects')
			if not fg_JsonIsValidValue(self.m_Value):
				self.m_Value = self.m_ValueObject.GetChildMemberWithName('mp_ObjectTree')
			if not fg_JsonIsValidValue(self.m_Value):
				return
			self.m_Value = self.m_Value.CreateValueFromAddress("[TempData]", fg_GetValueAddress(self.m_Value), fg_GetValidCanonicalType(self.m_Value.GetType()))

			fg_PrecacheType(self.m_Value.GetType())

			self.m_DataType = self.m_Value.GetType()
			fg_PrecacheType(self.m_DataType)
			self.m_Children = None
			self.m_bShowValueChild = True
			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		self.fp_EnsureChildren()
		if self.m_bShowValueChild and _Name == '[Value]':
			return self.m_NumExtraChildren
		ChildIndex = fg_JsonChildIndex(self.m_Children, _Name)
		if ChildIndex is not None:
			return ChildIndex
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		self.fp_EnsureChildren()
		if _iChild == self.m_NumExtraChildren and self.m_bShowValueChild:
			return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Children[_iChild]
		return None

	def fp_NumChildren(self):
		self.fp_EnsureChildren()
		if self.m_bShowValueChild:
			return 1 + self.m_NumExtraChildren
		return self.m_NumExtraChildren

class CSynthProvider_TCObjectEntry(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_bHasNameValue = False
		self.m_bHasValue = False
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NEncoding::NPrivate::TCObjectEntry")

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return

			self.m_NameValue = fg_JsonObjectEntryMember(self.m_ValueObject, 'mp_Name')
			self.m_bHasNameValue = fg_JsonIsValidValue(self.m_NameValue)
			if self.m_bHasNameValue:
				self.m_NameValueDataType = self.m_NameValue.GetType()

			self.m_Value = fg_JsonObjectEntryMember(self.m_ValueObject, 'mp_Value')
			self.m_bHasValue = fg_JsonIsValidValue(self.m_Value)
			if self.m_bHasValue:
				self.m_DataType = self.m_Value.GetType()
				fg_PrecacheType(self.m_DataType)

			self.m_bValid = self.m_bHasNameValue or self.m_bHasValue
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if self.m_bHasNameValue and _Name == '[Key]':
			return 0
		if self.m_bHasValue and _Name == '[Value]':
			return 1 if self.m_bHasNameValue else 0
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0 and self.m_bHasNameValue:
			return self.m_ValueObject.CreateValueFromAddress('[Key]', fg_GetAddressOf(self.m_NameValue), self.m_NameValueDataType)
		elif _iChild == (1 if self.m_bHasNameValue else 0) and self.m_bHasValue:
			return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		return None

	def fp_NumChildren(self):
		return (1 if self.m_bHasNameValue else 0) + (1 if self.m_bHasValue else 0)

def fg_SummaryProvider_TCObjectEntry(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		NonSynthValue = _Value.GetNonSyntheticValue()
		KeyMember = fg_JsonObjectEntryMember(NonSynthValue, 'mp_Name')
		KeySummary = None
		if fg_JsonIsValidValue(KeyMember):
			KeySummary = KeyMember.GetSummary()
			if KeySummary is None:
				KeyValue = KeyMember.GetValue()
				if KeyValue is not None:
					KeySummary = str(KeyValue)


		ValueMember = NonSynthValue.GetChildMemberWithName('mp_Value')
		CurrentType = fg_JsonCurrentType(NonSynthValue)
		if CurrentType == gc_EJsonType_Invalid:
			ValueSummary = "Invalid"
			if KeySummary is None:
				Value = ValueSummary
			else:
				Value = KeySummary + ' > ' + ValueSummary
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + '   ' + Value
			return Value
		if CurrentType == gc_EJsonType_Array:
			ValueSummary = fg_JsonArraySummary(NonSynthValue, 0)
		elif CurrentType == gc_EJsonType_Object:
			ValueSummary = fg_JsonObjectSummary(NonSynthValue, 0)
		else:
			ValueSummary = fg_JsonStructuredPlaceholder(CurrentType)
		if ValueSummary is not None:
			if KeySummary is None:
				Value = ValueSummary
			else:
				Value = KeySummary + ' > ' + ValueSummary
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + '   ' + Value
			return Value

		ValueMember = fg_JsonVariantActiveValue(NonSynthValue, '[Value]')

		if ValueMember is None or not ValueMember.IsValid():
			Value = KeySummary;
		else:
			ValueSummary = fg_JsonSummaryFromValue(ValueMember)

			if ValueSummary == "None":
				ValueSummary = "..."

			if KeySummary is None:
				if ValueSummary is None:
					return None
				else:
					Value = ValueSummary
			else:
				if ValueSummary is None:
					Value = KeySummary + ' > ?'
				else:
					Value = KeySummary + ' > ' + ValueSummary

		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + '   ' + Value
		return Value

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_TCObjectEntry) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_TCJsonValueBase(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		CurrentType = fg_JsonCurrentType(_Value)
		if CurrentType == gc_EJsonType_Invalid:
			return "Invalid"
		if CurrentType == gc_EJsonType_Object:
			return fg_JsonObjectSummary(_Value, 3)
		if CurrentType == gc_EJsonType_Array:
			return fg_JsonArraySummary(_Value, 3)
		return fg_JsonSummaryFromValue(fg_JsonVariantActiveValue(_Value, '[Value]'))

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_TCJsonValueBase) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_TCJsonObject(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		ObjectsSummary = fg_JsonObjectSummaryFromObject(_Value, 3)
		if ObjectsSummary is not None:
			return ObjectsSummary

		return "{...}"

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_TCJsonObject) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CEJsonUserType(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		ObjectsMember = fg_JsonDirectChild(_Value, 'm_Type')
		if ObjectsMember is not None:
			ObjectSummary = fg_GetValueRawSummary(ObjectsMember)
			if ObjectSummary is not None:
				return "UserType(" + ObjectSummary + ")"

		return "UserType"

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CEJsonUserType) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CJsonBoolean(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		ObjectsMember = fg_JsonDirectChild(_Value, 'm_bValue')
		if ObjectsMember.GetValueAsUnsigned():
			return "true"
		else:
			return "false"

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CJsonBoolean) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CJsonNull(_Value, dict):
	try:
		return "null";

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CJsonNull) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_Json(_Debugger):
	fg_AddSynth(_Debugger, CSynthProvider_TCJsonValueBase, "(^|^const )NMib::NEncoding::TCJsonValue<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCJsonValueBase, "(^|^const )NMib::NEncoding::TCEJsonValue<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCJsonValueBase, "(^|^const )NMib::NEncoding::TCJsonValue<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCJsonValueBase, "(^|^const )NMib::NEncoding::TCEJsonValue<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCObjectEntry, "(^|^const )NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCObjectEntry, "(^|^const )NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCJsonObjectMapNode, "(^|^const )NMib::NContainer::TCMapNode<.*, NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCJsonObjectMapNode, "(^|^const )NMib::NContainer::TCDestructiveMapNode<.*, NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCJsonObjectMapNode, "(^|^const )NMib::NContainer::TCMapNode<.*, NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCJsonObjectMapNode, "(^|^const )NMib::NContainer::TCDestructiveMapNode<.*, NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCJsonObject, "(^|^const )NMib::NEncoding::TCJsonObject<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCJsonObject, "(^|^const )NMib::NEncoding::TCJsonObject<.*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_CJsonBoolean, "(^|^const )NMib::NEncoding::NPrivate::CJsonBoolean$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CJsonNull, "(^|^const )NMib::NEncoding::NPrivate::CJsonNull$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CEJsonUserType, "(^|^const )NMib::NEncoding::CEJsonUserTypeSorted$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CEJsonUserType, "(^|^const )NMib::NEncoding::CEJsonUserTypeOrdered$", True)


	return
