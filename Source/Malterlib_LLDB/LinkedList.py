# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_GetTypeName(_Type):
	if _Type is None or not _Type.IsValid():
		return None

	Type = fg_GetValidCanonicalType(_Type).GetUnqualifiedType()
	if Type is None or not Type.IsValid():
		return None

	return Type.GetName()

def fg_TypesEqual(_Type0, _Type1):
	TypeName0 = fg_GetTypeName(_Type0)
	TypeName1 = fg_GetTypeName(_Type1)
	return TypeName0 is not None and TypeName0 == TypeName1

def fg_GetLinkMemberName(_TranslatorType):
	TranslatorName = fg_GetTypeName(_TranslatorType)
	if TranslatorName is None:
		return None

	TranslatorName = TranslatorName.split('::')[-1]
	for Prefix in ['CDLinkTranslator', 'CSLinkTranslator']:
		PrefixOffset = TranslatorName.find(Prefix)
		if PrefixOffset >= 0:
			MemberName = TranslatorName[PrefixOffset + len(Prefix):]
			if len(MemberName) > 0:
				return MemberName

	return None

def fg_TypeStartsWithLink(_Type, _LinkType, _Depth = 0):
	if _Depth >= 4:
		return False

	Type = fg_GetValidCanonicalType(_Type).GetUnqualifiedType()
	if not Type.IsValid():
		return False

	if fg_TypesEqual(Type, _LinkType):
		return True

	for iField in range(0, Type.GetNumberOfFields()):
		Field = Type.GetFieldAtIndex(iField)
		if Field.GetOffsetInBytes() == 0 and fg_TypeStartsWithLink(Field.GetType(), _LinkType, _Depth + 1):
			return True

	TypeName = Type.GetName()
	if TypeName is not None and TypeName.startswith('NMib::NIntrusive::TCDLink<') and Type.GetNumberOfTemplateArguments() > 0 and fg_TypesEqual(Type.GetTemplateArgumentType(0), _LinkType):
		return True

	return False

def fg_GetLinkFieldOffsets(_DataType, _LinkType, _BaseOffset = 0, _Depth = 0):
	if _Depth >= 4:
		return []

	Type = fg_GetValidCanonicalType(_DataType).GetUnqualifiedType()
	if not Type.IsValid():
		return []

	Offsets = []
	for iField in range(0, Type.GetNumberOfFields()):
		Field = Type.GetFieldAtIndex(iField)
		if fg_TypeStartsWithLink(Field.GetType(), _LinkType):
			Offsets.append((_BaseOffset + Field.GetOffsetInBytes(), Field.GetName()))

	for iBase in range(0, Type.GetNumberOfDirectBaseClasses()):
		Base = Type.GetDirectBaseClassAtIndex(iBase)
		Offsets += fg_GetLinkFieldOffsets(Base.GetType(), _LinkType, _BaseOffset + Base.GetOffsetInBytes(), _Depth + 1)

	return Offsets

def fg_GetNamedFieldOffsets(_DataType, _FieldName, _BaseOffset = 0, _Depth = 0):
	if _Depth >= 4:
		return []

	Type = fg_GetValidCanonicalType(_DataType).GetUnqualifiedType()
	if not Type.IsValid():
		return []

	Offsets = []
	for iField in range(0, Type.GetNumberOfFields()):
		Field = Type.GetFieldAtIndex(iField)
		if Field.GetName() == _FieldName:
			Offsets.append(_BaseOffset + Field.GetOffsetInBytes())

	for iBase in range(0, Type.GetNumberOfDirectBaseClasses()):
		Base = Type.GetDirectBaseClassAtIndex(iBase)
		Offsets += fg_GetNamedFieldOffsets(Base.GetType(), _FieldName, _BaseOffset + Base.GetOffsetInBytes(), _Depth + 1)

	return Offsets

def fg_GetListOffset(_DataType, _LinkType, _TranslatorType):
	Offsets = fg_GetLinkFieldOffsets(_DataType, _LinkType)
	MemberName = fg_GetLinkMemberName(_TranslatorType)
	if MemberName is not None:
		NamedOffsets = [Offset for Offset, FieldName in Offsets if FieldName == MemberName]
		if len(NamedOffsets) == 1:
			return NamedOffsets[0]
		NamedOffsets = fg_GetNamedFieldOffsets(_DataType, MemberName)
		if len(NamedOffsets) == 1:
			return NamedOffsets[0]

	if len(Offsets) == 1:
		return Offsets[0][0]

	return None

def fg_GetDLinkListTypes(_Type):
	ContainerType = fg_GetContainingType(_Type)
	if ContainerType is None or not ContainerType.IsValid():
		ContainerType = fg_GetValidCanonicalType(_Type)
	if ContainerType is None or not ContainerType.IsValid() or ContainerType.GetNumberOfTemplateArguments() < 3:
		return None

	DataType = fg_GetValidTemplateArgumentType(ContainerType, 0)
	TranslatorType = fg_GetValidTemplateArgumentType(ContainerType, 1)
	LinkType = fg_GetValidTemplateArgumentType(ContainerType, 2)
	if DataType is None or TranslatorType is None or LinkType is None:
		return None

	return (ContainerType, DataType, TranslatorType, LinkType)

def fg_GetSLinkListTypes(_Type, _LinkType):
	ContainerType = fg_GetContainingType(_Type)
	if ContainerType is None or not ContainerType.IsValid():
		ContainerType = fg_GetValidCanonicalType(_Type)
	if ContainerType is None or not ContainerType.IsValid() or ContainerType.GetNumberOfTemplateArguments() < 2:
		return None

	DataType = fg_GetValidTemplateArgumentType(ContainerType, 0)
	TranslatorType = fg_GetValidTemplateArgumentType(ContainerType, 1)
	if DataType is None or TranslatorType is None or _LinkType is None or not _LinkType.IsValid():
		return None

	return (ContainerType, DataType, TranslatorType, fg_GetValidCanonicalType(_LinkType))

class CSynthProvider_TCDLinkListAggregate(CSynthProvider_Container):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary, "NMib::NIntrusive::TCDLinkListAggregate")

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_DataSize = self.m_DataType.GetByteSize()
			self.m_ListLink = fg_ChildPath(self.m_ValueObject, 'm_Link.m_pNextPtr')
			self.m_pThisLink = fg_GetAddressOf(self.m_ListLink)
			self.m_First = self.fp_GetNodePointer(self.m_ListLink)
			self.m_pFirst = self.fp_GetNode(self.m_First)
			self.m_bValid = True
			self.m_bLooped = False

		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ContainerType = self.m_ValueObjectType
		if not ContainerType.IsValid():
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
		else:
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 1:
			TranslatorType = ContainerType.GetTemplateArgumentType(1)
			TranslatorType = fg_GetValidCanonicalType(TranslatorType)
		else:
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = fg_GetValidCanonicalType(LinkType)
		else:
			return False

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		self.m_Offset = fg_GetListOffset(DataType, LinkType, TranslatorType)
		if self.m_Offset is None:
			return False

		return True

	def fp_GetNodePointer(self, _pNode):
		return (fg_GetValueAsUnsigned(_pNode) >> 2) << 2

	def fp_GetNode(self, _pNodePointer):
		return self.m_ValueObject.CreateValueFromAddress("[TempData]", _pNodePointer, self.m_LinkType)

	def fp_GetData(self, _pNodePointer, _Name):
		if _pNodePointer < self.m_Offset:
			return None
		return fg_CreateDynamicValue(self.m_ValueObject, _Name, _pNodePointer - self.m_Offset, self.m_DataType)

	def fp_GetNext(self, _pNode):
		pNext = _pNode.GetValueForExpressionPath('.m_pNextPtr')
		pNextPointer = self.fp_GetNodePointer(pNext)
		return self.fp_GetNode(pNextPointer)

	def fp_ContainerGetChildAtIndex(self, _iChild):
		NodeAddress = self.m_ChildMap[_iChild]
		if NodeAddress is None:
			return None # We are at end of list

		return self.fp_GetData(NodeAddress, '[' + str(_iChild) + ']')

	def fp_ContainerGetError(self):
		if not self.m_bValid:
			return "Failed to extract type"
		if self.m_bLooped:
			return "Linked list is corrupted (looped)"
		return None

	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren
		if self.m_First == 0:
			return 0

		self.m_ChildMap = []

		ChildDict = {}
		self.m_bLooped = False

		pNode = self.m_pFirst
		pFirst = fg_GetAddressOf(pNode)
		iChild = 0
		NodeAddress = fg_GetAddressOf(pNode)
		while NodeAddress != self.m_pThisLink and NodeAddress != 0:
			if NodeAddress in ChildDict:
				self.m_bLooped = True
				break
			ChildDict[NodeAddress] = True

			self.m_ChildMap.append(NodeAddress)
			iChild = iChild + 1
			pNode = self.fp_GetNext(pNode)
			NodeAddress = fg_GetAddressOf(pNode)
			if iChild >= g_MaxSynthChildren or NodeAddress == pFirst:
				break
		return iChild;

class CSynthProvider_TCDLinkListAggregate_CIterator(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = None
			if not self.fp_ExtractType():
				return
			self.m_Current = self.m_ValueObject.GetChildMemberWithName('m_pCurrent')
			CurrentValue = self.m_Current.GetValueAsUnsigned()
			self.m_bEmpty = True
			if CurrentValue != 0 and CurrentValue >= self.m_Offset:
				self.m_bEmpty = False
				self.m_Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', CurrentValue - self.m_Offset, self.m_DataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True

		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		ListTypes = fg_GetDLinkListTypes(ValueType)
		if ListTypes is None:
			return False
		ContainerType, DataType, TranslatorType, LinkType = ListTypes

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		self.m_Offset = fg_GetListOffset(DataType, LinkType, TranslatorType)
		if self.m_Offset is None:
			return False

		return True

	def fp_GetChildIndex(self, _Name):
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			if self.m_bEmpty:
				return fg_GetEmptyValue(self.m_ValueObject)
			else:
				return self.m_Value
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

class CSynthProvider_TCLinkedList(CSynthProvider_Container):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			if not self.fp_ExtractType2():
				return
			self.m_DataSize = self.m_DataType.GetByteSize()
			self.m_ListLink = fg_ChildPath(self.m_ValueObject, 'm_Data.m_List.m_Link.m_pNextPtr')
			self.m_pThisLink = fg_GetAddressOf(self.m_ListLink)
			self.m_First = self.fp_GetNodePointer(self.m_ListLink)
			self.m_pFirst = self.fp_GetNode(self.m_First)
			self.m_bValid = True
			self.m_bLooped = False
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType2(self):

		ContainerType = fg_GetValueType(self.m_ValueObjectDeref)
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
		else:
			return False

		fg_PrecacheType(DataType)
		self.m_ValueType = DataType

		return True

	def fp_ExtractType(self):

		ContainerType = fg_ChildPath(self.m_ValueObject, 'm_Data.m_List').GetType()
		ContainerType = fg_GetInheritedType(ContainerType, "NMib::NIntrusive::TCDLinkListAggregate")
		if not ContainerType.IsValid():
			return False
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
		else:
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 1:
			TranslatorType = ContainerType.GetTemplateArgumentType(1)
			TranslatorType = fg_GetValidCanonicalType(TranslatorType)
		else:
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = fg_GetValidCanonicalType(LinkType)
		else:
			return False

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		self.m_Offset = fg_GetListOffset(DataType, LinkType, TranslatorType)
		if self.m_Offset is None:
			return False

		return True

	def fp_GetNodePointer(self, _pNode):
		return (fg_GetValueAsUnsigned(_pNode) >> 2) << 2

	def fp_GetNode(self, _pNodePointer):
		return self.m_ValueObject.CreateValueFromAddress("[TempData]", _pNodePointer, self.m_LinkType)

	def fp_GetData(self, _pNodePointer, _Name):
		if self.m_ValueType is None:
			return None;
		if _pNodePointer < self.m_Offset:
			return None
		Data = self.m_ValueObject.CreateValueFromAddress('[TempData]', _pNodePointer - self.m_Offset, self.m_DataType)
		MemberAddress = fg_GetAddressOf(Data.GetChildMemberWithName('m_Object'))
		return fg_CreateDynamicValue(self.m_ValueObject, _Name, MemberAddress, self.m_ValueType)

	def fp_GetNext(self, _pNode):
		pNext = _pNode.GetValueForExpressionPath('.m_pNextPtr')
		pNextPointer = self.fp_GetNodePointer(pNext)
		return self.fp_GetNode(pNextPointer)

	def fp_ContainerGetChildAtIndex(self, _iChild):
		NodeAddress = self.m_ChildMap[_iChild]
		if NodeAddress is None:
			return None # We are at end of list

		return self.fp_GetData(NodeAddress, '[' + str(_iChild) + ']')

	def fp_ContainerGetError(self):
		if not self.m_bValid:
			return "Failed to extract type"
		if self.m_bLooped:
			return "Linked list is corrupted (looped)"
		return None

	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren
		if self.m_First == 0:
			return 0

		self.m_ChildMap = []

		ChildDict = {}
		self.m_bLooped = False

		pNode = self.m_pFirst
		iChild = 0
		NodeAddress = fg_GetAddressOf(pNode)
		while NodeAddress != self.m_pThisLink:
			if NodeAddress in ChildDict:
				self.m_bLooped = True
				break
			ChildDict[NodeAddress] = True

			self.m_ChildMap.append(NodeAddress)
			iChild = iChild + 1
			pNode = self.fp_GetNext(pNode)
			NodeAddress = fg_GetAddressOf(pNode)
			if iChild >= g_MaxSynthChildren:
				break

		return iChild;

class CSynthProvider_TCLinkedList_CIterator(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		self.m_Value = None
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = None
			if not self.fp_ExtractType():
				return
			if not self.fp_ExtractType2():
				return
			self.m_Current = fg_ChildPath(self.m_ValueObject, 'm_Iter.m_pCurrent')
			CurrentValue = self.m_Current.GetValueAsUnsigned()
			self.m_bEmpty = True
			if CurrentValue != 0 and CurrentValue >= self.m_Offset:
				self.m_bEmpty = False
				Data = self.m_ValueObject.CreateValueFromAddress('[TempData]', self.m_Current.GetValueAsUnsigned() - self.m_Offset, self.m_DataType)
				MemberAddress = fg_GetAddressOf(Data.GetChildMemberWithName('m_Object'))
				self.m_Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', MemberAddress, self.m_ValueType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True

		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		Iter = fg_FindRawChild(self.m_ValueObject, 'm_Iter')
		if not fg_IsValidSBValue(Iter):
			Iter = self.m_ValueObject.GetChildMemberWithName('m_Iter')
		ListTypes = fg_GetDLinkListTypes(fg_GetValueType(Iter))
		if ListTypes is None:
			return False
		ContainerType, DataType, TranslatorType, LinkType = ListTypes

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		self.m_Offset = fg_GetListOffset(DataType, LinkType, TranslatorType)
		if self.m_Offset is None:
			return False

		return True

	def fp_ExtractType2(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		ContainerType = fg_GetContainingType(ValueType)
		if ContainerType is None or not ContainerType.IsValid():
			return False

		DataType = fg_GetValidTemplateArgumentType(ContainerType, 0)
		if DataType is None:
			return False

		fg_PrecacheType(DataType)
		self.m_ValueType = DataType
		return True

	def fp_GetChildIndex(self, _Name):
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			if self.m_bEmpty:
				return fg_GetEmptyValue(self.m_ValueObject)
			else:
				return self.m_Value
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren


class CSynthProvider_TCSLinkListAggregate(CSynthProvider_Container):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary)
		self.m_CachedNode = None

	def update(self):
		CSynthProvider_Container.update(self)
		self.m_CachedNode = None
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_DataSize = self.m_DataType.GetByteSize()
			Data = fg_FindRawChild(self.m_ValueObject, 'm_Data')
			First = fg_FindRawChild(Data, 'm_First')
			self.m_ListLink = First.GetChildMemberWithName('m_pNext')
			if not fg_IsValidSBValue(self.m_ListLink):
				return
			self.m_bValid = True
			self.m_bLooped = False
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ContainerType = fg_GetValueType(self.m_ValueObjectDeref)
		ContainerType = fg_GetInheritedType(ContainerType, "NMib::NIntrusive::TCSLinkListAggregate")
		Data = fg_FindRawChild(self.m_ValueObject, 'm_Data')
		First = fg_FindRawChild(Data, 'm_First')
		LinkType = fg_GetValidCanonicalType(fg_GetValueType(First))

		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
		else:
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 1:
			TranslatorType = ContainerType.GetTemplateArgumentType(1)
			TranslatorType = fg_GetValidCanonicalType(TranslatorType)
		else:
			return False

		if LinkType is None or not LinkType.IsValid():
			return False

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		self.m_Offset = fg_GetListOffset(DataType, LinkType, TranslatorType)
		if self.m_Offset is None:
			return False

		return True

	def fp_GetData(self, _pNodePointer, _Name):
		if _pNodePointer < self.m_Offset:
			return None
		return fg_CreateDynamicValue(self.m_ValueObject, _Name, _pNodePointer - self.m_Offset, self.m_DataType)

	def fp_GetNext(self, _pNode):
		pNext = _pNode.GetValueForExpressionPath('->m_pNext')
		return pNext

	def fp_ContainerGetChildAtIndex(self, _iChild):
		NodeAddress = self.m_ChildMap[_iChild]
		if NodeAddress is None:
			return None # We are at end of list

		return self.fp_GetData(NodeAddress, '[' + str(_iChild) + ']')

	def fp_ContainerGetError(self):
		if not self.m_bValid:
			return "Failed to extract type"
		if self.m_bLooped:
			return "Linked list is corrupted (looped)"
		return None

	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren
		if self.m_ListLink.GetValueAsUnsigned() == 0:
			return 0

		self.m_ChildMap = []

		ChildDict = {}
		self.m_bLooped = False

		pNode = self.m_ListLink
		iChild = 0
		NodeAddress = fg_GetValueAsUnsigned(pNode)
		while NodeAddress != 0:
			if NodeAddress in ChildDict:
				self.m_bLooped = True
				break
			ChildDict[NodeAddress] = True

			self.m_ChildMap.append(NodeAddress)
			iChild = iChild + 1
			pNode = self.fp_GetNext(pNode)
			NodeAddress = fg_GetValueAsUnsigned(pNode)
			if iChild >= g_MaxSynthChildren:
				break
		return iChild;


class CSynthProvider_TCSLinkListAggregate_CIterator(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = None
			self.m_Current = self.m_ValueObject.GetChildMemberWithName('m_pCurrent')
			CurrentValue = self.m_Current.GetValueAsUnsigned()
			self.m_bEmpty = True
			if CurrentValue != 0 and CurrentValue >= self.m_Offset:
				self.m_bEmpty = False
				self.m_Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', CurrentValue - self.m_Offset, self.m_DataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		Current = self.m_ValueObject.GetChildMemberWithName('m_pCurrent')
		LinkType = fg_GetValidCanonicalType(Current.GetType().GetPointeeType())
		ListTypes = fg_GetSLinkListTypes(ValueType, LinkType)
		if ListTypes is None:
			return False
		ContainerType, DataType, TranslatorType, LinkType = ListTypes

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		self.m_Offset = fg_GetListOffset(DataType, LinkType, TranslatorType)
		if self.m_Offset is None:
			return False

		return True

	def fp_GetChildIndex(self, _Name):
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			if self.m_bEmpty:
				return fg_GetEmptyValue(self.m_ValueObject)
			else:
				return self.m_Value
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren


def fg_MibLLDBInit_LinkedList(_Debugger):

	# Intrusive linked list
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate, "(^|^const )NMib::NIntrusive::TCDLinkList<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCDLinkList<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIterator<.*>$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIteratorConst<.*>$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIterator$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIteratorConst$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIterator<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIteratorConst<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIterator$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIteratorConst$", True, 1)

	# Intrusive singly linked list
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate, "(^|^const )NMib::NIntrusive::TCSLinkList<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCSLinkList<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIterator<.*>$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIteratorConst<.*>$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIterator$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIteratorConst$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIterator<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIteratorConst<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIterator$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIteratorConst$", True, 1)

	# Linked list
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList, "(^|^const )NMib::NContainer::TCLinkedList<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NContainer::TCLinkedList<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList_CIterator, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIterator<.*>$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList_CIterator, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIteratorConst<.*>$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList_CIterator, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIterator$", True, 1)
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList_CIterator, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIteratorConst$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIterator<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIteratorConst<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIterator$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIteratorConst$", True, 1)

	return
