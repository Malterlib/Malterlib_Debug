# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_AVLTypeName(_Type):
	if _Type is None or not _Type.IsValid():
		return None

	Type = fg_GetValidCanonicalType(_Type).GetUnqualifiedType()
	if Type is None or not Type.IsValid():
		return None

	return Type.GetName()

def fg_NormalizeTypeName(_TypeName):
	if _TypeName is None:
		return None

	return ''.join(_TypeName.split())

def fg_AVLTypesEqual(_Type0, _Type1):
	TypeName0 = fg_NormalizeTypeName(fg_AVLTypeName(_Type0))
	TypeName1 = fg_NormalizeTypeName(fg_AVLTypeName(_Type1))
	return TypeName0 is not None and TypeName0 == TypeName1

def fg_GetAVLIntegralTemplateArgument(_Type):
	Target = lldb.target
	if Target is None or not hasattr(_Type, 'GetTemplateArgumentValue') or _Type.GetNumberOfTemplateArguments() == 0:
		return None

	Value = _Type.GetTemplateArgumentValue(Target, 0)
	if fg_IsValidSBValue(Value) and Value.GetValue() is not None:
		return Value.GetValueAsUnsigned()

	return None

def fg_GetAVLLinkContainerType(_TreeType):
	if _TreeType.GetNumberOfTemplateArguments() == 0:
		return None

	MemberPointerType = _TreeType.GetTemplateArgumentType(0)
	if not MemberPointerType.IsValid():
		return None

	LinkContainerType = MemberPointerType.GetPointeeType()
	if not LinkContainerType.IsValid():
		return None

	return fg_GetValidCanonicalType(LinkContainerType)

def fg_GetAVLFieldOffsets(_Type, _WantedType, _BaseOffset = 0, _Depth = 0):
	if _Depth >= 8:
		return []

	Type = fg_GetValidCanonicalType(_Type).GetUnqualifiedType()
	if not Type.IsValid():
		return []

	Offsets = []
	for iField in range(0, Type.GetNumberOfFields()):
		Field = Type.GetFieldAtIndex(iField)
		if fg_AVLTypesEqual(Field.GetType(), _WantedType):
			Offsets.append((_BaseOffset + Field.GetOffsetInBytes(), Field.GetName()))

	for iBase in range(0, Type.GetNumberOfDirectBaseClasses()):
		Base = Type.GetDirectBaseClassAtIndex(iBase)
		Offsets += fg_GetAVLFieldOffsets(Base.GetType(), _WantedType, _BaseOffset + Base.GetOffsetInBytes(), _Depth + 1)

	return Offsets

def fg_GetAVLInnerLinkOffsets(_LinkContainerType, _NodeType, _BaseOffset = 0, _Depth = 0):
	if _Depth >= 8:
		return []

	Type = fg_GetValidCanonicalType(_LinkContainerType).GetUnqualifiedType()
	if not Type.IsValid():
		return []

	if fg_AVLTypesEqual(Type, _NodeType):
		return [(_BaseOffset, None)]

	Offsets = []
	for iField in range(0, Type.GetNumberOfFields()):
		Field = Type.GetFieldAtIndex(iField)
		if Field.GetName() == 'm_Link' and fg_AVLTypesEqual(Field.GetType(), _NodeType):
			Offsets.append((_BaseOffset + Field.GetOffsetInBytes(), Field.GetName()))

	for iBase in range(0, Type.GetNumberOfDirectBaseClasses()):
		Base = Type.GetDirectBaseClassAtIndex(iBase)
		Offsets += fg_GetAVLInnerLinkOffsets(Base.GetType(), _NodeType, _BaseOffset + Base.GetOffsetInBytes(), _Depth + 1)

	return Offsets

def fg_GetAVLLinkOffsets(_DataType, _NodeType, _BaseOffset = 0, _Depth = 0):
	if _Depth >= 8:
		return []

	Type = fg_GetValidCanonicalType(_DataType).GetUnqualifiedType()
	if not Type.IsValid():
		return []

	Offsets = []
	for iField in range(0, Type.GetNumberOfFields()):
		Field = Type.GetFieldAtIndex(iField)
		InnerOffsets = fg_GetAVLInnerLinkOffsets(Field.GetType(), _NodeType)
		for InnerOffset, FieldName in InnerOffsets:
			Offsets.append((_BaseOffset + Field.GetOffsetInBytes() + InnerOffset, Field.GetName(), FieldName))

	for iBase in range(0, Type.GetNumberOfDirectBaseClasses()):
		Base = Type.GetDirectBaseClassAtIndex(iBase)
		Offsets += fg_GetAVLLinkOffsets(Base.GetType(), _NodeType, _BaseOffset + Base.GetOffsetInBytes(), _Depth + 1)

	return Offsets

def fg_GetAVLTreeOffset(_TreeType, _DataType, _NodeType):
	Offset = fg_GetAVLIntegralTemplateArgument(_TreeType)
	if Offset is not None:
		return Offset

	LinkContainerType = fg_GetAVLLinkContainerType(_TreeType)
	if LinkContainerType is not None:
		MemberOffsets = fg_GetAVLFieldOffsets(_DataType, LinkContainerType)
		InnerOffsets = fg_GetAVLInnerLinkOffsets(LinkContainerType, _NodeType)
		if len(MemberOffsets) == 1 and len(InnerOffsets) == 1:
			return MemberOffsets[0][0] + InnerOffsets[0][0]

	Offsets = fg_GetAVLLinkOffsets(_DataType, _NodeType)
	if len(Offsets) == 1:
		return Offsets[0][0]

	return None

class CSynthProvider_TCAVLTreeAggregate_Node:
	def fp_Left(self):
		return CSynthProvider_TCAVLTreeAggregate_Node(self.fp_GetNode((self.m_Node.GetChildMemberWithName('m_pNext').GetChildAtIndex(0).GetValueAsUnsigned(0) >> 2) << 2).AddressOf(), self.m_NodeType)

	def fp_Right(self):
		return CSynthProvider_TCAVLTreeAggregate_Node(self.fp_GetNode((self.m_Node.GetChildMemberWithName('m_pNext').GetChildAtIndex(1).GetValueAsUnsigned(0) >> 2) << 2).AddressOf(), self.m_NodeType)

	def fp_GetNode(self, _pNodePointer):
		return fg_CreateDynamicValue(self.m_Node, '[TempData]', _pNodePointer, self.m_NodeType)

	def fp_Value(self):
		return self.m_Node.GetValueAsUnsigned(0)

	def fp_SBValue(self):
		return self.m_Node

	def fp_IsNull(self):
		return self.m_Value == 0

	def __init__(self, _Node, _NodeType):
		self.m_Node = _Node
		self.m_NodeType = _NodeType

	m_Left = property(fp_Left,None)
	m_Right = property(fp_Right,None)
	m_Value = property(fp_Value,None)
	m_IsNull = property(fp_IsNull,None)
	m_SBValue = property(fp_SBValue,None)

class CSynthProvider_TCAVLTreeAggregate_Iterator:

	def __init__(self, _pNode):
		pNode = _pNode
		self.m_pStack = []
		self.m_Position = 0

		Depth = 0
		while pNode.m_Value != 0:
			self.m_pStack.append(pNode)
			pNode = pNode.m_Left
			Depth = Depth + 1
			if Depth > 16:
				break;

	def f_Next(self, _Max):
		if len(self.m_pStack) == 0:
			return False

		if _Max[0] <= 0:
			return False

		self.m_Position = self.m_Position + 1
		pCurrent = self.m_pStack.pop()
		pCurrent = pCurrent.m_Right

		_Max[0] = _Max[0] - 1
		if _Max[0] <= 0:
			return False

		while pCurrent.m_Value != 0:
			self.m_pStack.append(pCurrent)
			pCurrent = pCurrent.m_Left
			_Max[0] = _Max[0] - 1
			if _Max[0] <= 0:
				return False

		return True

	def f_Advance(self, _nSteps, _Max):
		for iOriginalChild in range(0, _nSteps):
			if not self.f_Next([_Max]):
				return

	def f_Position(self):
		return self.m_Position

	def f_Node(self):
		return self.m_pStack[-1]

	def f_IsValid(self):
		return len(self.m_pStack) != 0

class CSynthProvider_TCAVLTreeAggregate(CSynthProvider_Container):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary, 'NMib::NIntrusive::TCAVLTreeAggregate')

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Root = self.m_ValueObject.GetValueForExpressionPath('.m_Root')

			if not self.fp_ExtractType():
				return

			self.m_Root = self.m_ValueObject.CreateValueFromAddress('[TempData]', (self.m_Root.GetValueAsUnsigned() >> 2) << 2, self.m_NodeType).AddressOf()

			self.m_DataSize = self.m_DataType.GetByteSize()

			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ContainerGetChildAtIndex(self, _iChild):
		Address = self.m_ChildMap[_iChild]
		if Address is None or Address < self.m_Offset:
			return None

		RetValue = fg_CreateDynamicValue(self.m_ValueObject, '[' + str(_iChild) + ']', Address - self.m_Offset, self.m_DataType)
		return RetValue

	def fp_ExtractType(self):

		ValueType = self.m_ValueObjectType;
		if not ValueType.IsValid() or ValueType.IsPointerType():
			return False

		DataType = self.m_ValueObjectType.GetTemplateArgumentType(3)
		DataType = fg_GetValidCanonicalType(DataType)

		NodeType = self.m_Root.GetType().GetPointeeType().GetUnqualifiedType()
		NodeType = fg_GetValidCanonicalType(NodeType)

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)

		self.m_DataType = DataType
		self.m_NodeType = NodeType
		self.m_Offset = fg_GetAVLTreeOffset(self.m_ValueObjectType, DataType, NodeType)
		if self.m_Offset is None:
			return False

		return True

	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren
		pNode = CSynthProvider_TCAVLTreeAggregate_Node(self.m_Root, self.m_NodeType)
		iNode = CSynthProvider_TCAVLTreeAggregate_Iterator(pNode)
		Max = [g_MaxSynthChildren * 2]
		nChildren = 0
		self.m_ChildMap = []
		while iNode.f_IsValid():
			self.m_ChildMap.append(iNode.f_Node().m_Value)
			nChildren = nChildren + 1
			if nChildren >= g_MaxSynthChildren:
				nChildren = g_MaxSynthChildren
				break
			iNode.f_Next(Max)

		return nChildren;

class CSynthProvider_TCAVLTreeAggregate_CIterator(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_pStack = self.m_ValueObject.GetChildMemberWithName('m_pStack')
			self.m_iStack = self.m_ValueObject.GetChildMemberWithName('m_iStack')
			if not fg_IsValidSBValue(self.m_iStack):
				return
			if not self.fp_ExtractType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = None
			self.m_bEmpty = True
			if self.m_iStack.GetValueAsSigned() >= 0:
				Address = fg_GetValueAsUnsigned(self.m_pStack.GetChildAtIndex(fg_GetValueAsUnsigned(self.m_iStack)%92))
				if Address >= self.m_Offset:
					self.m_bEmpty = False
					self.m_Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', Address - self.m_Offset, self.m_DataType)
					self.m_NumExtraChildren = self.m_Value.GetNumChildren();
				else:
					self.m_Value = fg_GetEmptyValue(self.m_ValueObject)
			else:
				self.m_Value = fg_GetEmptyValue(self.m_ValueObject)

			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)
		AVLTreeType = fg_GetContainingType(ValueType)
		if AVLTreeType is None or not AVLTreeType.IsValid():
			return False

		DataType = AVLTreeType.GetTemplateArgumentType(3)
		DataType = fg_GetValidCanonicalType(DataType)

		NodeType = self.m_pStack.GetChildAtIndex(0).GetType().GetUnqualifiedType()
		if NodeType.IsPointerType():
			NodeType = NodeType.GetPointeeType().GetUnqualifiedType()
		NodeType = fg_GetValidCanonicalType(NodeType)

		self.m_DataType = DataType
		self.m_NodeType = NodeType

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)

		self.m_Offset = fg_GetAVLTreeOffset(AVLTreeType, DataType, NodeType)
		if self.m_Offset is None:
			return False

		return True

	def fp_GetChildIndex(self, _Name):
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if self.m_Value is not None:
			if _iChild == self.m_NumExtraChildren:
				return self.m_Value
			elif _iChild < self.m_NumExtraChildren:
				return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren


class CSynthProvider_TCMap(CSynthProvider_Container):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary, 'NMib::NContainer::TCMap')

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Tree = fg_FindRawChild(self.m_ValueObject, 'mp_Tree')
			if not fg_IsValidSBValue(self.m_Tree):
				self.m_Tree = fg_ChildPath(self.m_ValueObject, 'mp_Tree')
			self.m_Root = self.m_Tree.GetValueForExpressionPath('.m_Root')
			if not fg_IsValidSBValue(self.m_Root):
				self.m_Root = fg_FindRawChild(self.m_Tree, 'm_Root')
			if not self.fp_ExtractType():
				return

			self.m_Root = self.m_ValueObject.CreateValueFromAddress('[TempData]', (self.m_Root.GetValueAsUnsigned() >> 2) << 2, self.m_NodeType).AddressOf()

			self.m_DataSize = self.m_DataType.GetByteSize()

			pNode = CSynthProvider_TCAVLTreeAggregate_Node(self.m_Root, self.m_NodeType)
			iNode = CSynthProvider_TCAVLTreeAggregate_Iterator(pNode)

			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ContainerGetChildAtIndex(self, _iChild):
		Address = self.m_ChildMap[_iChild]
		if Address is None or Address < self.m_Offset:
			return None

		RetValue =  fg_CreateDynamicValue(self.m_ValueObject, '[' + str(_iChild) + ']', Address - self.m_Offset, self.m_DataType)
		return RetValue

	def fp_ExtractType(self):

		ValueType = fg_GetInheritedType(fg_GetValueType(self.m_Tree), 'NMib::NIntrusive::TCAVLTreeAggregate')
		if ValueType is None or not ValueType.IsValid() or ValueType.GetNumberOfTemplateArguments() < 4:
			return False

		DataType = fg_GetValidCanonicalType(ValueType.GetTemplateArgumentType(3))

		NodeType = self.m_Root.GetType().GetPointeeType().GetUnqualifiedType()
		NodeType = fg_GetValidCanonicalType(NodeType)

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)

		self.m_DataType = DataType
		self.m_NodeType = NodeType

		self.m_Offset = fg_GetAVLTreeOffset(ValueType, DataType, NodeType)
		if self.m_Offset is None:
			return False

		return True

	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren

		pNode = CSynthProvider_TCAVLTreeAggregate_Node(self.m_Root, self.m_NodeType)
		iNode = CSynthProvider_TCAVLTreeAggregate_Iterator(pNode)
		Max = [g_MaxSynthChildren * 2]
		nChildren = 0
		self.m_ChildMap = []
		while iNode.f_IsValid():
			self.m_ChildMap.append(iNode.f_Node().m_Value)
			nChildren = nChildren + 1
			if nChildren >= g_MaxSynthChildren:
				nChildren = g_MaxSynthChildren
				break
			iNode.f_Next(Max)

		return nChildren;

class CSynthProvider_TCMap_CIterator(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Iter = self.m_ValueObject.GetChildMemberWithName('mp_Iter')
			self.m_pStack = self.m_Iter.GetChildMemberWithName('m_pStack')
			self.m_iStack = self.m_Iter.GetChildMemberWithName('m_iStack')
			if not fg_IsValidSBValue(self.m_iStack):
				return
			if not self.fp_ExtractType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = None
			self.m_bEmpty = True
			if self.m_iStack.GetValueAsSigned() >= 0:
				Address = fg_GetValueAsUnsigned(self.m_pStack.GetChildAtIndex(fg_GetValueAsUnsigned(self.m_iStack)%92))
				if Address >= self.m_Offset:
					self.m_bEmpty = False
					self.m_Value = fg_CreateDynamicValue(self.m_Iter, '[Value]', Address - self.m_Offset, self.m_DataType)
					self.m_NumExtraChildren = self.m_Value.GetNumChildren();
				else:
					self.m_Value = fg_GetEmptyValue(self.m_ValueObject)
			else:
				self.m_Value = fg_GetEmptyValue(self.m_ValueObject)

			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ValueType = fg_GetValueType(self.m_Iter)

		AVLTreeType = fg_GetContainingType(ValueType)
		if AVLTreeType is None or not AVLTreeType.IsValid():
			MapPointer = fg_FindRawChild(self.m_ValueObject, 'mp_pMap')
			if not fg_IsValidSBValue(MapPointer) or MapPointer.GetValueAsUnsigned() == 0:
				return False
			Tree = fg_FindRawChild(MapPointer.Dereference(), 'mp_Tree')
			if not fg_IsValidSBValue(Tree):
				return False
			AVLTreeType = fg_GetInheritedType(fg_GetValueType(Tree), 'NMib::NIntrusive::TCAVLTreeAggregate')
			if AVLTreeType is None or not AVLTreeType.IsValid():
				return False

		DataType = AVLTreeType.GetTemplateArgumentType(3)
		DataType = fg_GetValidCanonicalType(DataType)

		NodeType = self.m_pStack.GetChildAtIndex(0).GetType().GetUnqualifiedType()
		if NodeType.IsPointerType():
			NodeType = NodeType.GetPointeeType().GetUnqualifiedType()
		NodeType = fg_GetValidCanonicalType(NodeType)

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)

		self.m_DataType = DataType
		self.m_NodeType = NodeType

		self.m_Offset = fg_GetAVLTreeOffset(AVLTreeType, DataType, NodeType)
		if self.m_Offset is None:
			return False

		return True

	def fp_GetChildIndex(self, _Name):
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if self.m_Value is not None:
			if _iChild == self.m_NumExtraChildren:
				return self.m_Value
			elif _iChild < self.m_NumExtraChildren:
				return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren


def fg_SummaryProvider_TCMapNode(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		KeyMember = _Value.GetChildMemberWithName('m_Key')
		if not fg_IsValidSBValue(KeyMember):
			KeyMember = _Value.GetChildMemberWithName('mp_Key')
		if not fg_IsValidSBValue(KeyMember) and _Value.GetNumChildren() == 1:
			KeyMember = _Value.GetChildAtIndex(0).GetChildMemberWithName('m_Key')
			if not fg_IsValidSBValue(KeyMember):
				KeyMember = _Value.GetChildAtIndex(0).GetChildMemberWithName('mp_Key')

		KeySummary = None
		if fg_IsValidSBValue(KeyMember):
			KeySummary = KeyMember.GetSummary()
			if KeySummary is None:
				KeySummary = KeyMember.GetValue()

		ValueMember = _Value.GetChildMemberWithName('m_Value')
		if not fg_IsValidSBValue(ValueMember):
			ValueMember = _Value.GetChildMemberWithName('mp_Value')
		if not fg_IsValidSBValue(ValueMember) and _Value.GetNumChildren() == 1:
			ValueMember = _Value.GetChildAtIndex(0).GetChildMemberWithName('m_Value')
			if not fg_IsValidSBValue(ValueMember):
				ValueMember = _Value.GetChildAtIndex(0).GetChildMemberWithName('mp_Value')

		ValueSummary = None
		if fg_IsValidSBValue(ValueMember):
			ValueSummary = ValueMember.GetSummary()
			if ValueSummary is None:
				ValueSummary = ValueMember.GetValue()

			if ValueSummary == "None":
				ValueSummary = "..."

		if KeySummary is None:
			if ValueSummary is None:
				Value = None
			else:
				Value = '? > ' + str(ValueSummary)
		else:
			if ValueSummary is None:
				Value = str(KeySummary)
			else:
				Value = str(KeySummary) + ' > ' + str(ValueSummary)

		if ValueType.IsPointerType():
			PointerSummary = hex(_Value.GetValueAsUnsigned())
			if Value is None:
				return PointerSummary
			return PointerSummary + '   ' + Value
		return Value

	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_TCMapNode) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_AVLTree(_Debugger):

	# Intrusive AVL tree
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate, '(^|^const )NMib::NIntrusive::TCAVLTree<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerMapLimited, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerMapLimited, '(^|^const )NMib::NIntrusive::TCAVLTree<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate_CIterator, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::TCIterator<.*>$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::TCIterator<.*>$', True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate_CIterator, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::CIterator$', True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate_CIterator, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::CIteratorConst$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::CIterator$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::CIteratorConst$', True, 1)

	# Map
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, '(^|^const )NMib::NContainer::TCMap<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, '(^|^const )NMib::NContainer::TCSet<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, '(^|^const )NMib::NContainer::TCMapWithPool<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, '(^|^const )NMib::NContainer::TCSetWithPool<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerMapLimited, '(^|^const )NMib::NContainer::TCMap<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, '(^|^const )NMib::NContainer::TCSet<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerMapLimited, '(^|^const )NMib::NContainer::TCMapWithPool<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, '(^|^const )NMib::NContainer::TCSetWithPool<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap_CIterator, '(^|^const )NMib::NContainer::TCMap<.*>::TCIterator<.*>$', True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap_CIterator, '(^|^const )NMib::NContainer::NPrivate::TCMapIterator<.*>$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCMapNode, '(^|^const )(NMib::NContainer::)TCMapNode<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCMapNode, '(^|^const )(NMib::NContainer::)TCDestructiveMapNode<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NContainer::TCMap<.*>::TCIterator<.*>$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NContainer::NPrivate::TCMapIterator<.*>$', True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap_CIterator, '(^|^const )NMib::NContainer::TCMap<.*>::CIterator$', True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap_CIterator, '(^|^const )NMib::NContainer::TCMap<.*>::CIteratorConst$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NContainer::TCMap<.*>::CIterator$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NContainer::TCMap<.*>::CIteratorConst$', True, 1)

	return
