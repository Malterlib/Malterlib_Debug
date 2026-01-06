# Copyright (C) 2015 Hansoft AB
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

class CSynthProvider_TCJsonValueBase(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NEncoding::NPrivate::TCJsonValueBase")

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return
			self.m_NumExtraChildren = 0

			self.m_Value = self.m_ValueObject.GetChildMemberWithName('mp_Value')
			CurrentType = self.m_Value.GetValueForExpressionPath('.mp_Storage.m_CurrentType')

			if CurrentType.GetValueAsUnsigned() == 0:
				self.m_bEmpty = True
				self.m_bValid = True
				return;

			self.m_bEmpty = False

			self.m_Value = self.m_Value.CreateValueFromAddress("[TempData]", fg_GetValueAddress(self.m_Value), fg_GetValidCanonicalType(self.m_Value.GetType()))

			fg_PrecacheType(self.m_Value.GetType())

			self.m_Value = fg_GetLeafValue(self.m_Value)
			self.m_DataType = self.m_Value.GetType()
			fg_PrecacheType(self.m_DataType)
			self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if (not self.m_bEmpty and _Name == '[Value]') or (self.m_bEmpty and _Name == '[Empty]'):
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			if self.m_bEmpty:
				return fg_GetEmptyValue(self.m_ValueObject, "Invalid")
			else:
				return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

class CSynthProvider_TCJsonObject(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NEncoding::TCJsonObject")

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return
			self.m_NumExtraChildren = 0

			self.m_Value = self.m_ValueObject.GetChildMemberWithName('mp_ObjectTree')
			self.m_Value = self.m_Value.CreateValueFromAddress("[TempData]", fg_GetValueAddress(self.m_Value), fg_GetValidCanonicalType(self.m_Value.GetType()))

			fg_PrecacheType(self.m_Value.GetType())

			self.m_DataType = self.m_Value.GetType()
			fg_PrecacheType(self.m_DataType)
			self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

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

class CSynthProvider_TCObjectEntry(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary, "NMib::NEncoding::NPrivate::TCObjectEntry")

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return

			self.m_NumExtraChildren = 0

			self.m_NameValue = self.m_ValueObject.GetValueForExpressionPath('.mp_Name')
			self.m_NameValueDataType = self.m_NameValue.GetType()

			self.m_Value = fg_GetLeafValue(self.m_ValueObject.GetChildMemberWithName('mp_Value'))
			self.m_Value = self.m_Value.CreateValueFromAddress("[TempData]", fg_GetValueAddress(self.m_Value), fg_GetValidCanonicalType(self.m_Value.GetType()))

			fg_PrecacheType(self.m_Value.GetType())

			self.m_DataType = self.m_Value.GetType()
			self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Name]':
			return self.m_NumExtraChildren
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			return self.m_ValueObject.CreateValueFromAddress('[Name]', fg_GetAddressOf(self.m_NameValue), self.m_NameValueDataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

def fg_SummaryProvider_TCObjectEntry(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		NonSynthValue = _Value.GetNonSyntheticValue()
		KeyMember = NonSynthValue.GetValueForExpressionPath('.mp_Name')
		KeySummary = KeyMember.GetSummary()
		if KeySummary is None:
			KeySummary = str(KeyMember.GetValue())


		ValueMember = fg_GetLeafValue(NonSynthValue.GetChildMemberWithName('mp_Value'))

		if ValueMember is None or not ValueMember.IsValid():
			Value = KeySummary;
		else:
			ValueSummary = ValueMember.GetSummary()
			if ValueSummary is None:
				ValueSummary = str(ValueMember.GetValue())

			if ValueSummary == "None":
				ValueSummary = "..."

			if KeySummary is None:
				if ValueSummary is None:
					return None
				else:
					Value = '? > ' + ValueSummary
			else:
				if ValueSummary is None:
					Value = KeySummary + ' > ?'
				else:
					Value = KeySummary + ' > ' + ValueSummary

		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + '   ' + Value
		return Value

	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCObjectEntry) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_TCJsonObject(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		ObjectsMember = _Value.GetValueForExpressionPath('.mp_ObjectTree')
		ObjectsSummary = ObjectsMember.GetSummary()
		return ObjectsSummary;

	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCJsonObject) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CEJsonUserType(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		ObjectsMember = _Value.GetValueForExpressionPath('.m_Type')
		if ObjectsMember is not None:
			ObjectSummary = fg_GetValueRawSummary(ObjectsMember)
			if ObjectSummary is not None:
				return "UserType(" + ObjectSummary + ")"

		return "UserType"

	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_CEJsonUserType) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CJsonBoolean(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		ObjectsMember = _Value.GetValueForExpressionPath('.m_bValue')
		if ObjectsMember.GetValueAsUnsigned():
			return "true"
		else:
			return "false"

	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_CJsonBoolean) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CJsonNull(_Value, dict):
	try:
		return "null";

	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_CJsonNull) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_Json(_Debugger):

	fg_AddSynth(_Debugger, CSynthProvider_TCJsonValueBase, "(^|^const )NMib::NEncoding::TCJsonValue<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCJsonValueBase, "(^|^const )NMib::NEncoding::TCEJsonValue<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NEncoding::TCJsonValue<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NEncoding::TCEJsonValue<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCObjectEntry, "(^|^const )NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCObjectEntry, "(^|^const )NMib::NEncoding::NPrivate::TCObjectEntry<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCJsonObject, "(^|^const )NMib::NEncoding::TCJsonObject<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCJsonObject, "(^|^const )NMib::NEncoding::TCJsonObject<.*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_CJsonBoolean, "(^|^const )NMib::NEncoding::NPrivate::CJsonBoolean$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CJsonNull, "(^|^const )NMib::NEncoding::NPrivate::CJsonNull$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CEJsonUserType, "(^|^const )NMib::NEncoding::CEJsonUserTypeSorted$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CEJsonUserType, "(^|^const )NMib::NEncoding::CEJsonUserTypeOrdered$", True)


	return
