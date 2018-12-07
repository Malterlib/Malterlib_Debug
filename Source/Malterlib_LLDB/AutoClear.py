# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


class CSynthProvider_TCAutoClear(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = self.m_ValueObjectDeref.GetChildMemberWithName('m_Value')
			if not self.fp_ExtractType():
				return
			if self.m_DataType.IsPointerType():
				if self.m_Value.GetValueAsUnsigned() != 0:
					self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			else:
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		self.m_DataType = self.m_Value.GetType()
		fg_PrecacheType(self.m_DataType)		
		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Current]':
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			return self.m_ValueObject.CreateValueFromAddress('[Current]', self.m_Value.AddressOf().GetValueAsUnsigned(), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

class CSynthProvider_TCAutoClearInt(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = self.m_ValueObjectDeref.GetChildMemberWithName('m_Int')
			if not self.fp_ExtractType():
				return
			if self.m_DataType.IsPointerType():
				if self.m_Value.GetValueAsUnsigned() != 0:
					self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			else:
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		self.m_DataType = self.m_Value.GetType()
		fg_PrecacheType(self.m_DataType)		
		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Current]':
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			return self.m_ValueObject.CreateValueFromAddress('[Current]', self.m_Value.AddressOf().GetValueAsUnsigned(), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

def fg_MibLLDBInit_AutoClear(_Debugger):
	
	fg_AddSynth(_Debugger, CSynthProvider_TCAutoClear, "(^|^const )NMib::TCAutoClear<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCAutoClearInt, "(^|^const )NMib::TCAutoClearInt<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::TCAutoClear<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::TCAutoClearInt<.*>$", True)

	return
