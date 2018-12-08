// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include <Mib/Cryptography/UUID>
#include <Mib/Process/ProcessLaunch>

#include "Malterlib_Debug_Platform_OSX_Symbols.h"

#include <execinfo.h>
#include <dlfcn.h>
#include <cxxabi.h>

bool fg_MalterlibMallocOverride_Enabled();

void NMib::NSys::fg_Debug_BlockingMessage(NMib::NStr::CStr const &_Heading, NMib::NStr::CStr const &_Message)
{

}

void NMib::NSys::fg_Debug_DiffStrings(const NMib::NStr::CStr &_FirstStr, const NMib::NStr::CStr &_SecondStr, const NMib::NStr::CStr &_FirstName, const NMib::NStr::CStr &_SecondName)
{
	using namespace NMib::NStr;
	NContainer::TCVector<CStr> DiffPrograms;
	DiffPrograms.f_Insert("/Applications/Araxis Merge.app/Contents/Utilities/compare");
	DiffPrograms.f_Insert("/Applications/p4merge.app");

	CStr FirstExt = NMib::NFile::CFile::fs_GetExtension(_FirstName);
	CStr FirstName = NMib::NFile::CFile::fs_GetFileNoExt(_FirstName);
	if (FirstName.f_IsEmpty())
		FirstName = "FirstDiff";
	if (FirstExt.f_IsEmpty())
		FirstExt = "text";

	CStr SecondExt = NMib::NFile::CFile::fs_GetExtension(_SecondName);
	CStr SecondName = NMib::NFile::CFile::fs_GetFileNoExt(_SecondName);
	if (SecondName.f_IsEmpty())
		SecondName = "SecondDiff";
	if (SecondExt.f_IsEmpty())
		SecondExt = "text";

	for (auto iProgram = DiffPrograms.f_GetIterator(); iProgram; ++iProgram)
	{
		if (!NMib::NFile::CFile::fs_FileExists(CStr(*iProgram)))
			continue;
			
		CStr TempDir = NMib::NFile::CFile::fs_GetTemporaryDirectory();
		NMib::NFile::CFile::fs_CreateDirectory(TempDir);
		CStr FirstFile = NMib::NFile::CFile::fs_AppendPath
			(
				TempDir
				, CStr::CFormat("{}-{}-{}.txt")
				<< FirstName << FirstExt << NMib::NCryptography::fg_GetHashedUuidString(_FirstStr, NMib::NCryptography::CUniversallyUniqueIdentifier("{72048B5E-1F9C-4385-AF16-997FDC21F215}"))
			)
		;
		CStr SecondFile = NMib::NFile::CFile::fs_AppendPath
			(
				TempDir
				, CStr::CFormat("{}-{}-{}.txt")
				<< SecondName << SecondExt << NMib::NCryptography::fg_GetHashedUuidString(_SecondStr, NMib::NCryptography::CUniversallyUniqueIdentifier("{72048B5E-1F9C-4385-AF16-997FDC21F215}"))
			)
		;
		NMib::NFile::CFile::fs_WriteStringToFile(FirstFile, _FirstStr);
		NMib::NFile::CFile::fs_WriteStringToFile(SecondFile, _SecondStr);
		NContainer::TCVector<CStr> Params;
		Params.f_Insert(FirstFile);
		Params.f_Insert(SecondFile);
		CStr StdOut;
		CStr StdErr;
		uint32 ExitCode;
		if (NMib::NProcess::CProcessLaunch::fs_LaunchBlock(*iProgram, Params, StdOut, StdErr, ExitCode))
			break;
	}
}

void NMib::NSys::fg_Debug_GenerateCrashDump(const NMib::NStr::CStr &_Message, const NMib::NStr::CStr &_ExtraLog, NContainer::TCVector<NMib::NStr::CStr> &_GeneratedLogs, bint _bDisplayGUI)
{
	
}

void NMib::NSys::fg_Debug_GenerateMemoryDump
	(
	 	NMib::NContainer::TCVector<void*, NMib::NMemory::CAllocator_NonTrackedHeap> const &_Locations
	 	, NMib::NContainer::TCVector<mint, NMib::NMemory::CAllocator_NonTrackedHeap> const &_Sizes
	)
{

}

// Libunwind may buy us some more info, but the output from that (even Apple's variant) is pretty
// much the same as from dladdr as far as I can tell.

bool NMib::NSys::fg_Debug_AquireStackTraceInfo(CStackTraceInfo &_oInfo, CMibCodeAddress _Address, bool _bCanAllocNonTracked)
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
		int Status = 1;
		char *pDemangled;
#if !defined(_LIBCPP_BUILD_STATIC)
		if (fg_GetSys()->f_MemoryManager_ReportingLeaks() && fg_MalterlibMallocOverride_Enabled())
			Status = 1;
		else
#endif
			pDemangled = abi::__cxa_demangle(DLInfo.dli_sname, nullptr, nullptr, &Status);

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

#ifdef _LIBCPP_BUILD_STATIC
extern "C"
{
	void nontracked_free (void *__ptr);
}
#endif

NMib::CStackTraceInfo *NMib::NSys::fg_Debug_AquireStackTraceInfo(CMibCodeAddress _Address)
{
	auto &Symbols = NMib::NDebug::NPlatform::fg_GetSymbols();
	
	auto &Cache = Symbols.f_GetCache((mint)_Address);
	
	if (Cache.m_bValidCache)
	{
		if (Cache.m_bSuccessful)
			return &Cache.m_StackTraceInfo;
		else
			return nullptr;
	}
	
	DMibLock(Cache.m_Lock);
	if (Cache.m_bValidCache)
	{
		if (Cache.m_bSuccessful)
			return &Cache.m_StackTraceInfo;
		else
			return nullptr;
	}
	
	Cache.m_bValidCache = true;
	
	Dl_info DLInfo;
	int DLResult = dladdr((void const *)_Address, &DLInfo);

	NMib::NDebug::NPlatform::CAddressInfo AddrInfo;
	
	if (Symbols.f_Lookup((mint)_Address, AddrInfo))
	{
		if (DLResult)
		{
			Cache.m_StackTraceInfo.m_ModuleName = DLInfo.dli_fname;
			Cache.m_StackTraceInfo.m_pModuleName = Cache.m_StackTraceInfo.m_ModuleName;
		}
		else
			Cache.m_StackTraceInfo.m_pModuleName = nullptr;

		Cache.m_StackTraceInfo.m_FunctionName = AddrInfo.m_Function;
		Cache.m_StackTraceInfo.m_pFunctionName = Cache.m_StackTraceInfo.m_FunctionName.f_GetStr();

		Cache.m_StackTraceInfo.m_FileName = AddrInfo.m_File;
		Cache.m_StackTraceInfo.m_pSourceFileName = Cache.m_StackTraceInfo.m_FileName.f_GetStr();

		Cache.m_StackTraceInfo.m_SourceLine = AddrInfo.m_Line;

		Cache.m_bSuccessful = true;
		return &Cache.m_StackTraceInfo;
	}
	else
	{
		if (DLResult == 0)
			return nullptr;

		Cache.m_StackTraceInfo.m_ModuleName = DLInfo.dli_fname;
		Cache.m_StackTraceInfo.m_pModuleName = Cache.m_StackTraceInfo.m_ModuleName;
		int Status = 1;
		
		{
			char *pDemangled;
#if !defined(_LIBCPP_BUILD_STATIC)
			if (fg_GetSys()->f_MemoryManager_ReportingLeaks() && fg_MalterlibMallocOverride_Enabled())
				Status = 1;
			else
#endif
				pDemangled = abi::__cxa_demangle(DLInfo.dli_sname, nullptr, nullptr, &Status);
			
			if (Status == 0)
			{
				Cache.m_StackTraceInfo.m_FunctionName = pDemangled;
				Cache.m_StackTraceInfo.m_pFunctionName = Cache.m_StackTraceInfo.m_FunctionName;
#ifdef _LIBCPP_BUILD_STATIC
				nontracked_free(pDemangled);
#else
				free(pDemangled);
#endif
			}
			else
			{
				Cache.m_StackTraceInfo.m_FunctionName = DLInfo.dli_sname ? DLInfo.dli_sname : "";
				Cache.m_StackTraceInfo.m_pFunctionName = Cache.m_StackTraceInfo.m_FunctionName;
			}
		}

		Cache.m_StackTraceInfo.m_pSourceFileName = nullptr;
		Cache.m_StackTraceInfo.m_SourceLine = 0;
		Cache.m_bSuccessful = true;

		return &Cache.m_StackTraceInfo;
	}
}

void NMib::NSys::fg_Debug_ReleaseStackTraceInfo(CStackTraceInfo *_pInfo)
{
	if ((mint)_pInfo->m_pContext == 2)
	{
#ifdef _LIBCPP_BUILD_STATIC
		nontracked_free((void *)_pInfo->m_pFunctionName);
#else
		free((void *)_pInfo->m_pFunctionName);
#endif
	}
	else
	{
		// Do nothing since it's all cached
	}
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
