# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
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
		self.m_Offset = int(self.m_ValueObjectType.GetName().split('<')[1].split(',')[0])

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ValueType = fg_GetValueType(self.m_ValueObjectDeref)
		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_GetTree');
		if not MemberFunctionHelper:
			return False

		AVLTreeType = MemberFunctionHelper.GetReturnType().GetPointeeType()

		DataType = AVLTreeType.GetTemplateArgumentType(3)
		DataType = fg_GetValidCanonicalType(DataType)

		NodeType = self.m_pStack.GetChildAtIndex(0).GetType().GetUnqualifiedType()
		NodeType = fg_GetValidCanonicalType(NodeType)

		self.m_DataType = DataType
		self.m_NodeType = NodeType

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)

		self.m_Offset = int(AVLTreeType.GetName().split('<')[1].split(',')[0])
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
		CSynthProvider_Container.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Container.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Tree = fg_ChildPath(self.m_ValueObject, 'mp_Tree')
			self.m_Root = self.m_Tree.GetValueForExpressionPath('.m_Root')
			if not self.fp_ExtractType():
				return

			self.m_Root = self.m_ValueObject.CreateValueFromAddress('[TempData]', (self.m_Root.GetValueAsUnsigned() >> 2) << 2, self.m_NodeType).AddressOf()

			self.m_DataSize = self.m_DataType.GetByteSize()

			pNode = CSynthProvider_TCAVLTreeAggregate_Node(self.m_Root, self.m_NodeType)
			iNode = CSynthProvider_TCAVLTreeAggregate_Iterator(pNode)

			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ContainerGetChildAtIndex(self, _iChild):
		Address = self.m_ChildMap[_iChild]
		if Address is None or Address < self.m_Offset:
			return None

		RetValue =  fg_CreateDynamicValue(self.m_ValueObject, '[' + str(_iChild) + ']', Address - self.m_Offset, self.m_DataType)
		return RetValue

	def fp_ExtractType(self):

		ValueType = fg_GetInheritedType(fg_GetValueType(self.m_Tree), 'NMib::NIntrusive::TCAVLTreeAggregate')

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_GetNode')
		if not MemberFunctionHelper:
			return False

		DataType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType().GetPointeeType())

		NodeType = self.m_Root.GetType().GetPointeeType().GetUnqualifiedType()
		NodeType = fg_GetValidCanonicalType(NodeType)

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)

		self.m_DataType = DataType
		self.m_NodeType = NodeType

		self.m_Offset = int(ValueType.GetName().split('<')[1].split(',')[0])

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
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ValueType = fg_GetValueType(self.m_Iter)

		MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_GetTree');
		if not MemberFunctionHelper:
			return False

		AVLTreeType = MemberFunctionHelper.GetReturnType().GetPointeeType()

		DataType = AVLTreeType.GetTemplateArgumentType(3)
		DataType = fg_GetValidCanonicalType(DataType)

		NodeType = self.m_pStack.GetChildAtIndex(0).GetType().GetUnqualifiedType()
		NodeType = fg_GetValidCanonicalType(NodeType)

		fg_PrecacheType(DataType)
		fg_PrecacheType(NodeType)

		self.m_DataType = DataType
		self.m_NodeType = NodeType

		self.m_Offset = int(AVLTreeType.GetName().split('<')[1].split(',')[0])

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
		KeySummary = KeyMember.GetSummary()
		if KeySummary is None:
			KeySummary = KeyMember.GetValue()

		ValueMember = _Value.GetChildMemberWithName('m_Value')

		if ValueMember is None or not ValueMember.IsValid():
			Value = KeySummary;
		else:
			ValueSummary = ValueMember.GetSummary()
			if ValueSummary is None:
				ValueSummary = str(ValueMember.GetValue())

			if ValueSummary == "None":
				ValueSummary = "..."

			if KeySummary is None:
				if ValueSummary is None:
					return None
				else:
					Value = '? > ' + ValueSummary
			else:
				Value = KeySummary + ' > ' + ValueSummary

		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + '   ' + Value
		return Value

	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCMapNode) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_AVLTree(_Debugger):

	# Intrusive AVL tree
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate, '(^|^const )NMib::NIntrusive::TCAVLTree<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerMapLimited, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_ContainerMapLimited, '(^|^const )NMib::NIntrusive::TCAVLTree<.*>$', True)
	fg_AddSynth(_Debugger, CSynthProvider_TCAVLTreeAggregate_CIterator, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::TCIterator<.*>$', True, 1)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NIntrusive::TCAVLTreeAggregate<.*>::TCIterator<.*>$', True, 1)

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
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCMapNode, '(^|^const )(NMib::NContainer::)TCMapNode<.*>$', True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, '(^|^const )NMib::NContainer::TCMap<.*>::TCIterator<.*>$', True, 1)

	return
