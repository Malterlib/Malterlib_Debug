# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb, traceback, sys, os
from Common import *
from StringHelpers import *

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
			#print 'self.m_ValueObjectType: ', self.m_ValueObjectType.GetName()
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			traceback.print_exc(file=sys.stdout)
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
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
			return self.m_ValueObject.CreateValueFromAddress('[Function]', self.m_ValueObject.GetValueAsUnsigned(), g_CodeAddress_Function)
		elif _iChild == 1:
			return self.m_ValueObject.CreateValueFromAddress('[File]', self.m_ValueObject.GetValueAsUnsigned(), g_CodeAddress_File)
		elif _iChild == 2:
			return self.m_ValueObject.CreateValueFromAddress('[Line]', self.m_ValueObject.GetValueAsUnsigned(), g_CodeAddress_Line)
		elif _iChild == 3:
			return self.m_ValueObject.CreateValueFromAddress('[Address]', fg_GetAddressOf(self.m_ValueObject), g_CodeAddress_Line.GetBasicType(lldb.eBasicTypeVoid).GetPointerType())
		return None

	def fp_NumChildren(self):
		return 4

def fg_SummaryProvider_CCodeAddressFunction(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Address = _Value.GetAddress()
		if Address.IsValid():
			Function = Address.GetFunction()
			if Function.IsValid():
				return Function.GetName() + " +" + str(Address.GetOffset() - Function.GetStartAddress().GetOffset())
		return hex(fg_GetAddressOf(_Value))
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print '(fg_SummaryProvider_CCodeAddressFunction) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_SummaryProvider_CCodeAddressFile(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Address = _Value.GetAddress()
		if Address.IsValid():
			LineEntry = Address.GetLineEntry()
			if LineEntry.IsValid():
				FileSpec = LineEntry.GetFileSpec()
				if FileSpec.IsValid():
					return FileSpec.fullpath
		return "Unknown"
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print '(fg_SummaryProvider_CCodeAddressFile) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_SummaryProvider_CCodeAddressLine(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Address = _Value.GetAddress()
		if Address.IsValid():
			LineEntry = Address.GetLineEntry()
			if LineEntry.IsValid():
				return str(LineEntry.GetLine())
		return "Unknown"
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print '(fg_SummaryProvider_CCodeAddressLine) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_SummaryProvider_CMibCodeAddress(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None

		Current = _Value.GetChildMemberWithName('[File]')
		FileSummary = Current.GetSummary()
		if FileSummary == None:
			Value = Current.GetValue()
			if Value != None:
				FileSummary = str(Value)

		Current = _Value.GetChildMemberWithName('[Line]')
		LineSummary = Current.GetSummary()
		if LineSummary == None:
			Value = Current.GetValue()
			if Value != None:
				LineSummary = str(Value)

 		Address = Current.GetAddress()
		FunctionName = "Unknown"
		if Address.IsValid():
			Function = Address.GetFunction()
			if Function.IsValid():
				FunctionName = Function.GetType().GetName()

		if FunctionName != None and FileSummary != None and LineSummary != None and FileSummary != "Unknown" and LineSummary != "Unknown":
			return FunctionName + " - " + os.path.basename(FileSummary) + ":" + LineSummary

		if FunctionName != None:
			return FunctionName;

		return None
	except Exception as error:
		traceback.print_exc(file=sys.stdout)
		print '(fg_SummaryProvider_CMibCodeAddress) error: ', error, ' path: ', _Value.get_expr_path()
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
