# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

gc_MaxPThreadKey = 4096
gc_WindowsThreadLocalSlots = 256
gc_ThreadLocalFlagFastThreadLocal = 4

def fg_ThreadLocalAddressMask(_AddressSize):
	return (1 << (_AddressSize * 8)) - 1

def fg_ThreadLocalIsInvalidAddress(_Address, _AddressSize):
	InvalidAddress = fg_ThreadLocalAddressMask(_AddressSize)
	return _Address == 0 or _Address == InvalidAddress

def fg_ThreadLocalSignExtend(_Value, _AddressSize):
	Bits = _AddressSize * 8
	Mask = (1 << Bits) - 1
	_Value &= Mask
	SignBit = 1 << (Bits - 1)
	if (_Value & SignBit) != 0:
		return _Value - (1 << Bits)
	return _Value

def fg_ThreadLocalReadPointer(_Process, _Address):
	AddressSize = _Process.GetAddressByteSize()
	_Address &= fg_ThreadLocalAddressMask(AddressSize)
	if fg_ThreadLocalIsInvalidAddress(_Address, AddressSize):
		return None

	Error = lldb.SBError()
	Pointer = _Process.ReadPointerFromMemory(_Address, Error)
	if not Error.Success() or fg_ThreadLocalIsInvalidAddress(Pointer, AddressSize):
		return None
	return Pointer

def fg_ThreadLocalNameBase(_Name):
	return _Name.split('::')[-1]

def fg_ThreadLocalQualifiedName(_Name, _Prefix):
	if _Prefix is None or _Prefix == '':
		return _Name
	if '::' in _Name:
		return _Name
	return _Prefix.rstrip(':') + '::' + _Name

def fg_ThreadLocalNameMatches(_Name, _CandidateName):
	if _CandidateName is None:
		return False
	if _CandidateName == _Name:
		return True
	if _Name.endswith('::' + _CandidateName):
		return True
	if _CandidateName.endswith('::' + _Name):
		return True
	return False

def fg_ThreadLocalIsInvalidLoadAddress(_Address):
	return _Address is None or _Address == 0 or _Address == 0xffffffffffffffff

def fg_ThreadLocalGetLoadAddress(_Value):
	try:
		Address = _Value.GetLoadAddress()
		if type(Address) is int and not fg_ThreadLocalIsInvalidLoadAddress(Address):
			return Address
	except Exception:
		pass

	try:
		Address = fg_GetAddressOf(_Value)
		if type(Address) is int and not fg_ThreadLocalIsInvalidLoadAddress(Address):
			return Address
	except Exception:
		pass

	return None

def fg_ThreadLocalGetSymbolLoadAddress(_Target, _Symbol):
	try:
		Address = _Symbol.GetStartAddress().GetLoadAddress(_Target)
		if type(Address) is int and not fg_ThreadLocalIsInvalidLoadAddress(Address):
			return Address
	except Exception:
		pass

	return None

def fg_ThreadLocalFindGlobals(_Target, _Name, _MaxMatches = 64):
	if _Target is None:
		return []

	Globals = []
	LookupNames = [_Name]
	BaseName = fg_ThreadLocalNameBase(_Name)
	if BaseName != _Name:
		LookupNames.append(BaseName)

	for LookupName in LookupNames:
		try:
			Values = _Target.FindGlobalVariables(LookupName, _MaxMatches)
			if Values is not None:
				for iValue in range(Values.GetSize()):
					Value = Values.GetValueAtIndex(iValue)
					if fg_IsValidSBValue(Value):
						Globals.append(Value)
		except Exception:
			pass

	return Globals

def fg_ThreadLocalFindGlobal(_Target, _Name):
	Globals = fg_ThreadLocalFindGlobals(_Target, _Name)
	if len(Globals) == 0:
		return None

	SymbolAddress = fg_ThreadLocalFindDataSymbolAddress(_Target, _Name)
	if SymbolAddress is not None:
		for Value in Globals:
			if fg_ThreadLocalGetLoadAddress(Value) == SymbolAddress:
				return Value

	for Value in Globals:
		if fg_ThreadLocalNameMatches(_Name, Value.GetName()):
			return Value

	BaseName = fg_ThreadLocalNameBase(_Name)
	for Value in Globals:
		if fg_ThreadLocalNameMatches(BaseName, Value.GetName()):
			return Value

	return Globals[0]

def fg_ThreadLocalFindDataSymbols(_Target, _Name, _MaxMatches = 64):
	if _Target is None:
		return []

	Symbols = []
	LookupNames = [_Name]
	BaseName = fg_ThreadLocalNameBase(_Name)
	if BaseName != _Name:
		LookupNames.append(BaseName)

	for LookupName in LookupNames:
		try:
			SymbolContexts = _Target.FindSymbols(LookupName, lldb.eSymbolTypeData)
		except Exception:
			continue

		if SymbolContexts is None:
			continue

		for iSymbolContext in range(min(SymbolContexts.GetSize(), _MaxMatches)):
			Symbol = SymbolContexts.GetContextAtIndex(iSymbolContext).GetSymbol()
			if Symbol is not None and Symbol.IsValid():
				Symbols.append(Symbol)

	return Symbols

def fg_ThreadLocalFindDataSymbol(_Target, _Name):
	Symbols = fg_ThreadLocalFindDataSymbols(_Target, _Name)
	if len(Symbols) == 0:
		return None

	for Symbol in Symbols:
		if fg_ThreadLocalNameMatches(_Name, Symbol.GetName()):
			return Symbol

	BaseName = fg_ThreadLocalNameBase(_Name)
	for Symbol in Symbols:
		if fg_ThreadLocalNameMatches(BaseName, Symbol.GetName()):
			return Symbol

	return Symbols[0]

def fg_ThreadLocalFindDataSymbolAddress(_Target, _Name):
	Symbol = fg_ThreadLocalFindDataSymbol(_Target, _Name)
	if Symbol is None:
		return None

	return fg_ThreadLocalGetSymbolLoadAddress(_Target, Symbol)

def fg_ThreadLocalReadGlobalValueUnsigned(_Value):
	try:
		Value = fg_GetValueAsUnsigned(_Value)
		if type(Value) is int:
			return Value
	except Exception:
		pass

	return None

def fg_ThreadLocalReadGlobalUnsigned(_ValueObject, _Names, _Prefix = None):
	Process = _ValueObject.GetProcess()
	Target = Process.GetTarget()
	Names = [fg_ThreadLocalQualifiedName(Name, _Prefix) for Name in _Names]

	for Name in Names:
		Value = fg_ThreadLocalFindGlobal(Target, Name)
		if fg_IsValidSBValue(Value):
			Value = fg_ThreadLocalReadGlobalValueUnsigned(Value)
			if type(Value) is int:
				return Value

	return None

def fg_ThreadLocalGlobalExists(_ValueObject, _Names):
	Target = _ValueObject.GetProcess().GetTarget()
	for Name in _Names:
		if fg_ThreadLocalFindGlobal(Target, Name) is not None:
			return True
	return False

def fg_ThreadLocalGlobalOrSymbolExists(_ValueObject, _Names):
	Target = _ValueObject.GetProcess().GetTarget()
	for Name in _Names:
		if fg_ThreadLocalFindGlobal(Target, Name) is not None:
			return True

		try:
			SymbolContexts = Target.FindSymbols(Name, lldb.eSymbolTypeAny)
		except Exception:
			continue

		if SymbolContexts is not None and SymbolContexts.GetSize() > 0:
			return True

	return False

class CSynthProvider_TCThreadLocal(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return

			self.m_ThreadLocalObject = self.m_ValueObjectDeref
			if self.m_ValueObject.GetType().IsReferenceType():
				self.m_ThreadLocalObject = self.m_ValueObject.Dereference()
				if not fg_IsValidSBValue(self.m_ThreadLocalObject):
					return

			self.m_NumExtraChildren = 0
			self.m_ThreadLocal = None

			ThreadLocalIndex = fg_GetValueAsUnsigned(self.m_ThreadLocalObject.GetChildMemberWithName('m_ThreadLocalLocal'))

			if ThreadLocalIndex != 0:
				self.fp_GetThreadLocalFromThreadPointer(ThreadLocalIndex)

			if not self.fp_ExtractType():
				return

			if self.m_ThreadLocal is not None:
				self.m_Value = fg_CreateDynamicValue(self.m_ValueObject, '[TempData]', self.m_ThreadLocal, self.m_DataType)
				self.m_Value = fg_GetLeafValue(self.m_Value)
				self.m_ValueDataType = self.m_Value.GetType()
				fg_PrecacheType(self.m_ValueDataType)
				self.m_NumExtraChildren = self.m_Value.GetNumChildren();

			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		ContainerType = fg_GetValueType(self.m_ThreadLocalObject)
		if ContainerType.GetNumberOfTemplateArguments() > 0:
			DataType = ContainerType.GetTemplateArgumentType(0)
			DataType = fg_GetValidCanonicalType(DataType)
		else:
			return False

		fg_PrecacheType(DataType)

		self.m_DataType = DataType
		return True

	def fp_GetThreadLocalFromThreadPointer(self, _ThreadLocalIndex):
		Process = self.m_ValueObject.GetProcess()
		Target = Process.GetTarget()
		Triple = Target.GetTriple().lower()

		Thread = Process.GetSelectedThread()
		if not hasattr(Thread, 'GetThreadPointer'):
			return False

		AddressSize = Process.GetAddressByteSize()
		ThreadPointer = Thread.GetThreadPointer()
		if fg_ThreadLocalIsInvalidAddress(ThreadPointer, AddressSize):
			return True

		if 'apple' in Triple or 'darwin' in Triple:
			return self.fp_GetDarwinThreadLocalFromThreadPointer(ThreadPointer, _ThreadLocalIndex)

		if 'windows' in Triple or 'msvc' in Triple:
			return self.fp_GetWindowsThreadLocalFromThreadPointer(ThreadPointer, _ThreadLocalIndex)

		if 'linux' in Triple:
			return self.fp_GetLinuxThreadLocalFromThreadPointer(ThreadPointer, _ThreadLocalIndex)

		return False

	def fp_GetDarwinThreadLocalFromThreadPointer(self, _ThreadPointer, _ThreadLocalIndex):
		if _ThreadLocalIndex >= gc_MaxPThreadKey:
			return True

		Process = self.m_ValueObject.GetProcess()
		AddressSize = Process.GetAddressByteSize()
		Addresses = [_ThreadPointer + _ThreadLocalIndex * AddressSize]

		ThreadLocalOffsetPThread = fg_ThreadLocalReadGlobalUnsigned(
			self.m_ValueObject,
			[
				'NMib::NSys::g_ThreadLocalOffsetPThread',
				'NSys::g_ThreadLocalOffsetPThread',
				'g_ThreadLocalOffsetPThread',
			]
		)
		if ThreadLocalOffsetPThread is not None:
			Addresses.append(_ThreadPointer + ThreadLocalOffsetPThread + _ThreadLocalIndex * AddressSize)

		TriedAddresses = set()
		for Address in Addresses:
			if Address in TriedAddresses:
				continue
			TriedAddresses.add(Address)

			ThreadLocal = fg_ThreadLocalReadPointer(Process, Address)
			if ThreadLocal is not None:
				self.m_ThreadLocal = ThreadLocal
				return True

		return True

	def fp_GetLinuxThreadLocalFromThreadPointer(self, _ThreadPointer, _ThreadLocalIndex):
		if not fg_ThreadLocalGlobalOrSymbolExists(
			self.m_ValueObject,
			[
				'g_MalterlibLinuxThreadLocalsAreThreadPointerRelative',
				'::g_MalterlibLinuxThreadLocalsAreThreadPointerRelative',
			]
		):
			return False

		Process = self.m_ValueObject.GetProcess()
		AddressSize = Process.GetAddressByteSize()
		ThreadLocalOffset = fg_ThreadLocalSignExtend(_ThreadLocalIndex, AddressSize)
		ThreadLocal = fg_ThreadLocalReadPointer(Process, _ThreadPointer + ThreadLocalOffset)
		if ThreadLocal is not None:
			self.m_ThreadLocal = ThreadLocal
		return True

	def fp_GetWindowsThreadLocalFromThreadPointer(self, _ThreadPointer, _ThreadLocalIndex):
		if self.fp_HasFastThreadLocalFlag():
			return self.fp_GetWindowsFastThreadLocalFromThreadPointer(_ThreadPointer, _ThreadLocalIndex)

		if _ThreadLocalIndex >= gc_WindowsThreadLocalSlots:
			return True

		ThreadLocalsExtendedLocationOffset = fg_ThreadLocalReadGlobalUnsigned(
			self.m_ValueObject,
			[
				'ms_ThreadLocalsExtendedLocactionOffset',
			],
			'NMib::NThread::NPlatform::CWindowsThreadLocals'
		)
		if ThreadLocalsExtendedLocationOffset is None:
			return False

		Process = self.m_ValueObject.GetProcess()
		AddressSize = Process.GetAddressByteSize()
		ThreadLocals = fg_ThreadLocalReadPointer(Process, _ThreadPointer + ThreadLocalsExtendedLocationOffset)
		if ThreadLocals is not None:
			ThreadLocal = fg_ThreadLocalReadPointer(Process, ThreadLocals + _ThreadLocalIndex * AddressSize)
			if ThreadLocal is not None:
				self.m_ThreadLocal = ThreadLocal

		return True

	def fp_GetWindowsFastThreadLocalFromThreadPointer(self, _ThreadPointer, _ThreadLocalIndex):
		Process = self.m_ValueObject.GetProcess()
		MinOffset = fg_ThreadLocalReadGlobalUnsigned(
			self.m_ValueObject,
			[
				'ms_ThreadLocalsMinOffset',
			],
			'NMib::NThread::NPlatform::CWindowsThreadLocals'
		)
		MaxOffset = fg_ThreadLocalReadGlobalUnsigned(
			self.m_ValueObject,
			[
				'ms_ThreadLocalsMaxOffset',
			],
			'NMib::NThread::NPlatform::CWindowsThreadLocals'
		)
		if MinOffset is not None and MaxOffset is not None and (_ThreadLocalIndex < MinOffset or _ThreadLocalIndex > MaxOffset):
			return True

		ThreadLocal = fg_ThreadLocalReadPointer(Process, _ThreadPointer + _ThreadLocalIndex)
		if ThreadLocal is not None:
			self.m_ThreadLocal = ThreadLocal
		return True

	def fp_HasFastThreadLocalFlag(self):
		TypeName = fg_GetValueType(self.m_ThreadLocalObject).GetName()
		if TypeName is None:
			return False

		if 'EThreadLocalFlag_FastThreadLocal' in TypeName:
			return True

		TemplateArguments = list(fg_ParseTemplate(TypeName))
		if len(TemplateArguments) == 0:
			return False

		FlagArgument = TemplateArguments[-1]
		if 'FastThreadLocal' in FlagArgument:
			return True

		FlagNumber = ''
		for Char in FlagArgument:
			if Char >= '0' and Char <= '9':
				FlagNumber += Char
			elif FlagNumber != '':
				try:
					if (int(FlagNumber) & gc_ThreadLocalFlagFastThreadLocal) != 0:
						return True
				except Exception:
					pass
				FlagNumber = ''

		if FlagNumber != '':
			try:
				return (int(FlagNumber) & gc_ThreadLocalFlagFastThreadLocal) != 0
			except Exception:
				pass

		return False

	def fp_GetChildIndex(self, _Name):
		if self.m_ThreadLocal is None or self.m_DataType is None:
			if _Name == '[Empty]':
				return self.m_NumExtraChildren
		else:
			if _Name == '[Value]':
				return self.m_NumExtraChildren

		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == self.m_NumExtraChildren:
			if self.m_ThreadLocal is None or self.m_DataType is None:
				return fg_GetStringValue(self.m_ValueObject, '[Empty]', 'Thread-local value not materialized')
			else:
				return fg_CreateDynamicValue(self.m_ValueObject, '[Value]', self.m_ThreadLocal, self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren


def fg_MibLLDBInit_ThreadLocal(_Debugger):

	fg_AddSynth(_Debugger, CSynthProvider_TCThreadLocal, "(^|^const )NMib::NThread::TCThreadLocal<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NThread::TCThreadLocal<.*>$", True)

	fg_AddSynth(_Debugger, CSynthProvider_TCThreadLocal, "(^|^const )NMib::NThread::TCThreadLocalDynamic<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NThread::TCThreadLocalDynamic<.*>$", True)

	return
