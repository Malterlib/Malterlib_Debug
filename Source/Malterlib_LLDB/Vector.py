# Copyright © 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


class CSynthProvider_TCVector(CSynthProvider_Container):
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
			self.m_pData = fg_ChildPath(self.m_ValueObject, 'm_StaticData.m_pData.m_pPtr')
			
			if self.m_pData.GetValueAsUnsigned() == 0:
				self.m_pDataAddress = 0
			else:
				self.m_pDataAddress = self.m_pData.GetValueAsUnsigned() + self.m_pData.GetType().GetPointeeType().GetByteSize()
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ContainerGetChildAtIndex(self, _iChild):
		if self.m_pDataAddress == 0:
			return None
		Address = self.m_pDataAddress + self.m_DataSize * _iChild
		return self.m_ValueObject.CreateValueFromAddress('[' + str(_iChild) + ']', Address, self.m_DataType)

	def fp_ExtractType(self):
		
		ContainerType = fg_GetValueType(self.m_ValueObjectDeref)
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = DataType.GetCanonicalType()
		else:
			return False

		fg_PrecacheType(DataType)
		self.m_DataType = DataType
			
		return True

	def fp_ContainerNumChildren(self):
		Data = self.m_pData.Dereference()
		nChildren = Data.GetValueForExpressionPath('.m_InternalData.m_Length').GetValueAsUnsigned()
		return nChildren


class CSynthProvider_TCVector_CIterator(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Current = self.m_ValueObject.GetChildMemberWithName('m_Begin')
			self.m_NumExtraChildren = 0
			self.m_Value = None
			if self.m_Current.GetValueAsUnsigned() != 0:
				self.m_Value = self.m_ValueObject.CreateValueFromAddress('[Current]', self.m_Current.GetValueAsUnsigned(), self.m_Current.GetType().GetPointeeType())
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

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


def fg_MibLLDBInit_Vector(_Debugger):

	# Vector
	fg_AddSynth(_Debugger, CSynthProvider_TCVector, "(^|^const )NMib::NContainer::TCVector<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Container, "(^|^const )NMib::NContainer::TCVector<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCVector_CIterator, "(^|^const )NMib::NContainer::TCVectorIterator<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NContainer::TCVectorIterator<.*>$", True)

	return
