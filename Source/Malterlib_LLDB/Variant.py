# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from Common import *
from StringHelpers import *

def fg_ParseTemplate(_String):
	stack = []
	lastStart = 0
	for i, c in enumerate(_String):
		if c == ',' and len(stack) == 1:
			yield _String[lastStart: i].strip()
			lastStart = i + 1
		if c == '<':
			stack.append(i)
			if len(stack) == 1:
				lastStart = i + 1
		elif c == '>' and stack:
			stack.pop()
			if len(stack) == 0:
				yield _String[lastStart: i].strip()

class CSynthProvider_TCStreamableVariant(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NStorage::TCStreamableVariant")

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
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):

		ContainerType = self.m_ValueObjectType

		self.m_DataAddress = fg_GetAddressOf(fg_ChildPath(self.m_ValueObject, 'm_Storage.m_Aligned'))
		CurrentType = fg_ChildPath(self.m_ValueObject, 'm_Storage.m_CurrentType')
		self.m_CurrentTypeType = fg_GetValidCanonicalType(fg_GetValueType(CurrentType))
		self.m_CurrentType = CurrentType.GetValueAsUnsigned()

		TemplateString = ContainerType.GetName()
		TemplateParams = list(fg_ParseTemplate(TemplateString))

		nTypes = (len(TemplateParams) - 1) / 2;

		self.m_MemberToIndex = {};
		self.m_Types = []

		EnumeratorToValue = {};

		EnumeratorType = ContainerType.GetTemplateArgumentType(0)
		EnumMembers = ContainerType.GetTemplateArgumentType(0).GetEnumMembers()
		if EnumMembers != None:
			for iEnum in range(EnumMembers.GetSize()):
				Member = EnumMembers.GetTypeEnumMemberAtIndex(iEnum)
				EnumeratorToValue[Member.GetName()] = Member.GetValueAsSigned()

		for iType in range(nTypes):
			TemplateParam = TemplateParams[2 + iType * 2];
			TemplateParam = TemplateParam.split("::")[-1]

			if fg_IsInteger(TemplateParam):
				EnumValue = int(TemplateParam)
			else:
				EnumValue = EnumeratorToValue.get(TemplateParam);

			self.m_MemberToIndex[EnumValue] = iType
			self.m_Types.append(fg_GetValidCanonicalType(ContainerType.GetTemplateArgumentType(1 + iType*2)))

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
			if MemberIndex == None:
				return None
			Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', self.m_DataAddress, self.m_Types[MemberIndex])
			return Value
		if _iChild == 1:
			MemberIndex = self.m_MemberToIndex.get(self.m_CurrentType);
			if MemberIndex == None:
				return None
			return fg_GetStringValue(self.m_ValueObject, '[Type]', self.m_Types[MemberIndex].GetName())
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
