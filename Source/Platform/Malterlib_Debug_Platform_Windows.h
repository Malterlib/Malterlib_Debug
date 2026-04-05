// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <Mib/Core/Core>
#include <Mib/Debug/Debug>
#include <Mib/Core/PlatformSpecific/WindowsString>
#include <Mib/Core/PlatformSpecific/WindowsRegistry>
#include <Mib/Process/ProcessLaunch>

#include "Malterlib_Debug_Platform_Windows_StackTrace.h"

#pragma warning(disable:4091)
#include <Windows.h>
#include <DbgHelp.h>

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			struct CSubSystem_Debug_Platform_Windows : public NMib::CSubSystem
			{
				class CExceptionMemoryData;

				CSubSystem_Debug_Platform_Windows();
				~CSubSystem_Debug_Platform_Windows();

				void f_DestroyThreadSpecific() override;
				void f_EnableCrashDumps();

				static LONG fsp_ExceptionGenerateHandler(struct _EXCEPTION_POINTERS *_pExceptionInfo, void *_pData);
				void f_EnableCrashDumpCaches();
				void f_GenerateCrashDump(const NStr::CStr &_Message, const NStr::CStr &_ExtraLog, NContainer::TCVector<NMib::NStr::CStr> &_GeneratedLogs, bool _bDisplayGUI);
				static LONG fsp_ExceptionGenerateHandlerMemory(struct _EXCEPTION_POINTERS *_pExceptionInfo, void *_pData);
				void f_GenerateMemoryDump
					(
						NMib::NContainer::TCVector<void*, NMemory::CAllocator_NonTrackedHeap> const& _Locations
						, NMib::NContainer::TCVector<umint, NMib::NMemory::CAllocator_NonTrackedHeap> const& _Sizes
					)
				;

				void f_SetCrashDumpUserNotifyFunction(NSys::FCrashDumpUserNotify *_pCrashDumpUserNotify);
				void f_SetCrashDumpUserNotifyFormats(const NStr::CStrNonTracked &_CustomMessage, const NStr::CStrNonTracked &_CanContinueMessage, const NStr::CStrNonTracked &_NoContinueMessage);

				static LONG WINAPI fsp_UnhandledException(struct _EXCEPTION_POINTERS *_pExceptionInfo);
				static NStr::CStr fs_FixLineEndings(NStr::CStr const &_In);
				NStr::CStrNonTracked f_DumpObjects();
				NStr::CStrNonTracked f_DumpModules();
				uint32 f_GetRandom();

				static NStr::CStrNonTracked fs_FormatTimeFileName(const NTime::CTime &_Time);
				static bool fs_CheckAccessRights(NStr::CStrNonTracked &_Path);

				static LONG WINAPI fsp_DumpExceptionInformation(struct _EXCEPTION_POINTERS *_pExceptionInfo, const NStr::CStr &_Message, const NStr::CStr &_ExtraLog, NContainer::TCVector<NMib::NStr::CStr> *_pGeneratedLogs, bool _bDisplayGUI);
				static BOOL CALLBACK fp_DumpExceptionMemoryCallback(PVOID _pParam,const PMINIDUMP_CALLBACK_INPUT _pInput,PMINIDUMP_CALLBACK_OUTPUT _pOutput);
				static LONG WINAPI fsp_DumpExceptionMemory(struct _EXCEPTION_POINTERS *_pExceptionInfo, CExceptionMemoryData * _pExceptionMemoryData);

				void f_InstallExceptionFilterCallback(bool _bDoInstall);
				void f_UninstallExceptionFilterCallback();
				void f_UndecorateName(const ch8 *_pName, NStr::CStr &_Destination);
				void f_UndecorateName(const ch8 *_pName, NStr::CStrNonTracked &_Destination);
				void f_UndecorateName(const ch8 *_pName, ch8 *_pDestination, umint _MaxLen);
				CStackTraceInfo *f_AquireStackTraceInfo(CMibCodeAddress _Address);
				void f_ReleaseStackTraceInfo(CStackTraceInfo *_pInfo);

			public:
				enum
				{
					EWindowCache = 10
				};

				class CExceptionFilterPoller : public NMib::NThread::CThread
				{
				public:
					CExceptionFilterPoller();
					~CExceptionFilterPoller();

					virtual NStr::CStr f_GetThreadName();
					inline_never void f_PollFilter();
					aint f_Main();

				public:
					CSubSystem_Debug_Platform_Windows *m_pSystem;
				};

				NSys::FCrashDumpUserNotify *m_pCrashDumpUserNotifyFunction;

				NStr::CStrNonTracked m_CrashDumpUserNotifyFormat_CustomMessage;
				NStr::CStrNonTracked m_CrashDumpUserNotifyFormat_CanContinueMessage;
				NStr::CStrNonTracked m_CrashDumpUserNotifyFormat_NoContinueMessage;
				NThread::CMutual m_DumpExceptionInfoLock;
				NStr::CStrNonTracked m_DumpMetadataTemplate;

				NThread::CMutual m_RandomLock;
				NMisc::CAutoRandom m_Random;

				HWND m_CacheWindows[EWindowCache];

				LPTOP_LEVEL_EXCEPTION_FILTER m_pPrevExceptionFilter;
				bool m_bPollCheckExceptionFilter;
				aint m_bPollCheckExceptionFilterTimes;
				void *m_pDllNotificationCookie;
				CExceptionFilterPoller m_ExceptionFilterPoller;
				NAtomic::TCAtomic<smint> m_bExceptionFilterPollerInstalled;
				CStackTraceContext m_StackTrace;

			};

			CSubSystem_Debug_Platform_Windows &fg_Debug_Platfrom_Windows();
		}
	}
}

