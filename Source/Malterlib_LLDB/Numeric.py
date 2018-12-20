# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from Common import *
from StringHelpers import *

class CSynthProvider_TCTaggedInteger(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = self.m_ValueObjectDeref.GetChildMemberWithName('mp_Data')
			if not self.fp_ExtractType():
				return
			if self.m_DataType.IsPointerType():
				if self.m_Value.GetValueAsUnsigned() != 0:
					self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			else:
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		self.m_DataType = self.m_Value.GetType()
		fg_PrecacheType(self.m_DataType)		
		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Value]':
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren


def fg_MibLLDBInit_Numeric(_Debugger):
	
	# TCTaggedInteger
	fg_AddSynth(_Debugger, CSynthProvider_TCTaggedInteger, "(^|^const )TCTaggedInteger<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )TCTaggedInteger<.*>$", True)

	return
