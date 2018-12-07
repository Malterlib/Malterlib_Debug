# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


class CSynthProvider_TCAggregate(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_bConstructed = self.m_ValueObject.GetChildMemberWithName('m_bConstructed')
			self.m_Data = fg_ChildPath(self.m_ValueObject, 'm_ObjectSpace.m_Aligned')
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
		if _Name == '[Current]':
			return 0
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			Address = self.m_Data.AddressOf().GetValueAsUnsigned()
			return self.m_ValueObject.CreateValueFromAddress('[Current]', Address, self.m_DataType)
		return None

	def fp_NumChildren(self):
		if self.m_bConstructed.IsValid() and self.m_bConstructed.GetValueAsUnsigned() == 0:
			return 0
		return 1

def fg_MibLLDBInit_Aggregate(_Debugger):
	
	fg_AddSynth(_Debugger, CSynthProvider_TCAggregate, "(^|^const )NMib::NAggregate::TCAggregate<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NAggregate::TCAggregate<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCAggregate, "(^|^const )NMib::NAggregate::TCAggregateSimple<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NAggregate::TCAggregateSimple<.*>$", True)
		
	return
