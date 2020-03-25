# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

class CSynthProvider_TCThreadLocal(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return

			self.m_NumExtraChildren = 0

			Frame = self.m_ValueObject.GetProcess().GetSelectedThread().GetSelectedFrame()

			ThreadLocalIndex = self.m_ValueObject.GetChildMemberWithName('m_ThreadLocalLocal').GetValueAsUnsigned();
			if ThreadLocalIndex != 0 and Frame is not None:
				self.m_ThreadLocal = Frame.EvaluateExpression("fg_Debug_GetThreadLocal(" + str(ThreadLocalIndex) + ")").GetValueAsUnsigned()
				if self.m_ThreadLocal == 0:
					self.m_ThreadLocal = None
			else:
				self.m_ThreadLocal = None

			if not self.fp_ExtractType():
				return

			if self.m_ThreadLocal is not None:
				self.m_Value = fg_CreateDynamicValue(self.m_ValueObject, '[TempData]', self.m_ThreadLocal, self.m_DataType)
				self.m_Value = fg_GetLeafValue(self.m_Value)
				self.m_ValueDataType = self.m_Value.GetType()
				fg_PrecacheType(self.m_ValueDataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();

			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ContainerType = fg_GetValueType(self.m_ValueObjectDeref)
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
		else:
			return False

		fg_PrecacheType(DataType)
		
		self.m_DataType = DataType
		return True

	def fp_GetChildIndex(self, _Name):
		if self.m_ThreadLocal is None or self.m_DataType is None:
			if _Name == '[Empty]':
				return self.m_NumExtraChildren
		else:
			if _Name == '[Value]':
				return self.m_NumExtraChildren
		
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			if self.m_ThreadLocal is None or self.m_DataType is None:
				return self.m_ValueObject.CreateValueFromAddress('[Empty]', 0, self.m_DataType)
			else:
				return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', self.m_ThreadLocal, self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren


def fg_MibLLDBInit_ThreadLocal(_Debugger):
	
	fg_AddSynth(_Debugger, CSynthProvider_TCThreadLocal, "(^|^const )NMib::NThread::TCThreadLocal<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NThread::TCThreadLocal<.*>$", True)
	
	fg_AddSynth(_Debugger, CSynthProvider_TCThreadLocal, "(^|^const )NMib::NThread::TCThreadLocalDynamic<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NThread::TCThreadLocalDynamic<.*>$", True)
	
	return

