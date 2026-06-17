# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys
from .Common import *
from .StringHelpers import *

def fg_GetCodeAddressDetailsForAddress(_Value, _AddressValue):
	Details = {
		'Address': 0,
		'Function': None,
		'File': None,
		'Line': None,
		'Module': None,
	}

	Details['Address'] = _AddressValue

	if _AddressValue == 0:
		Details['Function'] = 'nullptr'
		return Details

	Target = _Value.GetTarget()
	if Target is None or not Target.IsValid():
		return Details

	Address = Target.ResolveLoadAddress(_AddressValue)
	if not Address.IsValid():
		return Details

	Module = Address.GetModule()
	if Module and Module.IsValid():
		FileSpec = Module.GetPlatformFileSpec()
		if FileSpec and FileSpec.IsValid():
			Details['Module'] = FileSpec.GetFilename()
			Details['Function'] = 'Unknown in ' + Details['Module']

	Function = Address.GetFunction()
	if Function.IsValid():
		FullName = Function.GetDisplayName()
		if FullName:
			Details['Function'] = fg_ExtractFunctionName(FullName)
		if not Details['Function']:
			Details['Function'] = Function.GetName()

	if not Details['Function']:
		Symbol = Address.GetSymbol()
		if Symbol.IsValid():
			FullName = Symbol.GetDisplayName()
			if FullName:
				Details['Function'] = fg_ExtractFunctionName(FullName)
			if not Details['Function']:
				Details['Function'] = Symbol.GetName()

	LineEntry = Address.GetLineEntry()
	if LineEntry.IsValid():
		FileSpec = LineEntry.GetFileSpec()
		if FileSpec.IsValid():
			Details['File'] = FileSpec.fullpath
		Line = LineEntry.GetLine()
		if Line != 0:
			Details['Line'] = str(Line)

	return Details

def fg_GetCodeAddressDetails(_Value, _AddressValue = None):
	if _AddressValue is None:
		_AddressValue = fg_GetValueAsUnsigned(_Value)

	Details = fg_GetCodeAddressDetailsForAddress(_Value, _AddressValue)

	if _AddressValue != 0 and (Details['File'] is None or Details['Line'] is None):
		AdjustedDetails = fg_GetCodeAddressDetailsForAddress(_Value, _AddressValue - 1)
		if AdjustedDetails['File'] is not None and AdjustedDetails['Line'] is not None:
			if Details['Function'] is None or Details['Function'].startswith('Unknown'):
				Details['Function'] = AdjustedDetails['Function']
			if Details['Module'] is None:
				Details['Module'] = AdjustedDetails['Module']
			Details['File'] = AdjustedDetails['File']
			Details['Line'] = AdjustedDetails['Line']
			Details['Address'] = _AddressValue

	return Details

def fg_FormatCodeAddressSummary(_Value, _AddressValue = None, _bIncludeAddress = False):
	Details = fg_GetCodeAddressDetails(_Value, _AddressValue)
	Summary = None

	if Details['Function'] is not None:
		Summary = Details['Function']
	elif Details['Address'] != 0:
		Summary = 'Unknown'
	else:
		Summary = 'nullptr'

	if Details['File'] is not None and Details['Line'] is not None:
		Summary += ' - ' + Details['File'] + ':' + Details['Line']

	if _bIncludeAddress:
		return hex(Details['Address']) + '   ' + Summary
	return Summary

class CSynthProvider_CMibCodeAddress(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)
		self.m_Details = None

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.m_ValueObjectType.IsPointerType():
				return
			if not fg_IsValidSBValue(self.m_ValueObject):
				return;
			self.m_Details = fg_GetCodeAddressDetails(self.m_ValueObject)
			self.m_bValid = True
		except Exception as error:
			fg_PrintException()
			fg_PrintError('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Function]':
			return 0
		if _Name == '[File]':
			return 1
		if _Name == '[Line]':
			return 2
		if _Name == '[Address]':
			return 3
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if self.m_Details is None:
			self.m_Details = fg_GetCodeAddressDetails(self.m_ValueObject)
		if _iChild == 0:
			return fg_GetStringValue(self.m_ValueObject, '[Function]', self.m_Details['Function'] if self.m_Details['Function'] is not None else 'Unknown')
		elif _iChild == 1:
			return fg_GetStringValue(self.m_ValueObject, '[File]', self.m_Details['File'] if self.m_Details['File'] is not None else 'Unknown')
		elif _iChild == 2:
			return fg_GetStringValue(self.m_ValueObject, '[Line]', self.m_Details['Line'] if self.m_Details['Line'] is not None else 'Unknown')
		elif _iChild == 3:
			return fg_GetStringValue(self.m_ValueObject, '[Address]', hex(self.m_Details['Address']))
		return None

	def fp_NumChildren(self):
		return 4

def fg_SummaryProvider_CCodeAddressFunction(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Details = fg_GetCodeAddressDetails(_Value)
		return Details['Function'] if Details['Function'] is not None else 'Unknown'
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CCodeAddressFunction) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CCodeAddressFile(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Details = fg_GetCodeAddressDetails(_Value)
		return Details['File'] if Details['File'] is not None else 'Unknown'
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CCodeAddressFile) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CCodeAddressLine(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Details = fg_GetCodeAddressDetails(_Value)
		return Details['Line'] if Details['Line'] is not None else 'Unknown'
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CCodeAddressLine) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_ExtractFunctionName(full_name):
	"""Extract just the function name from a full C++ function signature."""
	if not full_name:
		return None

	def fp_FindParameterStart(_String, _Start = 0):
		TemplateCount = 0
		for i in range(_Start, len(_String)):
			c = _String[i]
			if c == '<':
				TemplateCount += 1
			elif c == '>' and TemplateCount > 0:
				TemplateCount -= 1
			elif c == '(' and TemplateCount == 0:
				return i
		return -1

	def fp_FindLastScopeSeparator(_String):
		TemplateCount = 0
		LastScope = -1
		i = 0
		while i + 1 < len(_String):
			c = _String[i]
			if c == '<':
				TemplateCount += 1
			elif c == '>' and TemplateCount > 0:
				TemplateCount -= 1
			elif c == ':' and _String[i + 1] == ':' and TemplateCount == 0:
				LastScope = i
				i += 1
			i += 1
		return LastScope

	def fp_RemoveTopLevelTemplates(_String):
		if _String.startswith('operator'):
			for i in range(len('operator'), len(_String)):
				if _String[i] == '<':
					if i > len('operator'):
						return _String[:i]
					return _String
			return _String

		TemplateCount = 0
		Return = ''
		for c in _String:
			if c == '<':
				TemplateCount += 1
				continue
			if c == '>' and TemplateCount > 0:
				TemplateCount -= 1
				continue
			if TemplateCount == 0:
				Return += c
		return Return

	if '::operator()' in full_name or full_name.startswith('operator()'):
		op_idx = full_name.find('operator()')
		if op_idx != -1:
			param_idx = fp_FindParameterStart(full_name, op_idx + len('operator()'))
			if param_idx != -1:
				full_name = full_name[:param_idx]
	else:
		param_idx = fp_FindParameterStart(full_name)
		if param_idx != -1:
			full_name = full_name[:param_idx]

	LastScope = fp_FindLastScopeSeparator(full_name)
	if LastScope != -1:
		full_name = full_name[LastScope + 2:]

	return fp_RemoveTopLevelTemplates(full_name).strip()

def fg_SummaryProvider_CMibCodeAddress(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		return fg_FormatCodeAddressSummary(_Value)
	except Exception as error:
		fg_PrintException()
		fg_PrintError('(fg_SummaryProvider_CMibCodeAddress) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_MibLLDBInit_StackTrace(_Debugger):

	fg_AddSynth(_Debugger, CSynthProvider_CMibCodeAddress, "CMibCodeAddressType *")
	fg_AddSynth(_Debugger, CSynthProvider_CMibCodeAddress, "CMibCodeAddressType *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CMibCodeAddress, "CMibCodeAddressType *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CMibCodeAddress, "CMibCodeAddressType *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CCodeAddressFunction, "CMibCodeAddressType::CCodeAddressFunction *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CCodeAddressFunction, "CMibCodeAddressType::CCodeAddressFunction *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CCodeAddressFile, "CMibCodeAddressType::CCodeAddressFile *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CCodeAddressFile, "CMibCodeAddressType::CCodeAddressFile *const")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CCodeAddressLine, "CMibCodeAddressType::CCodeAddressLine *")
	fg_AddSummary(_Debugger, fg_SummaryProvider_CCodeAddressLine, "CMibCodeAddressType::CCodeAddressLine *const")

	return
