# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

class CSynthProvider_Pointer(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = self.m_ValueObject.GetChildMemberWithName('m_pPointTo')
			self.m_DataType = self.m_Value.GetType()
			fg_PrecacheType(self.m_DataType)
			if self.m_Value.GetValueAsUnsigned() != 0:
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
			return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

class CSynthProvider_TCUniquePointer(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = fg_ChildPath(self.m_ValueObject, 'm_Data.m_pPointTo')
			self.m_DataType = self.m_Value.GetType()
			fg_PrecacheType(self.m_DataType)
			if self.m_Value.GetValueAsUnsigned() != 0:
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
			return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

class CSynthProvider_TCBitStorePointer(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0

			TemplateString = self.m_ValueObjectType.GetName()
			TemplateParams = list(fg_ParseTemplate(TemplateString))
			if not fg_IsInteger(TemplateParams[1]):
				return

			NumBits = int(TemplateParams[1])

			ValueAddress = fg_ChildPath(self.m_ValueObject, 'mp_PointTo').GetValueAsUnsigned()
			ValueType = self.m_ValueObjectType.GetTemplateArgumentType(0)
			self.m_Value = fg_CreateDynamicValue(self.m_ValueObject, '[Value]', ValueAddress << NumBits, ValueType)

			self.m_DataType = self.m_Value.GetType()
			fg_PrecacheType(self.m_DataType)
			if self.m_Value.GetValueAsUnsigned() != 0:
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
			return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

class CSynthProvider_TCSharedPointer(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		self.m_RefCount = None
		self.m_WeakRefCount = None
		self.m_Value = None
		Process = _ValueObject.GetProcess()
		self.m_Endianness = Process.GetByteOrder()
		self.m_PointerSize = Process.GetAddressByteSize()
		self.m_CountType = _ValueObject.GetType().GetBasicType(lldb.eBasicTypeLong)
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_Value = None
			self.m_NumExtraChildren = 0
			self.m_RefCount = None
			self.m_WeakRefCount = None
			self.m_Value = fg_ChildPath(self.m_ValueObject, 'm_Data.m_pPointTo')
			self.m_DataType = fg_GetPointerValueType(self.m_Value)
			fg_PrecacheType(self.m_DataType)
			if self.m_Value.GetValueAsUnsigned() != 0:
				self.m_RefCount = self.m_Value.GetValueForExpressionPath('->m_RefCount.__a_')
				self.m_WeakRefCount = self.m_Value.GetValueForExpressionPath('->m_WeakRefCount.__a_')
				if fg_GetValidCanonicalType(self.m_DataType).GetName().startswith('NMib::NStorage::NPrivate::TCSharedPointerCounter'):
					Data = self.m_Value.GetChildMemberWithName('m_Data')
					self.m_DataType = fg_GetValueType(Data)
					fg_PrecacheType(self.m_DataType)
					self.m_Value = Data
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Value]':
			return self.m_NumExtraChildren
		if _Name == '[Count]':
			return self.m_NumExtraChildren + 1
		if _Name == '[WeakCount]':
			return self.m_NumExtraChildren + 2
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', fg_GetValueAddress(self.m_Value), self.m_DataType)
		elif _iChild == self.m_NumExtraChildren + 1:
			if self.m_RefCount is not None:
				Data = lldb.SBData.CreateDataFromSInt64Array(self.m_Endianness, self.m_PointerSize, [int(1 + self.m_RefCount.GetValueAsSigned())])
				return self.m_ValueObject.CreateValueFromData("[Count]", Data, self.m_CountType)
			else:
				return None
		elif _iChild == self.m_NumExtraChildren + 2:
			if self.m_WeakRefCount is not None:
				Data = lldb.SBData.CreateDataFromSInt64Array(self.m_Endianness, self.m_PointerSize, [int(self.m_WeakRefCount.GetValueAsSigned())])
				return self.m_ValueObject.CreateValueFromData("[WeakCount]", Data, self.m_CountType)
			else:
				return None
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 3 + self.m_NumExtraChildren


def fg_SummaryProvider_Pointer(_Value, dict):
	try:
		_Value.SetPreferSyntheticValue(True)
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Current = _Value.GetChildMemberWithName('[Value]')
		if not fg_IsValidSBValue(Current):
			return None

		PointerValue = fg_GetAddressOf(Current)
		if PointerValue == 0:
			Value = "nullptr";
		else:
			Current = Current.Dereference()

			Summary = Current.GetSummary()
			if Summary is None:
				Value = Current.GetValue()
				if Value is not None:
					Summary = str(Value)

			if Summary is not None:
				Value = hex(PointerValue) + "   " + Summary
			else:
				Value = hex(PointerValue)

		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Pointer) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_TCSharedPointer(_Value, dict):
	try:
		_Value.SetPreferSyntheticValue(True)
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Current = _Value.GetChildMemberWithName('[Value]')
		pValue = fg_ChildPath(_Value, 'm_Data.m_pPointTo')
		PointerValue = pValue.GetValueAsUnsigned()
		if PointerValue == 0:
			Value = "nullptr";
		else:
			if not fg_IsValidSBValue(Current):
				return None
			if Current.GetType().IsPointerType():
				Current = Current.Dereference()
			Summary = Current.GetSummary()
			if Summary is None:
				Value = Current.GetValue()
				if Value is not None:
					Summary = str(Value)
			
			RefCount = _Value.GetChildMemberWithName('[Count]')
			WeakRefCount = _Value.GetChildMemberWithName('[WeakCount]')
			
			if Summary is not None:
				if fg_IsValidSBValue(RefCount):
					if fg_IsValidSBValue(WeakRefCount):
						Value = hex(PointerValue) + " Count: " + str(RefCount.GetValueAsUnsigned()) + " WeakCount: " + str(WeakRefCount.GetValueAsUnsigned()) + "   " + Summary
					else:
						Value = hex(PointerValue) + " Count: " + str(RefCount.GetValueAsUnsigned()) + "   " + Summary
				else:
					if fg_IsValidSBValue(WeakRefCount):
						Value = hex(PointerValue)+ " WeakCount: " + str(WeakRefCount.GetValueAsUnsigned())  + "   " + Summary
					else:
						Value = hex(PointerValue) + "   " + Summary
			else:
				if fg_IsValidSBValue(RefCount):
					if fg_IsValidSBValue(WeakRefCount):
						Value = hex(PointerValue) + " Count: " + str(RefCount.GetValueAsUnsigned()) + " WeakCount: " + str(WeakRefCount.GetValueAsUnsigned())
					else:
						Value = hex(PointerValue) + " Count: " + str(RefCount.GetValueAsUnsigned())
				else:
					if fg_IsValidSBValue(WeakRefCount):
						Value = hex(PointerValue) + " WeakCount: " + str(WeakRefCount.GetValueAsUnsigned())
					else:
						Value = hex(PointerValue)

		if ValueType.IsPointerType():
			return hex(_Value.GetValueAsUnsigned()) + "   " + Value
		return Value
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_TCSharedPointer) error: ', error, ' path: ', _Value.get_expr_path())
		return


def fg_MibLLDBInit_Pointer(_Debugger):
	
	# Pointers
	fg_AddSynth(_Debugger, CSynthProvider_Pointer, "(^|^const )NMib::NStorage::TCAutoClearPtr<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_Pointer, "(^|^const )NMib::NStorage::TCAutoClearPtrDebug<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_Pointer, "(^|^const )NMib::NStorage::TCDebugPointer<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_Pointer, "(^|^const )NMib::NStorage::TCPointer<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCSharedPointer, "(^|^const )NMib::NStorage::TCSharedPointer<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCSharedPointer, "(^|^const )NMib::NStorage::TCWeakPointer<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCUniquePointer, "(^|^const )NMib::NStorage::TCUniquePointer<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCUniquePointer, "(^|^const )NMib::NStorage::NReference::TCReference<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCUniquePointer, "(^|^const )NMib::NStorage::NIndirection::TCIndirection<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCBitStorePointer, "(^|^const )NMib::NStorage::TCBitStorePointer<.*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::TCAutoClearPtr<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::TCAutoClearPtrDebug<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::TCDebugPointer<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::TCPointer<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::TCUniquePointer<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::NReference::TCReference<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::NIndirection::TCIndirection<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_Pointer, "(^|^const )NMib::NStorage::TCBitStorePointer<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCSharedPointer, "(^|^const )NMib::NStorage::TCSharedPointer<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCSharedPointer, "(^|^const )NMib::NStorage::TCWeakPointer<.*>$", True)

	return
