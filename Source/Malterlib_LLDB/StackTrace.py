# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


g_CodeAddress_pFile = None
g_CodeAddress_pLine = None
g_CodeAddress_pFunction = None

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
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		global g_CodeAddress_pFile
		global g_CodeAddress_pLine
		global g_CodeAddress_pFunction
		
		ValueObject = self.m_ValueObjectDeref
		ValueType = ValueObject.GetType()
		pFile = g_CodeAddress_pFile
		if not fg_IsValidSBValue(pFile):
			pFile = self.m_ValueObject.CreateValueFromExpression("[ms_pFile]", ValueType.GetName() + "::ms_pFile")
			if not fg_IsValidSBValue(pFile):
				return False
			g_CodeAddress_pFile = pFile
		pLine = g_CodeAddress_pLine
		if not fg_IsValidSBValue(pLine):
			pLine = self.m_ValueObject.CreateValueFromExpression("[ms_pLine]", ValueType.GetName() + "::ms_pLine")
			if not fg_IsValidSBValue(pLine):
				return False
			g_CodeAddress_pLine = pLine
		pFunction = g_CodeAddress_pFunction
		if not fg_IsValidSBValue(pFunction):
			pFunction = self.m_ValueObject.CreateValueFromExpression("[ms_pFunction]", ValueType.GetName() + "::ms_pFunction")
			if not fg_IsValidSBValue(pFunction):
				return False
			g_CodeAddress_pFunction = pFunction
		self.m_FileType = pFile.GetType()
		self.m_LineType = pLine.GetType()
		self.m_FunctionType = pFunction.GetType()
		
		fg_PrecacheType(self.m_FileType)
		fg_PrecacheType(self.m_LineType)
		fg_PrecacheType(self.m_FunctionType)
		
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
			return self.m_ValueObject.CreateValueFromAddress('[Function]', self.m_ValueObject.GetValueAsUnsigned(), self.m_FunctionType)
		elif _iChild == 1:
			return self.m_ValueObject.CreateValueFromAddress('[File]', self.m_ValueObject.GetValueAsUnsigned(), self.m_FileType)
		elif _iChild == 2:
			return self.m_ValueObject.CreateValueFromAddress('[Line]', self.m_ValueObject.GetValueAsUnsigned(), self.m_LineType)
		elif _iChild == 3:
			return self.m_ValueObject.CreateValueFromAddress('[Address]', self.m_ValueObject.AddressOf().GetValueAsUnsigned(), self.m_LineType.GetBasicType(lldb.eBasicTypeVoid).GetPointerType())
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
				return Function.GetName()
		return hex(_Value.AddressOf().GetValueAsUnsigned())
	except Exception as error:
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
		print '(fg_SummaryProvider_CCodeAddressLine) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_SummaryProvider_CMibCodeAddress(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Current = _Value.GetChildMemberWithName('[Function]')
		Summary = Current.GetSummary()
		if Summary == None:
			Value = Current.GetValue()
			if Value != None:
				Summary = str(Value)
		
		if Summary != None:
			return Summary;
		return None
	except Exception as error:
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
