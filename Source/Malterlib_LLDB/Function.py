# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_RemovePrefix(_String, _Prefix):
    if _String.startswith(_Prefix):
        return _String[len(_Prefix):]
    return _String

class CSynthProvider_TCFunction(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		self.m_NumExtraChildren = 0
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if self.m_ValueObjectType.IsPointerType():
				return
			self.m_NumExtraChildren = 0
			self.m_Value = None
			self.m_bEmpty = False

			TypeName = self.m_ValueObjectType.GetName()

			VTablePrefix = "."
			StorageName = ".m_Storage"
			StorageOffset = False

			if TypeName.startswith("NMib::NFunction::TCFunctionFastCall<"):
				StorageName = ".m_Data.m_pImpl"
				VTablePrefix = ".m_Data."
			if TypeName.startswith("NMib::NFunction::TCFunctionSmall<"):
				StorageName = ".m_Data.m_pImp"
				StorageOffset = True
				VTablePrefix = ".m_Data.m_pImp->"

			String = self.m_ValueObject.GetValueForExpressionPath(VTablePrefix + 'm_pVTable->m_pFunctorTypeName')
			StringSummary = fg_GetValueRawSummary(String)

			if not StringSummary:
				return

			Module = String.GetAddress().GetModule()

			Type = Module.FindFirstType(StringSummary)
			if not Type:
				ShortType = fg_RemovePrefix(StringSummary, "NMib::NFunction::NPrivate::")
				Type = Module.FindFirstType(ShortType)

			MemberFunctionHelper = fg_GetMemberFunction(Type, 'fs_Debug_GetFunctorType')
			if not MemberFunctionHelper:
				return

			ValueType = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
			if not ValueType:
				return

			ValueType = ValueType.GetPointeeType()

			self.m_bEmpty = ValueType.GetName() == "NMib::NFunction::NPrivate::CNullFunctionImpl"

			Storage = self.m_ValueObject.GetValueForExpressionPath(StorageName)

			if not Storage:
				return

			Address = fg_GetValueAddress(Storage)
			if StorageOffset:
				Address += Storage.GetType().GetPointeeType().GetByteSize()

			self.m_Value = self.m_ValueObject.CreateValueFromAddress("[TempData]", Address, ValueType)

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
		if _iChild == self.m_NumExtraChildren and self.m_Value is not None:
			if self.m_bEmpty:
				return fg_GetEmptyValue(self.m_ValueObject)
			else:
				return self.m_ValueObject.CreateValueFromAddress('[Value]', fg_GetAddressOf(self.m_Value), self.m_DataType)
		elif _iChild < self.m_NumExtraChildren:
			return self.m_Value.GetChildAtIndex(_iChild)
		return None

	def fp_NumChildren(self):
		return 1 + self.m_NumExtraChildren

def fg_MibLLDBInit_Function(_Debugger):
	
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunction<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCMutableFunction<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCMovableFunction<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionFastCall<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionSmall<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_TCFunction, "(^|^const )NMib::NFunction::TCFunctionNoAlloc<.*>$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NFunction::TCFunction<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NFunction::TCMutableFunction<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NFunction::TCMovableFunction<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NFunction::TCFunctionFastCall<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NFunction::TCFunctionSmall<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_IteratorCommon, "(^|^const )NMib::NFunction::TCFunctionNoAlloc<.*>$", True)

	return
