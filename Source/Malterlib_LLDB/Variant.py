# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

class CSynthProvider_TCVariantCommon(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NStorage::TCVariantCommon")

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ContainerType = self.m_ValueObjectType

		self.m_DataAddress = fg_GetAddressOf(fg_ChildPath(self.m_ValueObject, 'mp_Storage.m_Aligned'))
		CurrentType = fg_ChildPath(self.m_ValueObject, 'mp_Storage.m_CurrentType')
		self.m_CurrentTypeType = fg_GetValidCanonicalType(fg_GetValueType(CurrentType))
		self.m_CurrentType = CurrentType.GetValueAsUnsigned()

		TemplateString = ContainerType.GetName()
		TemplateParams = list(fg_ParseTemplate(TemplateString))

		nTypes = self.m_ValueObjectType.GetNumberOfDirectBaseClasses()

		self.m_MemberToIndex = {};
		self.m_Types = []


		for iType in range(nTypes):
			MemberType = self.m_ValueObjectType.GetDirectBaseClassAtIndex(iType).GetType()
			MemberParams = list(fg_ParseTemplate(MemberType.GetName()))

			if not fg_IsInteger(MemberParams[0]):
				continue

			EnumValue = int(MemberParams[0])
			self.m_MemberToIndex[EnumValue] = iType
			Type = fg_GetValidCanonicalType(MemberType.GetTemplateArgumentType(1))

			self.m_Types.append(Type)

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
		if _Name == '[Value]':
			return 0
		if _Name == '[Type]':
			return 1
		if _Name == '[Index]':
			return 2
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			MemberIndex = self.m_MemberToIndex.get(self.m_CurrentType);
			if MemberIndex is None:
				return None
			Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', self.m_DataAddress, self.m_Types[MemberIndex])
			return Value
		if _iChild == 1:
			MemberIndex = self.m_MemberToIndex.get(self.m_CurrentType);
			if MemberIndex is None:
				return None
			return fg_GetStringValue(self.m_ValueObject, '[Type]', self.m_Types[MemberIndex].GetName())
		if _iChild == 2:
			MemberIndex = self.m_MemberToIndex.get(self.m_CurrentType);
			if MemberIndex is None:
				return None
			if self.m_CurrentTypeType.GetTypeClass() == lldb.eTypeClassBuiltin:
				return self.m_ValueObject.CreateValueFromExpression('[Index]', str(self.m_CurrentType))
			return self.m_ValueObject.CreateValueFromExpression('[Index]', '(' + self.m_CurrentTypeType.GetName() + ')' + str(self.m_CurrentType))
		return None

	def fp_NumChildren(self):
		return 3

def fg_MibLLDBInit_Variant(_Debugger):
	
	# TCVariant
	
	fg_AddSynth(_Debugger, CSynthProvider_TCVariantCommon, "(^|^const )NMib::NStorage::TCVariant<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCVariantCommon, "(^|^const )NMib::NStorage::TCVariantCommon<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NStorage::TCVariant<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NStorage::TCVariantCommon<.*>$", True)

	return
