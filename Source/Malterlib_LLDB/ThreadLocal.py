# Copyright © 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *



class CSynthProvider_TCThreadLocal(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			ThreadLocalIndex = self.m_ValueObject.GetChildMemberWithName('m_ThreadLocalLocal').GetValueAsUnsigned();
			if ThreadLocalIndex != 0:
				self.m_ThreadLocal = self.m_ValueObject.CreateValueFromExpression("[TempData]", "fg_Debug_GetThreadLocal(" + str(ThreadLocalIndex) + ")").GetValueAsUnsigned()
				if self.m_ThreadLocal == 0:
					self.m_ThreadLocal = None
			else:
				self.m_ThreadLocal = None
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

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

	def fp_GetChildIndex(self, _Name):
		if self.m_ThreadLocal == None or self.m_DataType == None:
			if _Name == '[Invalid]':
				return 0
		else:
			if _Name == '[Current]':
				return 0
		
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			if self.m_ThreadLocal == None or self.m_DataType == None:
				return self.m_ValueObject.CreateValueFromAddress('[Invalid]', 0, self.m_DataType)
			else:
				return self.m_ValueObject.CreateValueFromAddress('[Current]', self.m_ThreadLocal, self.m_DataType)
		return None

	def fp_NumChildren(self):
		return 1


def fg_MibLLDBInit_ThreadLocal(_Debugger):
	
	fg_AddSynth(_Debugger, CSynthProvider_TCThreadLocal, "(^|^const )NMib::NThread::TCThreadLocal<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NThread::TCThreadLocal<.*>$", True)
	
	fg_AddSynth(_Debugger, CSynthProvider_TCThreadLocal, "(^|^const )NMib::NThread::TCThreadLocalDynamic<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NThread::TCThreadLocalDynamic<.*>$", True)
	
	return

