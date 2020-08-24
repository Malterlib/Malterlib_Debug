# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
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
		
		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = fg_GetValidCanonicalType(LinkType)
		else:
			return False

		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)

		self.m_DataType = DataType
		self.m_LinkType = LinkType

		MemberFunctionHelper = fg_GetMemberFunction(ContainerType, 'fs_Debug_GetOffset')
		if not MemberFunctionHelper:
			return False

		OffsetType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
		self.m_Offset = int(OffsetType.GetName().split(',')[-1].split('>')[0])

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_List')
		if not MemberFunctionHelper:
			return False

		ContainerType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType().GetPointeeType())
		if not ContainerType.IsValid():
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
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

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_GetOffset')
		if not MemberFunctionHelper:
			return False

		OffsetType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
		self.m_Offset = int(OffsetType.GetName().split(',')[-1].split('>')[0])

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
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

		if ContainerType.GetNumberOfTemplateArguments() > 2:
			LinkType = ContainerType.GetTemplateArgumentType(2)
			LinkType = fg_GetValidCanonicalType(LinkType)
		else:
			return False
		
		fg_PrecacheType(DataType)
		fg_PrecacheType(LinkType)
		
		self.m_DataType = DataType
		self.m_LinkType = LinkType
		
		MemberFunctionHelper = fg_GetMemberFunction(ContainerType, 'fs_Debug_GetOffset')
		if not MemberFunctionHelper:
			return False

		OffsetType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
		self.m_Offset = int(OffsetType.GetName().split(',')[-1].split('>')[0])

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_IntrusiveList')
		if not MemberFunctionHelper:
			return False

		ContainerType = fg_GetInheritedType(fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType().GetPointeeType()), "NMib::NIntrusive::TCDLinkListAggregate")
		if not ContainerType.IsValid():
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
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

		MemberFunctionHelper = fg_GetMemberFunction(ContainerType, 'fs_Debug_GetOffset')
		if not MemberFunctionHelper:
			return False

		OffsetType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
		self.m_Offset = int(OffsetType.GetName().split(',')[-1].split('>')[0])

		return True

	def fp_ExtractType2(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_List')
		if not MemberFunctionHelper:
			return False

		ContainerType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType().GetPointeeType())
		if not ContainerType.IsValid():
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
		else:
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
			self.m_ListLink = fg_ChildPath(self.m_ValueObject, 'm_Data.m_First.m_pNext')
			self.m_bValid = True
			self.m_bLooped = False
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ContainerType = fg_GetValueType(self.m_ValueObjectDeref)
		ContainerType = fg_GetInheritedType(ContainerType, "NMib::NIntrusive::TCSLinkListAggregate")
		
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
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

		MemberFunctionHelper = fg_GetMemberFunction(ContainerType, 'fs_Debug_GetOffset')
		if not MemberFunctionHelper:
			return False

		OffsetType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
		self.m_Offset = int(OffsetType.GetName().split(',')[-1].split('>')[0])

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ValueType = fg_GetValueType(self.m_ValueObjectDeref)

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_List')
		if not MemberFunctionHelper:
			return False

		ContainerType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType().GetPointeeType())
		if not ContainerType.IsValid():
			return False

		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
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

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_GetOffset')
		if not MemberFunctionHelper:
			return False
		
		OffsetType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
		self.m_Offset = int(OffsetType.GetName().split(',')[-1].split('>')[0])

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
