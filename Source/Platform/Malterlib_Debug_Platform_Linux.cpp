// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <Mib/Core/Core>

#include "Malterlib_Debug_Platform_Linux_Symbols.h"

#include <dlfcn.h>
#include <cxxabi.h>

// Libunwind may buy us some more info, but the output from that (even Apple's variant) is pretty
// much the same as from dladdr as far as I can tell.

bool NMib::NSys::fg_Debug_AquireStackTraceInfo(CStackTraceInfo & _oInfo, CMibCodeAddress _Address, bool _bCanAllocNonTracked)
{
	if (_bCanAllocNonTracked)
	{
		auto pInfo = NSys::fg_Debug_AquireStackTraceInfo(_Address);
		if (!pInfo)
			return false;
		_oInfo = *pInfo;
		_oInfo.m_pContext = pInfo;
		return true;
	}

	_oInfo.m_pContext = (void *)1;

	Dl_info DLInfo;
	int DLResult = dladdr((void const *)_Address, &DLInfo);

	if (DLResult == 0)
		return false;

	_oInfo.m_pFunctionName = DLInfo.dli_sname;
	_oInfo.m_pModuleName = DLInfo.dli_fname;

	if (_bCanAllocNonTracked)
	{
		//CDisableHeapOverrideScope Scope;
		int Status = 1;
		char *pDemangled = abi::__cxa_demangle(DLInfo.dli_sname, nullptr, nullptr, &Status);
		if (Status == 0)
		{
			_oInfo.m_pFunctionName = pDemangled;
			_oInfo.m_pContext = (void *)2;
		}
	}
	else
		_oInfo.m_pFunctionName = DLInfo.dli_sname;
	return true;
}


NMib::CStackTraceInfo *NMib::NSys::fg_Debug_AquireStackTraceInfo(CMibCodeAddress _pAddress)
{
	return NMib::NDebug::NPlatform::fg_GetSymbols().f_AcquireStackTraceInfo((umint)_pAddress);
}

extern "C"
{
	module_export void nontracked_free (void *__ptr) __THROW;
}

void NMib::NSys::fg_Debug_ReleaseStackTraceInfo(CStackTraceInfo *_pInfo)
{
	if ((umint)_pInfo->m_pContext == 2)
	{
//		CDisableHeapOverrideScope Scope;
#ifdef _LIBCPP_BUILD_STATIC
		nontracked_free((void *)_pInfo->m_pFunctionName);
#else
		free((void *)_pInfo->m_pFunctionName);
#endif
	}
	else if ((umint)_pInfo->m_pContext == 1)
	{
		// Nothing to deallocate
	}
	else if (_pInfo->m_pContext)
	{
		NMib::NDebug::NPlatform::fg_GetSymbols().f_ReleaseStackTraceInfo((CStackTraceInfo *)_pInfo->m_pContext);
	}
	else
		NMib::NDebug::NPlatform::fg_GetSymbols().f_ReleaseStackTraceInfo(_pInfo);
}

void NMib::NSys::fg_Debug_BlockingMessage(NMib::NStr::CStr const &_Heading, NMib::NStr::CStr const &_Message)
{

}

void NMib::NSys::fg_Debug_DiffStrings(const NMib::NStr::CStr &_FirstStr, const NMib::NStr::CStr &_SecondStr, const NMib::NStr::CStr &_FirstName, const NMib::NStr::CStr &_SecondName)
{
	DMibError("Not implemented - fg_Debug_DiffStrings");
}

void NMib::NSys::fg_Debug_GenerateCrashDump(const NMib::NStr::CStr &_Message, const NMib::NStr::CStr &_ExtraLog, NContainer::TCVector<NMib::NStr::CStr> &_GeneratedLogs, bool _bDisplayGUI)
{

}

NMib::EDebugCheckFailureAction NMib::NSys::fg_Debug_ReportContractFailure(const ch8 *_pFileName, int32 _Line, void *_pCodePointer, const NMib::NStr::CStrNonTracked &_ErrorMessage)
{
	return EDebugContractFailureAction_NotHandled;
}

void NMib::NSys::fg_Debug_SetCrashDumpUserNotifyFunction(NMib::NSys::FCrashDumpUserNotify *_pCrashDumpUserNotify)
{

}

void NMib::NSys::fg_Debug_SetCrashDumpUserNotifyFormats(NMib::NStr::CStrNonTracked const &_CustomMessage, NMib::NStr::CStrNonTracked const &_CanContinueMessage, NMib::NStr::CStrNonTracked const &_NoContinueMessage)
{

}

