# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


class CSynthProvider_TCStreamableVariant(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):

		ContainerType = fg_GetInheritedType(self.m_ValueObjectDeref.GetType(), "NMib::NStorage::TCStreamableVariant")
		if not ContainerType.IsValid():
			return False
		
		self.m_DataAddress = fg_ChildPath(self.m_ValueObject, 'm_Storage.m_Aligned').AddressOf().GetValueAsUnsigned()
		CurrentType = fg_ChildPath(self.m_ValueObject, 'm_Storage.m_CurrentType')
		self.m_CurrentTypeType = fg_GetValueType(CurrentType).GetCanonicalType()
		self.m_CurrentType = CurrentType.GetValueAsUnsigned()

		MemberValues = fg_GetStaticFromSBValueGlobals(self.m_ValueObject, "ms_MemberValues", ContainerType, "CMemberValues")
		
		if not fg_IsValidSBValue(MemberValues):
			MemberValues = fg_GetStaticFromSBValue(self.m_ValueObject, "ms_MemberValues", ContainerType, "ms_MemberValues")
			if not fg_IsValidSBValue(MemberValues):
				return False
		MemberValues = MemberValues.GetChildMemberWithName('m_Values')
		
		nTypes = MemberValues.GetNumChildren();
		self.m_MemberToIndex = {};
		self.m_Types = []
		for iType in range(nTypes):
			self.m_MemberToIndex[MemberValues.GetChildAtIndex(iType).GetValueAsUnsigned()] = iType
			self.m_Types.append(ContainerType.GetTemplateArgumentType(1 + iType*2))
		
		self.m_nTypes = 0
		VoidType = ContainerType.GetBasicType(lldb.eBasicTypeVoid)
		for iType in self.m_Types:
			fg_PrecacheType(iType)
			if self.m_nTypes > 0:
				if iType != VoidType:
					self.m_nTypes = self.m_nTypes + 1
			else:
				self.m_nTypes = self.m_nTypes + 1

		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Current]':
			return 0
		if _Name == '[Type]':
			return 1
		if _Name == '[Index]':
			return 2
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			MemberIndex = self.m_MemberToIndex.get(self.m_CurrentType);
			if MemberIndex == None:
				return None
			return self.m_ValueObject.CreateValueFromAddress('[Current]', self.m_DataAddress, self.m_Types[MemberIndex])
		if _iChild == 1:
			MemberIndex = self.m_MemberToIndex.get(self.m_CurrentType);
			if MemberIndex == None:
				return None
			return self.m_ValueObject.CreateValueFromExpression('[Type]', '"' + self.m_Types[MemberIndex].GetName() + '"')
		if _iChild == 2:
			MemberIndex = self.m_MemberToIndex.get(self.m_CurrentType);
			if MemberIndex == None:
				return None
			if self.m_CurrentTypeType.GetTypeClass() == lldb.eTypeClassBuiltin:
				return self.m_ValueObject.CreateValueFromExpression('[Index]', str(self.m_CurrentType))
			return self.m_ValueObject.CreateValueFromExpression('[Index]', '(' + self.m_CurrentTypeType.GetName() + ')' + str(self.m_CurrentType))
		return None

	def fp_NumChildren(self):
		return 3

def fg_MibLLDBInit_Variant(_Debugger):
	
	# TCVariant
	
	fg_AddSynth(_Debugger, CSynthProvider_TCStreamableVariant, "(^|^const )NMib::NStorage::TCVariant<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCStreamableVariant, "(^|^const )NMib::NStorage::TCStreamableVariant<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NStorage::TCVariant<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NStorage::TCStreamableVariant<.*>$", True)
	
	return
