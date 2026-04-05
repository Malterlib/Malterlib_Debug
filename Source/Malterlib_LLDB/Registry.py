# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *
from .AVLTree import *

class CSynthProvider_TCRegistry(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		self.m_Value = None
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Data = None
			self.m_Name = None
			self.m_NumExtraChildren = 0
			self.m_Name = fg_ChildPath(self.m_ValueObject, 'mp_Key.m_Name')
			if not fg_IsValidSBValue(self.m_Name):
				return
			self.m_Data = fg_ChildPath(self.m_ValueObject, 'mp_Data')
			if not fg_IsValidSBValue(self.m_Data):
				return
			self.m_NameType = self.m_Name.GetType()
			fg_PrecacheType(self.m_NameType)
			self.m_DataType = self.m_Data.GetType()
			fg_PrecacheType(self.m_DataType)
			self.m_Children = fg_ChildPath(self.m_ValueObject, 'mp_Children.m_Tree')
			if not fg_IsValidSBValue(self.m_Children):
				return
			self.m_ChildrenSynth = CSynthProvider_TCAVLTreeAggregate(self.m_Children, None)
			self.m_ChildrenSynth.update()
			if not self.m_ChildrenSynth.m_bValid:
				self.m_NumExtraChildren = 0
			else:
				self.m_NumExtraChildren = self.m_ChildrenSynth.fp_ContainerNumChildren()
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Key]':
			return self.m_NumExtraChildren
		if _Name == '[Value]':
			return self.m_NumExtraChildren + 1
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			Ret = self.m_ValueObject.CreateValueFromAddress('[Key]', fg_GetAddressOf(self.m_Name), self.m_NameType)
			return Ret
		elif _iChild == self.m_NumExtraChildren + 1:
			return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Data), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_ChildrenSynth.fp_ContainerGetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 2 + self.m_NumExtraChildren


def fg_SummaryProvider_TCRegistry(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		ValueName = fg_ChildPath(_Value, 'mp_Key.m_Name')
		if not fg_IsValidSBValue(ValueName):
			return None
		ValueData = fg_ChildPath(_Value, 'mp_Data')
		if not fg_IsValidSBValue(ValueData):
			return None
		pRootChild = fg_ChildPath(_Value, 'mp_Children.m_Tree.m_Root')
		if not fg_IsValidSBValue(pRootChild):
			return None

		bLeaf = pRootChild.GetValueAsUnsigned() >> 1 == 0

		Name = fg_GetValueRawSummary(ValueName)
		Data = fg_GetValueRawSummary(ValueData)
		if Name is None:
			Name = ""
		if Data is None:
			Data = ""

		if bLeaf:
			Value = '"' + Name + '" "' + Data + '"'
		else:
			Value = '"' + Name + '" "' + Data + '" {'

		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCRegistry) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_Registry(_Debugger):

	# TCRegistry

	fg_AddSynth(_Debugger, CSynthProvider_TCRegistry, "(^|^const )NMib::NContainer::TCRegistry<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCRegistry, "(^|^const )NMib::NContainer::TCRegistry<.*>$", True)

	return
