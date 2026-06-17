# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_VariantIsVoidType(_Type):
	if _Type is None or not _Type.IsValid():
		return False

	CanonicalType = _Type.GetCanonicalType()
	return CanonicalType.IsValid() and CanonicalType.GetName() == "void"

def fg_VariantGetIndexValue(_ValueObject, _Name, _Value, _Type):
	if _Type is not None and _Type.IsValid() and _Type.GetTypeClass() != lldb.eTypeClassBuiltin:
		Process = _ValueObject.GetProcess()
		Data = lldb.SBData.CreateDataFromUInt64Array(Process.GetByteOrder(), Process.GetAddressByteSize(), [int(_Value)])
		Value = _ValueObject.CreateValueFromData(_Name, Data, _Type)
		if fg_IsValidSBValue(Value):
			return Value

	return fg_GetUnsignedValue(_ValueObject, _Name, _Value)

class CSynthProvider_TCVariantCommon(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		ContainerValue = _ValueObject
		if _ValueObject.GetType().IsPointerType():
			DereferencedValue = _ValueObject.Dereference()
			if fg_IsValidSBValue(DereferencedValue):
				ContainerValue = DereferencedValue
		self.m_ContainerType = fg_GetValidCanonicalType(fg_GetValueType(ContainerValue))

		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NStorage::TCVariantCommon")
		self.m_CurrentValueType = None
		self.m_bCurrentTypeVoid = False
		self.m_DataValue = None

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
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):

		ContainerType = self.m_ContainerType

		Storage = fg_FindRawChild(self.m_ValueObject, 'mp_Storage')
		if not fg_IsValidSBValue(Storage):
			Storage = fg_ChildPath(self.m_ValueObject, 'mp_Storage')
		AlignedStorage = Storage.GetChildMemberWithName('m_Aligned')
		if fg_IsValidSBValue(AlignedStorage):
			self.m_DataValue = AlignedStorage
		else:
			DataStorage = Storage.GetChildMemberWithName('m_Storage')
			if fg_IsValidSBValue(DataStorage):
				self.m_DataValue = DataStorage
			else:
				self.m_DataValue = Storage

		self.m_DataAddress = fg_GetAddressOf(self.m_DataValue)

		CurrentType = fg_FindRawChild(Storage, 'm_CurrentType')
		if not fg_IsValidSBValue(CurrentType):
			CurrentType = Storage.GetChildMemberWithName('m_CurrentType')
		self.m_CurrentTypeType = fg_GetValidCanonicalType(fg_GetValueType(CurrentType))
		self.m_CurrentType = CurrentType.GetValueAsUnsigned()

		self.m_MemberToType = fg_VariantMemberTypesFromType(ContainerType, self.m_ValueObject.GetTarget())

		self.m_CurrentValueType = self.m_MemberToType.get(self.m_CurrentType)
		self.m_bCurrentTypeVoid = fg_VariantIsVoidType(self.m_CurrentValueType)

		self.m_nTypes = 0
		VoidType = ContainerType.GetBasicType(lldb.eBasicTypeVoid)
		for Type in self.m_MemberToType.values():
			fg_PrecacheType(Type)
			if self.m_nTypes > 0:
				if Type != VoidType:
					self.m_nTypes = self.m_nTypes + 1
			else:
				self.m_nTypes = self.m_nTypes + 1

		return True

	def fp_GetChildIndex(self, _Name):
		if self.m_bCurrentTypeVoid:
			if _Name == '[Type]':
				return 0
			if _Name == '[Index]':
				return 1
			return CSynthProvider_Common.fp_GetChildIndex(self, _Name)
		if _Name == '[Value]':
			return 0
		if _Name == '[Type]':
			return 1
		if _Name == '[Index]':
			return 2
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		Type = self.m_CurrentValueType
		if Type is None:
			return None

		if self.m_bCurrentTypeVoid:
			if _iChild == 0:
				return fg_GetStringValue(self.m_ValueObject, '[Type]', Type.GetName())
			if _iChild == 1:
				return fg_VariantGetIndexValue(self.m_ValueObject, '[Index]', self.m_CurrentType, self.m_CurrentTypeType)
			return None

		if _iChild == 0:
			if self.m_DataAddress != 0:
				Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', self.m_DataAddress, Type)
				if fg_IsValidSBValue(Value):
					return Value

			if fg_IsValidSBValue(self.m_DataValue):
				Data = self.m_DataValue.GetData()
				if Data.IsValid() and Data.GetByteSize() > 0:
					Value = self.m_ValueObject.CreateValueFromData('[Value]', Data, Type)
					if fg_IsValidSBValue(Value):
						return Value

			return None
		if _iChild == 1:
			return fg_GetStringValue(self.m_ValueObject, '[Type]', Type.GetName())
		if _iChild == 2:
			return fg_VariantGetIndexValue(self.m_ValueObject, '[Index]', self.m_CurrentType, self.m_CurrentTypeType)
		return None

	def fp_NumChildren(self):
		if self.m_CurrentValueType is None:
			return 0
		if self.m_bCurrentTypeVoid:
			return 2
		return 3

def fg_SummaryProvider_TCVariantCommon(_Value, dict):
	try:
		_Value.SetPreferSyntheticValue(True)
		Type = fg_GetValueType(_Value)
		if Type.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		TypeValue = _Value.GetChildMemberWithName('[Type]')
		if fg_IsValidSBValue(TypeValue):
			TypeSummary = TypeValue.GetSummary()
			if TypeSummary is None:
				TypeSummary = TypeValue.GetValue()
			if TypeSummary is not None and len(TypeSummary) >= 2 and TypeSummary[0] == '"' and TypeSummary[-1] == '"':
				TypeSummary = TypeSummary[1:-1]
			if TypeSummary == '"void"' or TypeSummary == 'void':
				return 'void'

		Current = fg_GetLeafValue(_Value.GetChildMemberWithName('[Value]'))
		if not fg_IsValidSBValue(Current):
			return ''

		if Current.GetType().IsPointerType():
			PointerValue = Current.GetValueAsUnsigned()
			if PointerValue == 0:
				return 'nullptr'

			CurrentDeref = Current.Dereference()
			Summary = CurrentDeref.GetSummary()
			if Summary is not None:
				return hex(PointerValue) + '   ' + Summary

			Value = CurrentDeref.GetValue()
			if Value is not None:
				return hex(PointerValue) + '   ' + str(Value)
		else:
			Summary = Current.GetSummary()
			if Summary is not None:
				return Summary

			Value = Current.GetValue()
			if Value is not None:
				return str(Value)

		ReturnString = '{ '
		Overflow = False
		AddedFirst = False
		for iChild in range(Current.GetNumChildren()):
			Child = Current.GetChildAtIndex(iChild)
			Summary = Child.GetSummary()
			if not Summary:
				Summary = Child.GetValue()
				if Summary:
					Summary = str(Summary)
			if Summary:
				if len(ReturnString) > 64:
					Overflow = True
					break

				if AddedFirst:
					ReturnString += ', '

				AddedFirst = True
				ReturnString += Child.GetName() + ' = ' + Summary

		if Overflow:
			ReturnString += ', ... }'
		else:
			ReturnString += ' }'

		return ReturnString
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_TCVariantCommon) error: ', error, ' path: ', _Value.get_expr_path())
		return None

def fg_MibLLDBInit_Variant(_Debugger):

	# TCVariant

	fg_AddSynth(_Debugger, CSynthProvider_TCVariantCommon, "(^|^const )NMib::NStorage::TCVariant<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCVariantCommon, "(^|^const )NMib::NStorage::TCVariantCommon<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCVariantCommon, "(^|^const )NMib::NStorage::TCVariant<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCVariantCommon, "(^|^const )NMib::NStorage::TCVariantCommon<.*>$", True)

	return
