# Copyright © 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


class CSynthProvider_TCAVLTreeAggregate_Node:
	def fp_Left(self):
		return CSynthProvider_TCAVLTreeAggregate_Node(self.fp_GetNode((self.m_Node.GetChildMemberWithName("m_pNext").GetChildAtIndex(0).GetChildMemberWithName("m_pPtr").GetValueAsUnsigned(0) >> 2) << 2).AddressOf(), self.m_NodeType)

	def fp_Right(self):
		return CSynthProvider_TCAVLTreeAggregate_Node(self.fp_GetNode((self.m_Node.GetChildMemberWithName("m_pNext").GetChildAtIndex(1).GetChildMemberWithName("m_pPtr").GetValueAsUnsigned(0) >> 2) << 2).AddressOf(), self.m_NodeType)

	def fp_GetNode(self, _pNodePointer):
		return self.m_Node.CreateValueFromAddress("[TempData]", _pNodePointer, self.m_NodeType)

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
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Root = fg_ChildPath(self.m_ValueObject, 'm_Root.m_pPtr')

			if not self.fp_ExtractType():
				return
			
			self.m_Root = self.m_ValueObject.CreateValueFromAddress("[TempData]", (self.m_Root.GetValueAsUnsigned() >> 2) << 2, self.m_NodeType).AddressOf()

			self.m_DataSize = self.m_DataType.GetByteSize()
		 
			pNode = CSynthProvider_TCAVLTreeAggregate_Node(self.m_Root, self.m_NodeType)
			iNode = CSynthProvider_TCAVLTreeAggregate_Iterator(pNode)
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ContainerGetChildAtIndex(self, _iChild):
		Address = self.m_ChildMap[_iChild]
		if Address == None:
			return None
		
		RetValue = self.m_ValueObject.CreateValueFromAddress('[' + str(_iChild) + ']', Address - self.m_Offset, self.m_DataType)
		return RetValue
			
	def fp_ExtractType(self):
		
		ValueType = fg_GetInheritedType(self.m_ValueObjectDeref.GetType(), "NMib::NIntrusive::TCAVLTreeAggregate")
		if not ValueType.IsValid() or ValueType.IsPointerType():
			return False
		pNode = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pNode", ValueType, "ms_pNode")
		if not fg_IsValidSBValue(pNode):
			return False
		DataType = pNode.GetType().GetPointeeType()
		DataType = DataType.GetCanonicalType()
		
		NodeType = self.m_Root.GetType().GetPointeeType().GetUnqualifiedType()
		NodeType = NodeType.GetCanonicalType()

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)
		
		self.m_DataType = DataType
		self.m_NodeType = NodeType

		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_OffsetTCAVLTreeAggregate", ValueType, "ms_OffsetTCAVLTreeAggregate")
		if not fg_IsValidSBValue(Offset):
			return False
		self.m_Offset = Offset.GetValueAsUnsigned()
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
			if self.m_iStack.GetValueAsSigned() >= 0:
				Address = self.m_pStack.GetChildAtIndex(self.m_iStack.GetValueAsUnsigned()%92).GetValueAsUnsigned()
				self.m_Value = self.m_ValueObject.CreateValueFromAddress('[Current]', Address - self.m_Offset, self.m_DataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		
		ValueType = fg_GetValueType(self.m_ValueObjectDeref)
		pNode = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pTree->ms_pNode", ValueType)
		if not fg_IsValidSBValue(pNode):
			return False
		DataType = pNode.GetType().GetPointeeType()
		DataType = DataType.GetCanonicalType()
		
		NodeType = self.m_pStack.GetChildAtIndex(0).GetType().GetUnqualifiedType()
		NodeType = NodeType.GetCanonicalType()

		self.m_DataType = DataType
		self.m_NodeType = NodeType

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)
		
		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_pTree->ms_OffsetTCAVLTreeAggregate", ValueType)
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
		if self.m_iStack.GetValueAsSigned() < 0:
			return 0
		return 1 + self.m_NumExtraChildren


class CSynthProvider_TCMap(CSynthProvider_Container):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Tree = fg_ChildPath(self.m_ValueObject, 'mp_Data.m_Tree')
			self.m_Root = self.m_Tree.GetValueForExpressionPath('.m_Root.m_pPtr')
			if not self.fp_ExtractType():
				return

			self.m_Root = self.m_ValueObject.CreateValueFromAddress("[TempData]", (self.m_Root.GetValueAsUnsigned() >> 2) << 2, self.m_NodeType).AddressOf()
			
			self.m_DataSize = self.m_DataType.GetByteSize()
		 
			pNode = CSynthProvider_TCAVLTreeAggregate_Node(self.m_Root, self.m_NodeType)
			iNode = CSynthProvider_TCAVLTreeAggregate_Iterator(pNode)
	
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ContainerGetChildAtIndex(self, _iChild):
		Address = self.m_ChildMap[_iChild]
		if Address == None:
			return None
		
		RetValue =  self.m_ValueObject.CreateValueFromAddress('[' + str(_iChild) + ']', Address - self.m_Offset, self.m_DataType)
		return RetValue
			
	def fp_ExtractType(self):
		
		ValueType = fg_GetValueType(self.m_Tree)
		pNode = fg_GetStaticFromSBValue(self.m_ValueObject, "mp_Data.m_Tree.ms_pNode", ValueType, "ms_pNode")
		if not fg_IsValidSBValue(pNode):
			return False
		DataType = pNode.GetType().GetPointeeType()
		DataType = DataType.GetCanonicalType()
		
		NodeType = self.m_Root.GetType().GetPointeeType().GetUnqualifiedType()
		NodeType = NodeType.GetCanonicalType()

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)
		
		self.m_DataType = DataType
		self.m_NodeType = NodeType
		
		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "mp_Data.m_Tree.ms_OffsetTCAVLTreeAggregate", ValueType, "ms_OffsetTCAVLTreeAggregate")
		if not fg_IsValidSBValue(Offset):
			return False
		self.m_Offset = Offset.GetValueAsUnsigned()

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
			if self.m_iStack.GetValueAsSigned() >= 0:
				Address = self.m_pStack.GetChildAtIndex(self.m_iStack.GetValueAsUnsigned()%92).GetValueAsUnsigned()
				self.m_Value = self.m_Iter.CreateValueFromAddress('[Current]', Address - self.m_Offset, self.m_DataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		
		ValueType = fg_GetValueType(self.m_Iter)
		pNode = fg_GetStaticFromSBValue(self.m_ValueObject, "mp_Iter.ms_pTree->ms_pNode", ValueType, "ms_pNode")
		if not fg_IsValidSBValue(pNode):
			return False
		DataType = pNode.GetType().GetPointeeType()
		DataType = DataType.GetCanonicalType()
		
		NodeType = self.m_pStack.GetChildAtIndex(0).GetType().GetUnqualifiedType()
		NodeType = NodeType.GetCanonicalType()

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)
		
		self.m_DataType = DataType
		self.m_NodeType = NodeType

		Offset = fg_GetStaticFromSBValue(self.m_ValueObject, "mp_Iter.ms_pTree->ms_OffsetTCAVLTreeAggregate", ValueType, "ms_OffsetTCAVLTreeAggregate")
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
		if self.m_iStack.GetValueAsSigned() < 0:
			return 0
		return 1 + self.m_NumExtraChildren


def fg_SummaryProvider_TCMapTreeMember(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		KeyMember = _Value.GetChildMemberWithName('m_Key')
		KeySummary = KeyMember.GetSummary()
		if KeySummary == None:
			KeySummary = KeyMember.GetValue()

		ValueMember = _Value.GetChildMemberWithName('m_Data')
		
		if ValueMember == None or not ValueMember.IsValid():
			Value = KeySummary;
		else:
			ValueSummary = ValueMember.GetSummary()
			if ValueSummary == None:
				ValueSummary = ValueMember.GetValue()

			if KeySummary == None:
				if ValueSummary == None:
					return None
				else:
					Value = "? > " + ValueSummary
			else:
				if ValueSummary == None:
					Value = KeySummary + " > ?"
				else:
					Value = KeySummary + " > " + ValueSummary

		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value

	except Exception as error:
		print '(fg_SummaryProvider_TCMapTreeMember) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_MibLLDBInit_AVLTree(_Debugger):

	# Intrusive AVL tree
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate, "(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate, "(^|^const )NMib::NIntrusive::TCAVLTree<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NIntrusive::TCAVLTree<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate_CIterator, "(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::TIterator<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::TIterator<.*>$", True, 1)

	# Map
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, "(^|^const )NMib::NContainer::TCMap<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, "(^|^const )NMib::NContainer::TCSet<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, "(^|^const )NMib::NContainer::TCMapWithPool<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap, "(^|^const )NMib::NContainer::TCSetWithPool<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NContainer::TCMap<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NContainer::TCSet<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NContainer::TCMapWithPool<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerLimited, "(^|^const )NMib::NContainer::TCSetWithPool<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCMap_CIterator, "(^|^const )NMib::NContainer::TCMap<.*>::TCIterator<.*>$", True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCMapTreeMember, "(^|^const )(NMib::NContainer::)TCMapTreeMember<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCMap<.*>::TCIterator<.*>$", True, 1)
	
	return
