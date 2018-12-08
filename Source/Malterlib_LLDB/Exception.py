# Copyright (C) 2015 Hansoft AB 
# Distributed under the MIT license, see license text in LICENSE.Malterlib

import lldb
from Common import *
from StringHelpers import *


class CSynthProvider_NException_CCallstack(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		self.m_Callstack = self.m_ValueObject.GetChildMemberWithName('m_Callstack')
		self.m_CallstackLen = self.m_ValueObject.GetChildMemberWithName('m_CallstackLen')
		self.m_nCallStack = 0
		self.m_nCallStack = self.m_CallstackLen.GetValueAsUnsigned()
		return True

	def fp_GetChildIndex(self, _Name):
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		return self.m_Callstack.GetChildAtIndex(_iChild);

	def fp_NumChildren(self):
		return self.m_nCallStack


class CSynthProvider_NException_CExceptionBase(CSynthProvider_Common):
	def __init__(self, _ValueObject, _Dictionary):
		CSynthProvider_Common.__init__(self, _ValueObject, _Dictionary)

	def update(self):
		CSynthProvider_Common.update(self)
		try:
			if self.m_ValueObjectType.GetPointeeType().IsPointerType():
				return
			if not self.fp_ExtractType():
				return
			self.m_bValid = True
		except Exception as error:
			print '(' + self.__class__.__name__ + ') update error: ', error, ' path: ', self.m_ValueObject.get_expr_path()
			return

	def fp_ExtractType(self):
		self.m_pClass = self.m_ValueObject.GetChildMemberWithName('m_pClass')
		self.m_ErrorNoAlloc = self.m_ValueObject.GetChildMemberWithName('m_ErrorNoAlloc')
		self.m_pErrorAlloc = fg_ChildPath(self.m_ValueObject, 'm_pErrorAlloc.m_Data.m_pPointTo.m_pPtr')
		self.m_pErrorAllocNonTracked = fg_ChildPath(self.m_ValueObject, 'm_pErrorAllocNonTracked.m_Data.m_pPointTo.m_pPtr')
		self.m_pCallstack = fg_ChildPath(self.m_ValueObject, 'm_pCallstack.m_Data.m_pPointTo.m_pPtr')
		self.m_pCallstackNonTracked = fg_ChildPath(self.m_ValueObject, 'm_pCallstackNonTracked.m_Data.m_pPointTo.m_pPtr')
		return True

	def fp_GetChildIndex(self, _Name):
		if _Name == '[Message]':
			return 0
		if _Name == '[Type]':
			return 1
		if _Name == '[Callstack]':
			return 2
		return CSynthProvider_Common.fp_GetChildIndex(self, _Name)

	def fp_GetChildAtIndex(self, _iChild):
		if _iChild == 0:
			if self.m_pErrorAllocNonTracked.GetValueAsUnsigned():
				Value = self.m_pErrorAllocNonTracked.Dereference()
				return self.m_ValueObject.CreateValueFromAddress('[Message]', self.m_pErrorAllocNonTracked.GetValueAsUnsigned(), Value.GetType());
			if self.m_pErrorAlloc.GetValueAsUnsigned():
				Value = self.m_pErrorAlloc.Dereference()
				return self.m_ValueObject.CreateValueFromAddress('[Message]', self.m_pErrorAlloc.GetValueAsUnsigned(), Value.GetType());
			return self.m_ValueObject.CreateValueFromAddress('[Message]', self.m_ErrorNoAlloc.AddressOf().GetValueAsUnsigned(), self.m_ErrorNoAlloc.GetType());
		elif _iChild == 1:
			return self.m_ValueObject.CreateValueFromAddress('[Type]', self.m_pClass.AddressOf().GetValueAsUnsigned(), self.m_pClass.GetType());
		elif _iChild == 2:
			if self.m_pCallstackNonTracked.GetValueAsUnsigned():
				Value = self.m_pCallstackNonTracked.Dereference()
				return self.m_ValueObject.CreateValueFromAddress('[Callstack]', self.m_pCallstackNonTracked.GetValueAsUnsigned(), Value.GetType());
			if self.m_pCallstack.GetValueAsUnsigned():
				Value = self.m_pCallstack.Dereference()
				return self.m_ValueObject.CreateValueFromAddress('[Callstack]', self.m_pCallstack.GetValueAsUnsigned(), Value.GetType());
			return None
		return None

	def fp_NumChildren(self):
		return 3


def fg_SummaryProvider_CExceptionBase(_Value, dict):
	try:
		ValueType = fg_GetValueType(_Value)
		if ValueType.GetPointeeType().IsPointerType():
			return None
		Current = _Value.GetChildMemberWithName('[Message]')
		Summary = Current.GetSummary()
		if Summary == None:
			Value = Current.GetValue()
			if Value != None:
				Summary = str(Value)
		
		if Summary != None:
			if ValueType.IsPointerType():
				return hex(_Value.GetValueAsUnsigned()) + "   " + Summary
			return Summary;
		return None
	except Exception as error:
		print '(fg_SummaryProvider_CExceptionBase) error: ', error, ' path: ', _Value.get_expr_path()
		return

def fg_MibLLDBInit_Exception(_Debugger):
	
	# Exceptions
	fg_AddSynth(_Debugger, CSynthProvider_NException_CCallstack, "(^|^const )NMib::NException::CCallstack$", True)
	
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NException::TCException<.*>$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NException::CException.*$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NContract::CContractException.*$", True)

	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NException::CExceptionBase$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::CDynamicLibraryException$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NConcurrency::CExceptionActorDeleted$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NDBus::CDBusException$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NFile::CExceptionFile$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NNetwork::CExceptionNet$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NContainer::CExceptionList$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NContainer::CExceptionListBoundCheck$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NMemory::CExceptionMemoryManagerDebug$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NContainer::CExceptionRegistry$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NSql::CExceptionDatabase$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NStream::CExceptionStream$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NStream::CExceptionStreamVersionMismatch$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NMib::NProcess::CExceptionProcessProxyProtocol$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NAOQT::NDesktopIntegration::CUnityException$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NAOCC::NNetwork::CExceptionConnectionManager$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NAOUI::CExceptionAOUI$", True)
	fg_AddSynth(_Debugger, CSynthProvider_NException_CExceptionBase, "(^|^const )NBuildServer::CExceptionSlaveProtocol$", True)

	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NException::CExceptionBase$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::CDynamicLibraryException$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NConcurrency::CExceptionActorDeleted$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NDBus::CDBusException$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NFile::CExceptionFile$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NNetwork::CExceptionNet$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NContainer::CExceptionList$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NContainer::CExceptionListBoundCheck$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NMemory::CExceptionMemoryManagerDebug$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NContainer::CExceptionRegistry$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NSql::CExceptionDatabase$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NStream::CExceptionStream$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NStream::CExceptionStreamVersionMismatch$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NProcess::CExceptionProcessProxyProtocol$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NAOQT::NDesktopIntegration::CUnityException$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NAOCC::NNetwork::CExceptionConnectionManager$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NAOUI::CExceptionAOUI$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NBuildServer::CExceptionSlaveProtocol$", True)
	
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NException::TCException<.*>$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NException::CException.*$", True)
	fg_AddSummary(_Debugger, fg_SummaryProvider_CExceptionBase, "(^|^const )NMib::NContract::CContractException.*$", True)
	
	return
