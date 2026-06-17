# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *


class CSynthProvider_TCAggregate(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_bConstructed = self.m_ValueObject.GetChildMemberWithName('m_bConstructed')
			if fg_IsValidSBValue(self.m_bConstructed):
				self.m_bEmpty = self.m_bConstructed.GetValueAsUnsigned() == 0
			self.m_Data = fg_ChildPath(self.m_ValueObject, 'm_ObjectSpace')
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
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
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return 0
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			if self.m_bEmpty:
				return fg_GetEmptyValue(self.m_ValueObject, "Not constructed")
			Address = fg_GetAddressOf(self.m_Data)
			return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', Address, self.m_DataType)
		return None

	def fp_NumChildren(self):
		return 1

def fg_MibLLDBInit_Aggregate(_Debugger):

	fg_AddSynth(_Debugger, CSynthProvider_TCAggregate, "(^|^const )NMib::NStorage::TCAggregate<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NStorage::TCAggregate<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCAggregate, "(^|^const )NMib::NStorage::TCAggregateSimple<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NStorage::TCAggregateSimple<.*>$", True)

	return
