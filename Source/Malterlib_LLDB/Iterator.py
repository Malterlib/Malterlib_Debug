# Copyright (C) 2015 Hansoft AB
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *
from .String import *

class CSynthProvider_TCRange(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Front = self.m_ValueObject.GetChildMemberWithName('mp_Front')
			self.m_Back = self.m_ValueObject.GetChildMemberWithName('mp_Back')
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if _Name == 'mp_Front':
			return 0
		if _Name == 'mp_Back':
			return 1
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			return self.m_Front
		elif 1:
			return self.m_Back
		return None

	def fp_NumChildren(self):
		return 2

class CSynthProvider_TCIterator(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			Parent = self.m_ValueObject.GetNonSyntheticValue().GetChildAtIndex(0)
			ParentType = Parent.GetType()
			while ParentType.GetName().startswith("NMib::NIterator::TCIterator"):
				Parent = Parent.GetChildAtIndex(0)
				ParentType = Parent.GetType()

			self.m_Parent = Parent
			self.m_ParentType = ParentType
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Imp]':
			return 0
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			return fg_CreateDynamicValue(self.m_ValueObject, '[Imp]', fg_GetAddressOf(self.m_Parent), self.m_ParentType)
		return None

	def fp_NumChildren(self):
		return 1

def fg_SummaryProvider_TCIterator(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Imp = _Value.GetChildMemberWithName('[Imp]')
		if not fg_IsValidSBValue(Imp):
			return None

		Summary = Imp.GetSummary()
		return Summary
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCIterator) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_IsCh8Type(_Type):
	if _Type == lldb.eBasicTypeChar:
		return True
	if _Type == lldb.eBasicTypeSignedChar:
		return True
	if _Type == lldb.eBasicTypeUnsignedChar:
		return True
	return False

def fg_IsCh16Type(_Type):
	if _Type == lldb.eBasicTypeChar16:
		return True
	return False

def fg_IsCh32Type(_Type):
	if _Type == lldb.eBasicTypeChar32:
		return True
	if _Type == lldb.eBasicTypeSignedWChar:
		return True
	if _Type == lldb.eBasicTypeUnsignedWChar:
		return True
	return False

def fg_SummaryProvider_TCRange(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Front = _Value.GetChildMemberWithName('mp_Front')
		if not fg_IsValidSBValue(Front):
			return None
		Back = _Value.GetChildMemberWithName('mp_Back')
		if fg_IsValidSBValue(Back):
			FrontArray = Front.GetChildMemberWithName('mp_pArray')
			Parent = Front
			while not fg_IsValidSBValue(FrontArray) and fg_IsValidSBValue(Parent):
				Parent = Parent.GetNonSyntheticValue().GetChildAtIndex(0)
				FrontArray = Parent.GetChildMemberWithName('mp_pArray')

			BackArray = Back.GetChildMemberWithName('mp_pArray')
			Parent = Back
			while not fg_IsValidSBValue(BackArray) and fg_IsValidSBValue(Parent):
				Parent = Parent.GetNonSyntheticValue().GetChildAtIndex(0)
				BackArray = Parent.GetChildMemberWithName('mp_pArray')

			if fg_IsValidSBValue(FrontArray) and fg_IsValidSBValue(BackArray):
				FrontArrayType = FrontArray.GetType()
				BackArrayType = BackArray.GetType()
				if FrontArrayType.IsPointerType() and BackArrayType.IsPointerType():
					FrontArrayType = FrontArrayType.GetPointeeType()
					BackArrayType = BackArrayType.GetPointeeType()
					FrontBasicType = FrontArrayType.GetBasicType()
					BackBasicType = BackArrayType.GetBasicType()
					BackAddress = fg_GetValueAddress(BackArray)
					FrontAddress = fg_GetValueAddress(FrontArray)
					bReverse = BackAddress < FrontAddress
					if bReverse:
						Temp = FrontAddress
						FrontAddress = BackAddress
						BackAddress	= Temp
						Temp = FrontArray
						FrontArray = BackArray
						BackArray = Temp
					Length = BackAddress - FrontAddress
					if fg_IsCh8Type(FrontBasicType) and fg_IsCh8Type(BackBasicType):
						if bReverse:
							FrontArray = _Value.CreateValueFromExpression("[TempData]", "(char *)" + hex(FrontAddress + 1));
						#FrontArray = _Value.CreateValueFromAddress("[TempData]", FrontAddress + 1, _Value.GetType().GetBasicType(lldb.eBasicTypeChar).GetPointerType())
						return fg_SummaryProvider_Str_ArrayPtr_ch8(FrontArray, None, int(Length))
					elif fg_IsCh16Type(FrontBasicType) and fg_IsCh16Type(BackBasicType):
						if bReverse:
							FrontArray = _Value.CreateValueFromExpression("[TempData]", "(char16_t *)" + hex(FrontAddress + 2));
						#FrontArray = _Value.CreateValueFromAddress("[TempData]", FrontAddress + 2, _Value.GetType().GetBasicType(lldb.eBasicTypeChar16).GetPointerType())
						return fg_SummaryProvider_Str_ArrayPtr_ch16(FrontArray, None, int(Length/2))
					elif fg_IsCh32Type(FrontBasicType) and fg_IsCh32Type(BackBasicType):
						if bReverse:
							FrontArray = _Value.CreateValueFromExpression("[TempData]", "(char32_t *)" + hex(FrontAddress + 4));
						#FrontArray = _Value.CreateValueFromAddress("[TempData]", FrontAddress + 4, _Value.GetType().GetBasicType(lldb.eBasicTypeChar32).GetPointerType())
						return fg_SummaryProvider_Str_ArrayPtr_ch32(FrontArray, None, None, int(Length/4))

		Summary = Front.GetSummary()
		return Summary
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCRange) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_TCArrayIterator(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Array = _Value.GetChildMemberWithName("mp_pArray")
		if not fg_IsValidSBValue(Array):
			return None

		Summary = Array.GetSummary()
		return Summary
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCArrayIterator) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_TCIterator_UTFAdaptor(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		Parent = _Value
		Current = Parent.GetChildMemberWithName('mp_iCurrent')
		while not fg_IsValidSBValue(Current) and fg_IsValidSBValue(Parent):
			Parent = Parent.GetNonSyntheticValue().GetChildAtIndex(0)
			Current = Parent.GetChildMemberWithName('mp_iCurrent')

		if not fg_IsValidSBValue(Current):
			return None

		Summary = Current.GetSummary()
		return Summary
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCArrayIterator) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CNullTerminatedBackIterator(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		return "Null terminated sentinel"
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCArrayIterator) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_Iterator(_Debugger):

	# Iterator
	fg_AddSynth(_Debugger, CSynthProvider_TCIterator, "(^|^const )NMib::NIterator::TCIterator<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCRange, "(^|^const )NMib::NIterator::TCRange<.*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_TCIterator, "(^|^const )NMib::NIterator::TCIterator<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCRange, "(^|^const )NMib::NIterator::TCRange<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCArrayIterator, "(^|^const )NMib::NIterator::TCArrayIterator<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCIterator_UTFAdaptor, "(^|^const )NMib::NStr::TCIterator_UTF8Adaptor<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCIterator_UTFAdaptor, "(^|^const )NMib::NStr::TCIterator_UTF16Adaptor<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCIterator_UTFAdaptor, "(^|^const )NMib::NStr::TCIterator_UTF8AdaptorWithBackward<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCIterator_UTFAdaptor, "(^|^const )NMib::NStr::TCIterator_UTF16AdaptorWithBackward<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CNullTerminatedBackIterator, "(^|^const )NMib::NStr::CNullTerminatedBackIterator$", True)


	return

