# Copyright © 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *

class CSynthProvider_TCDLinkListAggregate(CSynthProvider_Container):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_DataSize = self.m_DataType.GetByteSize()
			self.m_ListLink = fg_ChildPath(self.m_ValueObject, 'm_Link.m_pNextPtr.m_pPtr')
			self.m_pThisLink = self.m_ListLink.AddressOf().GetValueAsUnsigned()
			self.m_First = self.fp_GetNodePointer(self.m_ListLink)
			self.m_pFirst = self.fp_GetNode(self.m_First)
			self.m_bValid = True
		 
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):

		ContainerType = fg_GetInheritedType(self.m_ValueObjectDeref.GetType(), "NMib::NIntrusive::TCDLinkListAggregate")
		if not ContainerType.IsValid():
			return False
		
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
		else:
			return False
		
		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = LinkType.GetCanonicalType()
		else:
			return False
		
		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_OffsetTCDLinkListAggregate", ContainerType)
		if not fg_IsValidSBValue(Offset):
			return False
		self.m_Offset = Offset.GetValueAsUnsigned()
		return True

	def fp_GetNodePointer(self, _pNode):
		return (_pNode.GetValueAsUnsigned(0) >> 2) << 2

	def fp_GetNode(self, _pNodePointer):
		return self.m_ValueObject.CreateValueFromAddress("[TempData]", _pNodePointer, self.m_LinkType)

	def fp_GetData(self, _pNodePointer, _Name):
		return self.m_ValueObject.CreateValueFromAddress(_Name, _pNodePointer - self.m_Offset, self.m_DataType)

	def fp_GetNext(self, _pNode):
		pNext = _pNode.GetValueForExpressionPath('.m_Data.m_pNextPtr')
		pNextPointer = self.fp_GetNodePointer(pNext)
		return self.fp_GetNode(pNextPointer)

	# Floyd's cyle-finding algorithm
	# try to detect if this list has a loop
	def fp_HasLoop(self):
		pSlow = self.m_pFirst
		pFast1 = self.m_pFirst
		pFast2 = self.m_pFirst
		while pSlow.AddressOf().GetValueAsUnsigned(0) != self.m_pThisLink:
			SlowAddress = pSlow.AddressOf().GetValueAsUnsigned(0)
			pFast1 = self.fp_GetNext(pFast2)
			if pFast1.AddressOf().GetValueAsUnsigned(0) == self.m_pThisLink:
				return False
			pFast2 = self.fp_GetNext(pFast1)
			if pFast2.AddressOf().GetValueAsUnsigned(0) == self.m_pThisLink:
				return False
			if pFast1.AddressOf().GetValueAsUnsigned(0) == SlowAddress or pFast2.AddressOf().GetValueAsUnsigned(0) == SlowAddress:
				return True
			pSlow = self.fp_GetNext(pSlow)
		return False

	def fp_ContainerGetChildAtIndex(self, _iChild):
		NodeAddress = self.m_ChildMap[_iChild]
		if NodeAddress == None:
			return None # We are at end of list

		return self.fp_GetData(NodeAddress, '[' + str(_iChild) + ']')
			
	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren
		if self.m_First == 0:
			return 0
		#if self.fp_HasLoop():
		#	return 0
		# We handle loops by simply aborting after g_MaxSynthChildren

		self.m_ChildMap = []
		
		pNode = self.m_pFirst
		iChild = 0
		NodeAddress = pNode.AddressOf().GetValueAsUnsigned(0)
		while NodeAddress != self.m_pThisLink:
			self.m_ChildMap.append(NodeAddress)
			iChild = iChild + 1
			pNode = self.fp_GetNext(pNode)
			NodeAddress = pNode.AddressOf().GetValueAsUnsigned(0)
			if iChild >= g_MaxSynthChildren:
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
			if self.m_Current.GetValueAsUnsigned() != 0:
				self.m_Value = self.m_ValueObject.CreateValueFromAddress('[Current]', self.m_Current.GetValueAsUnsigned() - self.m_Offset, self.m_DataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True

		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		
		List = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pList", self.m_ValueObject.GetType())
		if not fg_IsValidSBValue(List):
			return False

		ContainerType = fg_GetInheritedType(fg_GetPointerValueType(List), "NMib::NIntrusive::TCDLinkListAggregate")
		if not ContainerType.IsValid():
			return False
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
		else:
			return False
		
		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = LinkType.GetCanonicalType()
		else:
			return False

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)
		
		self.m_DataType = DataType
		self.m_LinkType = LinkType
		
		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pList->ms_OffsetTCDLinkListAggregate", ContainerType, "ms_OffsetTCDLinkListAggregate")
		if not fg_IsValidSBValue(Offset):
			return False
		
		self.m_Offset = Offset.GetValueAsUnsigned()

		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Current]':
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if self.m_Value != None:
			if _iChild == self.m_NumExtraChildren:
				return self.m_Value
			elif _iChild < self.m_NumExtraChildren:
				return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		if self.m_Current.GetValueAsUnsigned() == 0:
			return 0
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
			self.m_ListLink = fg_ChildPath(self.m_ValueObject, 'm_Data.m_List.m_Link.m_pNextPtr.m_pPtr')
			self.m_pThisLink = self.m_ListLink.AddressOf().GetValueAsUnsigned()
			self.m_First = self.fp_GetNodePointer(self.m_ListLink)
			self.m_pFirst = self.fp_GetNode(self.m_First)
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType2(self):

		ContainerType = fg_GetValueType(self.m_ValueObjectDeref)
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
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
			DataType = DataType.GetCanonicalType()
		else:
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = LinkType.GetCanonicalType()
		else:
			return False
		
		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)
		
		self.m_DataType = DataType
		self.m_LinkType = LinkType
		
		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "m_Data.m_List.ms_OffsetTCDLinkListAggregate", ContainerType, "ms_OffsetTCDLinkListAggregate")
		if not fg_IsValidSBValue(Offset):
			return False
		self.m_Offset = Offset.GetValueAsUnsigned()
		return True

	def fp_GetNodePointer(self, _pNode):
		return (_pNode.GetValueAsUnsigned(0) >> 2) << 2

	def fp_GetNode(self, _pNodePointer):
		return self.m_ValueObject.CreateValueFromAddress("[TempData]", _pNodePointer, self.m_LinkType)

	def fp_GetData(self, _pNodePointer, _Name):
		if self.m_ValueType == None:
			return None;
		Data = self.m_ValueObject.CreateValueFromAddress('[TempData]', _pNodePointer - self.m_Offset, self.m_DataType)
		MemberAddress = Data.GetChildMemberWithName('m_Object').AddressOf().GetValueAsUnsigned()
		return self.m_ValueObject.CreateValueFromAddress(_Name, MemberAddress, self.m_ValueType)

	def fp_GetNext(self, _pNode):
		pNext = _pNode.GetValueForExpressionPath('.m_Data.m_pNextPtr')
		pNextPointer = self.fp_GetNodePointer(pNext)
		return self.fp_GetNode(pNextPointer)

	# Floyd's cyle-finding algorithm
	# try to detect if this list has a loop
	def fp_HasLoop(self):
		pSlow = self.m_pFirst
		pFast1 = self.m_pFirst
		pFast2 = self.m_pFirst
		while pSlow.AddressOf().GetValueAsUnsigned(0) != self.m_pThisLink:
			SlowAddress = pSlow.AddressOf().GetValueAsUnsigned(0)
			pFast1 = self.fp_GetNext(pFast2)
			if pFast1.AddressOf().GetValueAsUnsigned(0) == self.m_pThisLink:
				return False
			pFast2 = self.fp_GetNext(pFast1)
			if pFast2.AddressOf().GetValueAsUnsigned(0) == self.m_pThisLink:
				return False
			if pFast1.AddressOf().GetValueAsUnsigned(0) == SlowAddress or pFast2.AddressOf().GetValueAsUnsigned(0) == SlowAddress:
				return True
			pSlow = self.fp_GetNext(pSlow)
		return False

	def fp_ContainerGetChildAtIndex(self, _iChild):
		NodeAddress = self.m_ChildMap[_iChild]
		if NodeAddress == None:
			return None # We are at end of list

		return self.fp_GetData(NodeAddress, '[' + str(_iChild) + ']')

	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren
		if self.m_First == 0:
			return 0
		#if self.fp_HasLoop():
		#	return 0
		# We handle loops by simply aborting after g_MaxSynthChildren

		self.m_ChildMap = []

		pNode = self.m_pFirst
		iChild = 0
		NodeAddress = pNode.AddressOf().GetValueAsUnsigned(0)
		while NodeAddress != self.m_pThisLink:
			self.m_ChildMap.append(NodeAddress)
			iChild = iChild + 1
			pNode = self.fp_GetNext(pNode)
			NodeAddress = pNode.AddressOf().GetValueAsUnsigned(0)
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
			if self.m_Current.GetValueAsUnsigned() != 0:
				Data = self.m_ValueObject.CreateValueFromAddress('[TempData]', self.m_Current.GetValueAsUnsigned() - self.m_Offset, self.m_DataType)
				MemberAddress = Data.GetChildMemberWithName('m_Object').AddressOf().GetValueAsUnsigned()
				self.m_Value = self.m_ValueObject.CreateValueFromAddress('[Current]', MemberAddress, self.m_ValueType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True

		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		
		ValueType = fg_GetValueType(self.m_ValueObjectDeref)
		List = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pIntrusiveList", ValueType)
		if not fg_IsValidSBValue(List):
			return False

		ContainerType = fg_GetInheritedType(fg_GetPointerValueType(List), "NMib::NIntrusive::TCDLinkListAggregate")
		if not ContainerType.IsValid():
			return False
		
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
		else:
			return False
		
		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = LinkType.GetCanonicalType()
		else:
			return False

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)
		
		self.m_DataType = DataType
		self.m_LinkType = LinkType
		
		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pIntrusiveList->ms_OffsetTCDLinkListAggregate", ContainerType, "ms_OffsetTCDLinkListAggregate")
		if not fg_IsValidSBValue(Offset):
			return False
		
		self.m_Offset = Offset.GetValueAsUnsigned()
		return True

	def fp_ExtractType2(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)
		List = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pList", ValueType)
		if not fg_IsValidSBValue(List):
			return False
		ContainerType = fg_GetPointerValueType(List)
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
		else:
			return False

		fg_PrecacheType(DataType)
		self.m_ValueType = DataType
		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Current]':
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if self.m_Value != None:
			if _iChild == self.m_NumExtraChildren:
				return self.m_Value
			elif _iChild < self.m_NumExtraChildren:
				return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		if self.m_Current.GetValueAsUnsigned() == 0:
			return 0
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
			self.m_ListLink = fg_ChildPath(self.m_ValueObject, 'm_Data.m_First.m_pNext.m_pPtr')
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		ContainerType = fg_GetValueType(self.m_ValueObjectDeref)
		ContainerType = fg_GetInheritedType(ContainerType, "NMib::NIntrusive::TCSLinkListAggregate")
		
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
		else:
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = LinkType.GetCanonicalType()
		else:
			return False
		
		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)
		
		self.m_DataType = DataType
		self.m_LinkType = LinkType
		
		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_OffsetTCSLinkListAggregate", ContainerType)
		if not fg_IsValidSBValue(Offset):
			return False
		self.m_Offset = Offset.GetValueAsUnsigned()
		return True

	def fp_GetData(self, _pNodePointer, _Name):
		return self.m_ValueObject.CreateValueFromAddress(_Name, _pNodePointer - self.m_Offset, self.m_DataType)

	def fp_GetNext(self, _pNode):
		pNext = _pNode.GetValueForExpressionPath('->m_pNext.m_pPtr')
		return pNext

	# Floyd's cyle-finding algorithm
	# try to detect if this list has a loop
	def fp_HasLoop(self):
		pSlow = self.m_ListLink
		pFast1 = self.m_ListLink
		pFast2 = self.m_ListLink
		while pSlow.GetValueAsUnsigned(0) != 0:
			SlowAddress = pSlow.GetValueAsUnsigned(0)
			pFast1 = self.fp_GetNext(pFast2)
			if pFast1.GetValueAsUnsigned(0) == 0:
				return False
			pFast2 = self.fp_GetNext(pFast1)
			if pFast2.GetValueAsUnsigned(0) == 0:
				return False
			if pFast1.GetValueAsUnsigned(0) == SlowAddress or pFast2.GetValueAsUnsigned(0) == SlowAddress:
				return True
			pSlow = self.fp_GetNext(pSlow)
		return False

	def fp_ContainerGetChildAtIndex(self, _iChild):
		NodeAddress = self.m_ChildMap[_iChild]
		if NodeAddress == None:
			return None # We are at end of list

		return self.fp_GetData(NodeAddress, '[' + str(_iChild) + ']')
			
	def fp_ContainerNumChildren(self):
		global g_MaxSynthChildren
		if self.m_ListLink.GetValueAsUnsigned() == 0:
			return 0
		#if self.fp_HasLoop():
		#	return 0
		# We handle loops by simply aborting after g_MaxSynthChildren

		self.m_ChildMap = []

		pNode = self.m_ListLink
		iChild = 0
		NodeAddress = pNode.GetValueAsUnsigned(0)
		while NodeAddress != 0:
			self.m_ChildMap.append(NodeAddress)
			iChild = iChild + 1
			pNode = self.fp_GetNext(pNode)
			NodeAddress = pNode.GetValueAsUnsigned(0)
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
			if self.m_Current.GetValueAsUnsigned():
				self.m_Value = self.m_ValueObject.CreateValueFromAddress('[Current]', self.m_Current.GetValueAsUnsigned() - self.m_Offset, self.m_DataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		List = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pList", fg_GetValueType(self.m_ValueObjectDeref), "ms_OffsetTCSLinkListAggregate")
		if not fg_IsValidSBValue(List):
			return False
		ContainerType = fg_GetPointerValueType(List)
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
		else:
			return False
		
		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = LinkType.GetCanonicalType()
		else:
			return False

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)
		
		self.m_DataType = DataType
		self.m_LinkType = LinkType
		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pList->ms_OffsetTCSLinkListAggregate", ContainerType, "ms_OffsetTCSLinkListAggregate")
		if not fg_IsValidSBValue(Offset):
			return False
		self.m_Offset = Offset.GetValueAsUnsigned()
		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Current]':
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if self.m_Value != None:
			if _iChild == self.m_NumExtraChildren:
				return self.m_Value
			elif _iChild < self.m_NumExtraChildren:
				return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		if self.m_Current.GetValueAsUnsigned() == 0:
			return 0
		return 1 + self.m_NumExtraChildren


def fg_MibLLDBInit_LinkedList(_Debugger):

	# Intrusive linked list
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate, "(^|^const )NMib::NIntrusive::TCDLinkList<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCDLinkList<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIterator$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCDLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIteratorConst$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIterator$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCDLinkListAggregate<.*>::CIteratorConst$", True)

	# Intrusive singly linked list
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate, "(^|^const )NMib::NIntrusive::TCSLinkList<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCSLinkList<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIterator$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCSLinkListAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIteratorConst$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIterator$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCSLinkListAggregate<.*>::CIteratorConst$", True)

	# Linked list
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList, "(^|^const )NMib::NContainer::TCLinkedList<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NContainer::TCLinkedList<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList_CIterator, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIterator$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCLinkedList_CIterator, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIteratorConst$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIterator$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCLinkedList<.*>::CIteratorConst$", True)
	
	return