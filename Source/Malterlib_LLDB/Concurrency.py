# Copyright (C) 2019 Nonna Holding AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

class CSynthProvider_TCActor(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		self.m_RefCount = None
		self.m_WeakRefCount = None
		self.m_ActorType = None
		self.m_Value = None
		self.m_ActorHolder = None
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
			self.m_ActorHolder = None
			self.m_NumExtraChildren = 0
			self.m_RefCount = None
			self.m_WeakRefCount = None
			self.m_DataType = None
			self.m_ActorType = None

			Temp = self.m_ValueObject.GetNonSyntheticValue().GetChildMemberWithName('m_pInternalActor')

			if Temp.GetType().IsPointerType():
				self.m_ActorHolder = Temp
			else:
				self.m_ActorHolder = fg_ChildPath(Temp, 'm_Data.m_pPointTo')

			self.m_ActorHolderDataType = fg_GetPointerValueType(self.m_ActorHolder)
			if self.m_ActorHolder.GetValueAsUnsigned() != 0:
				self.m_ActorType = fg_ChildPath(self.m_ActorHolder, 'm_ActorTypeName')
				self.m_ActorTypeType = fg_GetValueType(self.m_ActorType)
				self.m_RefCount = fg_ChildPath(self.m_ActorHolder, 'm_RefCount.__a_.__a_value')
				self.m_WeakRefCount = fg_ChildPath(self.m_ActorHolder, 'm_WeakRefCount.__a_.__a_value')
				self.m_Value = fg_ChildPath(self.m_ActorHolder, 'mp_pActor.m_Data.m_pPointTo')
				if self.m_Value != None:
					self.m_DataType = fg_GetPointerValueType(self.m_Value)
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
		if _Name == '[Type]':
			return self.m_NumExtraChildren + 1
		if _Name == '[ActorHolder]':
			return self.m_NumExtraChildren + 2
		if _Name == '[Count]':
			return self.m_NumExtraChildren + 3
		if _Name == '[WeakCount]':
			return self.m_NumExtraChildren + 4
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			if self.m_Value != None:
				return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', fg_GetValueAddress(self.m_Value), self.m_DataType)
		if _iChild == self.m_NumExtraChildren + 1:
			if self.m_ActorType != None:
				return fg_CreateDynamicValue(self.m_ValueObject, '[Type]', fg_GetValueAddress(self.m_ActorType), self.m_ActorTypeType)
		if _iChild == self.m_NumExtraChildren + 2:
			if self.m_ActorHolder != None:
				return fg_CreateDynamicValue(self.m_ValueObject, '[ActorHolder]', fg_GetValueAddress(self.m_ActorHolder), self.m_ActorHolderDataType)
		elif _iChild == self.m_NumExtraChildren + 3:
			if self.m_RefCount != None:
				Data = lldb.SBData.CreateDataFromSInt64Array(self.m_Endianness, self.m_PointerSize, [int(1 + self.m_RefCount.GetValueAsSigned())])
				return self.m_ValueObject.CreateValueFromData('[Count]', Data, self.m_CountType)
		elif _iChild == self.m_NumExtraChildren + 4:
			if self.m_WeakRefCount != None:
				Data = lldb.SBData.CreateDataFromSInt64Array(self.m_Endianness, self.m_PointerSize, [int(self.m_WeakRefCount.GetValueAsSigned())])
				return self.m_ValueObject.CreateValueFromData('[WeakCount]', Data, self.m_CountType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 5 + self.m_NumExtraChildren

class CSynthProvider_ActorHolder(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
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
			self.m_Value = fg_GetBaseValue(self.m_ValueObject, 'NMib::NConcurrency::CActorHolder')
			if fg_IsValidSBValue(self.m_Value):
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();
				self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return self.m_NumExtraChildren

def fg_SummaryProvider_TCActor(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		Temp = _Value.GetNonSyntheticValue().GetChildMemberWithName('m_pInternalActor')

		if Temp.GetType().IsPointerType():
			Current = Temp
		else:
			Current = fg_ChildPath(Temp, 'm_Data.m_pPointTo')

		if not fg_IsValidSBValue(Current):
			return None

		Summary = Current.GetSummary()

		Type = _Value.GetChildMemberWithName('[Type]')
		if fg_IsValidSBValue(Type):
			TypeSummary = Type.GetSummary()
		else:
			TypeSummary = None

		if Summary != None and TypeSummary != None:
			return Summary + " " + TypeSummary
		elif TypeSummary != None:
			return TypeSummary

		return Summary
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_Pointer) error: ', error, ' path: ', _Value.get_expr_path())
		return

class CSynthProvider_CThisActor(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = self.m_ValueObjectDeref.GetChildMemberWithName('m_pThis')
			self.m_Value = fg_GetLeafValue(self.m_Value)
			if not self.fp_ExtractType():
				return
			self.m_NumExtraChildren = self.m_Value.GetNumChildren();
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		self.m_DataType = self.m_Value.GetType()
		fg_PrecacheType(self.m_DataType)
		return True

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


def fg_MibLLDBInit_Concurrency(_Debugger):
	
	fg_AddSynth(_Debugger, CSynthProvider_TCActor, "(^|^const )NMib::NConcurrency::TCActor<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_ActorHolder, "(^|^const )NMib::NConcurrency::TCActorInternal<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_CThisActor, "(^|^const )NMib::NConcurrency::NPrivate::CThisActor$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCActor, "(^|^const )NMib::NConcurrency::TCActor<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NConcurrency::NPrivate::CThisActor$", True)

	return
