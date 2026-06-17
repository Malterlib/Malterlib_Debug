# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_ActorGetInternalActorHolder(_Value):
	InternalActor = _Value.GetNonSyntheticValue().GetChildMemberWithName('m_pInternalActor')
	if not fg_IsValidSBValue(InternalActor):
		return None

	if InternalActor.GetType().IsPointerType():
		return InternalActor

	InternalActorHolder = fg_ChildPath(InternalActor, 'm_Data.m_pPointTo')
	if fg_IsValidSBValue(InternalActorHolder):
		return InternalActorHolder

	return None

def fg_ActorGetAtomicValue(_Atomic):
	if not fg_IsValidSBValue(_Atomic):
		return None

	Value = fg_ChildPath(_Atomic, '__a_.__a_value')
	if not fg_IsValidSBValue(Value):
		Value = fg_ChildPath(_Atomic, 'm_Value')
	if not fg_IsValidSBValue(Value) and _Atomic.GetNumChildren() > 0:
		Value = _Atomic.GetChildAtIndex(0).GetChildMemberWithName('m_Value')
	if not fg_IsValidSBValue(Value):
		Value = _Atomic

	return Value

def fg_ActorGetHolderBase(_ActorHolder):
	if not fg_IsValidSBValue(_ActorHolder):
		return None

	if _ActorHolder.GetType().IsPointerType():
		if _ActorHolder.GetValueAsUnsigned() == 0:
			return None
		ActorHolder = _ActorHolder.Dereference()
	else:
		ActorHolder = _ActorHolder

	if not fg_IsValidSBValue(ActorHolder):
		return None

	return fg_GetBaseValue(ActorHolder, 'NMib::NConcurrency::CActorHolder')

def fg_ActorFindHolderChild(_ActorHolderBase, _Name):
	Value = fg_FindRawChild(_ActorHolderBase, _Name)
	if fg_IsValidSBValue(Value):
		return Value
	return None

def fg_ActorCreateValue(_ValueObject, _Name, _Address, _Type):
	Value = _ValueObject.CreateValueFromAddress(_Name, _Address, _Type)
	DynamicValue = Value.GetDynamicValue(lldb.eDynamicDontRunTarget)
	if fg_IsValidSBValue(DynamicValue):
		return DynamicValue
	return Value

def fg_ActorGetStaticActorType(_ValueObject, _FallbackValue):
	Type = fg_GetValueType(_ValueObject)
	ActorType = Type.GetTemplateArgumentType(0)
	if ActorType is not None and ActorType.IsValid():
		return ActorType

	return fg_GetPointerValueType(_FallbackValue)

class CSynthProvider_TCActor(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		self.m_RefCount = None
		self.m_WeakRefCount = None
		self.m_ActorType = None
		self.m_ActorTypeFallback = None
		self.m_Value = None
		self.m_ValueAddress = 0
		self.m_ValueData = None
		self.m_ActorHolder = None
		self.m_ActorHolderAddress = 0
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
			self.m_ActorTypeFallback = None
			self.m_ValueAddress = 0
			self.m_ValueData = None
			self.m_ActorHolderAddress = 0

			self.m_ActorHolder = fg_ActorGetInternalActorHolder(self.m_ValueObject)
			if not fg_IsValidSBValue(self.m_ActorHolder):
				self.m_bValid = True
				return

			self.m_ActorHolderDataType = fg_GetPointerValueType(self.m_ActorHolder)
			self.m_ActorHolderAddress = self.m_ActorHolder.GetValueAsUnsigned()
			if self.m_ActorHolderAddress != 0:
				ActorHolderBase = fg_ActorGetHolderBase(self.m_ActorHolder)
				self.m_ActorType = fg_ActorFindHolderChild(ActorHolderBase, 'm_ActorTypeName')
				if self.m_ActorType is not None:
					self.m_ActorTypeType = fg_GetValueType(self.m_ActorType)

				RefCount = fg_ActorFindHolderChild(ActorHolderBase, 'm_RefCount')
				self.m_RefCount = fg_ActorGetAtomicValue(fg_ActorFindHolderChild(RefCount, 'm_RefCount'))
				self.m_WeakRefCount = fg_ActorGetAtomicValue(fg_ActorFindHolderChild(RefCount, 'm_WeakRefCount'))
				self.m_Value = fg_ActorGetAtomicValue(fg_ActorFindHolderChild(ActorHolderBase, 'mp_pActorUnsafe'))
				if self.m_Value is not None:
					self.m_DataType = fg_ActorGetStaticActorType(self.m_ValueObject, self.m_Value)
					self.m_ActorTypeFallback = self.m_DataType.GetName()
					fg_PrecacheType(self.m_DataType)
					self.m_ValueAddress = self.m_Value.GetValueAsUnsigned()
					if self.m_ValueAddress != 0:
						self.m_ValueData = fg_ActorCreateValue(self.m_ValueObject, '[Value]', self.m_ValueAddress, self.m_DataType)
						self.m_NumExtraChildren = self.m_ValueData.GetNumChildren();

			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
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
			if self.m_ValueData is not None:
				return self.m_ValueData
		if _iChild == self.m_NumExtraChildren + 1:
			if self.m_ActorType is not None:
				return fg_CreateDynamicValue(self.m_ValueObject, '[Type]', fg_GetValueAddress(self.m_ActorType), self.m_ActorTypeType)
			if self.m_ActorTypeFallback is not None:
				return fg_GetStringValue(self.m_ValueObject, '[Type]', self.m_ActorTypeFallback)
		if _iChild == self.m_NumExtraChildren + 2:
			if self.m_ActorHolder is not None:
				return fg_ActorCreateValue(self.m_ValueObject, '[ActorHolder]', self.m_ActorHolderAddress, self.m_ActorHolderDataType)
		elif _iChild == self.m_NumExtraChildren + 3:
			if self.m_RefCount is not None:
				Data = lldb.SBData.CreateDataFromSInt64Array(self.m_Endianness, self.m_PointerSize, [int(1 + self.m_RefCount.GetValueAsSigned())])
				return self.m_ValueObject.CreateValueFromData('[Count]', Data, self.m_CountType)
		elif _iChild == self.m_NumExtraChildren + 4:
			if self.m_WeakRefCount is not None:
				Data = lldb.SBData.CreateDataFromSInt64Array(self.m_Endianness, self.m_PointerSize, [int(self.m_WeakRefCount.GetValueAsSigned())])
				return self.m_ValueObject.CreateValueFromData('[WeakCount]', Data, self.m_CountType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_ValueData.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		if self.m_ActorHolderAddress == 0:
			return 0
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
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
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

		ActorHolder = fg_ActorGetInternalActorHolder(_Value)
		if not fg_IsValidSBValue(ActorHolder):
			return None

		ActorHolderAddress = ActorHolder.GetValueAsUnsigned()
		if ActorHolderAddress == 0:
			return "nullptr"

		Summary = hex(ActorHolderAddress)

		Type = _Value.GetChildMemberWithName('[Type]')
		if fg_IsValidSBValue(Type):
			TypeSummary = Type.GetSummary()
			if TypeSummary is None:
				TypeSummary = Type.GetValue()
		else:
			TypeSummary = None

		RefCount = _Value.GetChildMemberWithName('[Count]')
		WeakRefCount = _Value.GetChildMemberWithName('[WeakCount]')

		if fg_IsValidSBValue(RefCount):
			Summary += " Count: " + str(RefCount.GetValueAsUnsigned())
		if fg_IsValidSBValue(WeakRefCount):
			Summary += " WeakCount: " + str(WeakRefCount.GetValueAsUnsigned())
		if TypeSummary is not None:
			Summary += " " + TypeSummary

		return Summary
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_Pointer) error: ', error, ' path: ', _Value.get_expr_path())
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
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
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
	fg_AddSynth(_Debugger, CSynthProvider_TCActor, "(^|^const )NMib::NConcurrency::TCWeakActor<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_ActorHolder, "(^|^const )NMib::NConcurrency::TCActorInternal<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_CThisActor, "(^|^const )NMib::NConcurrency::NPrivate::CThisActor$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCActor, "(^|^const )NMib::NConcurrency::TCActor<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_TCActor, "(^|^const )NMib::NConcurrency::TCWeakActor<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NConcurrency::NPrivate::CThisActor$", True)

	return
