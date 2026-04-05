# Copyright © Unbroken AB
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import lldb, traceback, sys, os
from .Common import *
from .StringHelpers import *

g_CodeAddress_File = None
g_CodeAddress_Line = None
g_CodeAddress_Function = None

class CSynthProvider_CMibCodeAddress(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.m_ValueObjectType.IsPointerType():
				return
			if not fg_IsValidSBValue(self.m_ValueObject):
				return;
			#print('self.m_ValueObjectType: ', self.m_ValueObjectType.GetName())
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print('(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path())
			return

	def fp_ExtractType(self):
		global g_CodeAddress_File
		global g_CodeAddress_Line
		global g_CodeAddress_Function

		ValueObject = self.m_ValueObjectDeref
		ValueType = ValueObject.GetType()
		if not g_CodeAddress_File:
			MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_File')
			if MemberFunctionHelper:
				g_CodeAddress_File = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
				if not g_CodeAddress_File:
					return False
		if not g_CodeAddress_Line:
			MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_Line')
			if MemberFunctionHelper:
				g_CodeAddress_Line = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
				if not g_CodeAddress_Line:
					return False
		if not g_CodeAddress_Function:
			MemberFunctionHelper = fg_GetMemberFunction(ValueType, 'fs_Debug_Function')
			if MemberFunctionHelper:
				g_CodeAddress_Function = fg_GetValidCanonicalType(MemberFunctionHelper.GetReturnType())
				if not g_CodeAddress_Function:
					return False

		return True

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
		if _iChild == 0:
			Address = self.m_ValueObject.Dereference().GetAddress()
			if Address.IsValid() and Address.GetModule():
				return self.m_ValueObject.CreateValueFromAddress('[Function]', self.m_ValueObject.GetValueAsUnsigned(), g_CodeAddress_Function)
			else:
				return self.m_ValueObject.CreateValueFromAddress('[Function]', 0, g_CodeAddress_Function)
		elif _iChild == 1:
			Address = self.m_ValueObject.Dereference().GetAddress()
			if Address.IsValid() and Address.GetModule():
				return self.m_ValueObject.CreateValueFromAddress('[File]', self.m_ValueObject.GetValueAsUnsigned(), g_CodeAddress_File)
			else:
				return self.m_ValueObject.CreateValueFromAddress('[File]', 0, g_CodeAddress_File)
		elif _iChild == 2:
			Address = self.m_ValueObject.Dereference().GetAddress()
			if Address.IsValid() and Address.GetModule():
				return self.m_ValueObject.CreateValueFromAddress('[Line]', self.m_ValueObject.GetValueAsUnsigned(), g_CodeAddress_Line)
			else:
				return self.m_ValueObject.CreateValueFromAddress('[Line]', 0, g_CodeAddress_Line)
		elif _iChild == 3:
			return self.m_ValueObject.CreateValueFromAddress('[Address]', fg_GetAddressOf(self.m_ValueObject), g_CodeAddress_Line.GetBasicType(lldb.eBasicTypeVoid).GetPointerType())
		return None

	def fp_NumChildren(self):
		return 4

def fg_SummaryProvider_CCodeAddressFunction(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Address = _Value.GetAddress()
		if Address.IsValid() and Address.GetModule() and _Value.GetValueAsUnsigned() != 0:
			Function = Address.GetFunction()
			if Function.IsValid():
				return Function.GetName() + " +" + str(Address.GetOffset() - Function.GetStartAddress().GetOffset())
		if Address.IsValid() and Address.GetModule():
			return "Unknown in " + Address.GetModule().GetPlatformFileSpec().GetFilename()
		else:
			return "Unknown"
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_CCodeAddressFunction) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CCodeAddressFile(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Address = _Value.GetAddress()
		if Address.IsValid() and Address.GetModule() and _Value.GetValueAsUnsigned() != 0:
			LineEntry = Address.GetLineEntry()
			if LineEntry.IsValid():
				FileSpec = LineEntry.GetFileSpec()
				if FileSpec.IsValid():
					return FileSpec.fullpath
		return "Unknown"
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_CCodeAddressFile) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_SummaryProvider_CCodeAddressLine(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())
		Address = _Value.GetAddress()
		if Address.IsValid() and Address.GetModule() and _Value.GetValueAsUnsigned() != 0:
			LineEntry = Address.GetLineEntry()
			if LineEntry.IsValid():
				return str(LineEntry.GetLine())
		return "Unknown"
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_CCodeAddressLine) error: ', error, ' path: ', _Value.get_expr_path())
		return

def fg_ExtractFunctionName(full_name):
	"""Extract just the function name from a full C++ function signature."""
	if not full_name:
		return None

	# Special handling for operator() - we need to keep the first () as part of the name
	if '::operator()' in full_name or full_name.startswith('operator()'):
		# Find operator() and skip past it before looking for parameters
		op_idx = full_name.find('operator()')
		if op_idx != -1:
			# Start looking for parameters after 'operator()'
			search_start = op_idx + len('operator()')
			if '(' in full_name[search_start:]:
				param_idx = full_name.index('(', search_start)
				full_name = full_name[:param_idx]
	else:
		# Normal function - remove parameter list by finding matching parentheses
		paren_count = 0
		template_count = 0
		param_start = -1

		for i, c in enumerate(full_name):
			if c == '<':
				template_count += 1
			elif c == '>':
				template_count -= 1
			elif c == '(' and template_count == 0:
				if param_start == -1:
					param_start = i
				paren_count += 1
			elif c == ')' and template_count == 0:
				paren_count -= 1
				if paren_count == 0 and param_start != -1:
					# Found the end of parameters, truncate here
					full_name = full_name[:param_start]
					break

	# Now remove template parameters
	template_count = 0
	template_start = -1

	for i, c in enumerate(full_name):
		if c == '<':
			if template_count == 0:
				template_start = i
			template_count += 1
		elif c == '>':
			template_count -= 1
			if template_count == 0 and template_start != -1:
				# Found a complete template, remove it
				full_name = full_name[:template_start] + full_name[i+1:]
				break

	# Extract just the function name after the last '::'
	if '::' in full_name:
		parts = full_name.split('::')
		function_name = parts[-1]
	else:
		function_name = full_name

	# Clean up any remaining whitespace
	return function_name.strip()

def fg_SummaryProvider_CMibCodeAddress(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return hex(_Value.GetValueAsUnsigned())

		Current = _Value.GetChildMemberWithName('[File]')
		FileSummary = Current.GetSummary()
		if FileSummary is None:
			Value = Current.GetValue()
			if Value is not None:
				FileSummary = str(Value)

		Current = _Value.GetChildMemberWithName('[Line]')
		LineSummary = Current.GetSummary()
		if LineSummary is None:
			Value = Current.GetValue()
			if Value is not None:
				LineSummary = str(Value)

		Address = Current.GetAddress()
		FunctionName = "Unknown"
		if Address.IsValid() and Address.GetModule():
			FunctionName = "Unknown in " + Address.GetModule().GetPlatformFileSpec().GetFilename()
		if Address.IsValid() and Address.GetModule() and _Value.GetValueAsUnsigned() != 0:
			Function = Address.GetFunction()
			if Function.IsValid():
				FullName = Function.GetDisplayName()
				if FullName:
					FunctionName = fg_ExtractFunctionName(FullName)
				if not FunctionName:
					FunctionName = Function.GetName()

		if FunctionName is not None and FileSummary is not None and LineSummary is not None and FileSummary != "Unknown" and LineSummary != "Unknown":
			return FunctionName + " - " + FileSummary + ":" + LineSummary

		if FunctionName is not None:
			return FunctionName;

		return None
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print('(fg_SummaryProvider_CMibCodeAddress) error: ', error, ' path: ', _Value.get_expr_path())
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
