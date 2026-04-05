// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <Mib/Core/Core>

#include <Mib/Core/PlatformSpecific/Windows>
#include <Mib/Core/PlatformSpecific/WindowsRegistry>
#include <Mib/Core/PlatformSpecific/WindowsString>
#include <Mib/Core/PlatformSpecific/WindowsUndocumented>
#include <Mib/Debug/Debug>
#include <Mib/Encoding/EJson>
#include <Mib/Encoding/JsonShortcuts>
#include <Mib/Process/ProcessLaunch>

#include "Malterlib_Debug_Platform_Windows.h"

#include <Windows.h>

namespace NMib
{
	namespace NSys
	{
		void fg_Windows_ExpectedFilter(LPTOP_LEVEL_EXCEPTION_FILTER _pFilter);
	}

	namespace NDebug
	{
		namespace NPlatform
		{
			static LRESULT WINAPI fs_WindowCacheProc(HWND _hWnd, UINT _Message, WPARAM _wParam, LPARAM _lParam)
			{
				if (_Message == WM_ENDSESSION || _Message == WM_QUERYENDSESSION)
					NMib::NPlatform::fg_ReportIsShuttingDown();

				return DefWindowProc(_hWnd, _Message, _wParam, _lParam);
			}

			CSubSystem_Debug_Platform_Windows::CSubSystem_Debug_Platform_Windows()
				: m_pCrashDumpUserNotifyFunction(nullptr)
				, m_bPollCheckExceptionFilter(true)
				, m_pDllNotificationCookie(nullptr)
			{
				using namespace NMib::NStr;
				using namespace NMib::NEncoding;

				m_ExceptionFilterPoller.m_pSystem = this;

				WNDCLASSA WndClass;
				memset(&WndClass, 0, sizeof(WndClass));
				WndClass.lpszClassName = "MalterlibCrashDumpWindowCache";
				WndClass.lpfnWndProc = fs_WindowCacheProc;
				WndClass.hInstance = g_hDllInstance;
				RegisterClassA(&WndClass);

				for (umint i = 0; i < EWindowCache; ++i)
					m_CacheWindows[i] = nullptr;

				auto BuildMetadata = NSys::fg_GetBuildMetadata();

				NEncoding::CEJsonSorted Metadata
					{
						"Product"_ = BuildMetadata.m_pProduct
						, "Application"_ = BuildMetadata.m_pApplication
						, "Configuration"_ = BuildMetadata.m_pConfiguration
						, "GitBranch"_ = BuildMetadata.m_pGitBranch
						, "GitCommit"_ = BuildMetadata.m_pGitCommit
						, "Platform"_ = BuildMetadata.m_pPlatform
						, "Version"_ = BuildMetadata.m_pVersion
#if defined(DMibContract_AnyEnabled) || DMibEnableSafeCheck > 0
						, "ExceptionInfo"_ = "{ExceptionInfo}"
#endif
					}
				;

				auto &OutTags = Metadata["Tags"].f_Array();

				for (umint iTag = 0; iTag < BuildMetadata.m_nTags; ++iTag)
					OutTags.f_Insert(BuildMetadata.m_pTags[iTag]);

				m_DumpMetadataTemplate = Metadata.f_ToString();
			}

			CSubSystem_Debug_Platform_Windows::~CSubSystem_Debug_Platform_Windows()
			{
				f_UninstallExceptionFilterCallback();
				for (umint i = 0; i < EWindowCache; ++i)
				{
					if (m_CacheWindows[i])
					{
						DestroyWindow(m_CacheWindows[i]);
						m_CacheWindows[i] = nullptr;
					}
				}
				UnregisterClassA("MalterlibCrashDumpWindowCache", g_hDllInstance);

				m_CrashDumpUserNotifyFormat_CustomMessage.f_Clear();
				m_CrashDumpUserNotifyFormat_CanContinueMessage.f_Clear();
				m_CrashDumpUserNotifyFormat_NoContinueMessage.f_Clear();
			}

			void CSubSystem_Debug_Platform_Windows::f_DestroyThreadSpecific()
			{
				m_ExceptionFilterPoller.f_Stop();
			}

			void CSubSystem_Debug_Platform_Windows::f_EnableCrashDumps()
			{
#if !defined(DMibSanitizerEnabled_Address)
				if (!g_bIsDll)
				{
					m_pPrevExceptionFilter = SetUnhandledExceptionFilter(&fsp_UnhandledException);
					NSys::fg_Windows_ExpectedFilter(&fsp_UnhandledException);
					f_InstallExceptionFilterCallback(true);
				}
				else
#endif
				{
					f_InstallExceptionFilterCallback(false);
				}
			}

			uint32 CSubSystem_Debug_Platform_Windows::f_GetRandom()
			{
				DMibLock(m_RandomLock);
				return m_Random.f_GetValue<uint32>();
			}

			NStr::CStrNonTracked CSubSystem_Debug_Platform_Windows::fs_FormatTimeFileName(const NTime::CTime &_Time)
			{
				NTime::CTimeConvert::CDateTime DateTime;
				NTime::CTimeConvert(_Time).f_ExtractDateTime(DateTime);

				return NStr::CStrNonTracked::CFormat("{}-{sj2,sf0}-{sj2,sf0}_{sj2,sf0}.{sj2,sf0}.{sj2,sf0}.{sj3,sf0,fe3}") << DateTime.m_Year << DateTime.m_Month << DateTime.m_DayOfMonth << DateTime.m_Hour << DateTime.m_Minute << DateTime.m_Second << DateTime.m_Fraction * 1000.0;
			}

			bool CSubSystem_Debug_Platform_Windows::fs_CheckAccessRights(NStr::CStrNonTracked &_Path)
			{
				try
				{
					auto &SubSystem = fg_Debug_Platfrom_Windows();
					uint32 RandomValue = SubSystem.f_GetRandom();
					NStr::CStrNonTracked GUID = NStr::CStrNonTracked::CFormat("TestAccessRights.{}.{}") << RandomValue << fs_FormatTimeFileName(NTime::CTime::fs_NowUTC());
					NFile::CFile::fs_CreateDirectory(_Path);
					NFile::CFile::fs_CreateDirectory(_Path + "/" + GUID);
					NFile::CFile::fs_DeleteDirectory(_Path + "/" + GUID);

					NStr::CStrNonTracked FileName = _Path + "/" + GUID + ".file";
					{
						NFile::CFile File;
						File.f_Open(FileName, NFile::EFileOpen_Write | NFile::EFileOpen_NoLocalCache | NFile::EFileOpen_ShareAll);

						uint32 Test = 1;
						File.f_Write(&Test, sizeof(Test));
					}
					NFile::CFile::fs_DeleteFile(FileName);

					return true;

				}
				catch (NFile::CExceptionFile)
				{
					return false;
				}
			}


			void CSubSystem_Debug_Platform_Windows::f_UndecorateName(const ch8 *_pName, NStr::CStr &_Destination)
			{
				return m_StackTrace.f_UndecorateName(_pName, _Destination);
			}

			void CSubSystem_Debug_Platform_Windows::f_UndecorateName(const ch8 *_pName, NStr::CStrNonTracked &_Destination)
			{
				return m_StackTrace.f_UndecorateName(_pName, _Destination);
			}

			void CSubSystem_Debug_Platform_Windows::f_UndecorateName(const ch8 *_pName, ch8 *_pDestination, umint _MaxLen)
			{
				return m_StackTrace.f_UndecorateName(_pName, _pDestination, _MaxLen);
			}

			CStackTraceInfo *CSubSystem_Debug_Platform_Windows::f_AquireStackTraceInfo(CMibCodeAddress _Address)
			{
				return m_StackTrace.f_AquireStackTraceInfo((umint)_Address);
			}

			void CSubSystem_Debug_Platform_Windows::f_ReleaseStackTraceInfo(CStackTraceInfo *_pInfo)
			{
				return m_StackTrace.f_ReleaseStackTraceInfo((CStackTraceContext::CLocalStackTraceInfo *)_pInfo);
			}


			constinit NMib::TCSubSystem<CSubSystem_Debug_Platform_Windows, NMib::ESubSystemDestruction_BeforeNonTrackedMemoryManager> g_SubSystem_Debug_Platform_Windows = {DAggregateInit};

			CSubSystem_Debug_Platform_Windows &fg_Debug_Platfrom_Windows()
			{
				return *g_SubSystem_Debug_Platform_Windows;
			}
		}
	}
}

void NMib::NSys::fg_Debug_BlockingMessage(NMib::NStr::CStr const &_Heading, NMib::NStr::CStr const &_Message)
{
	class CMessageBoxThread : public NMib::NThread::CThread
	{
	public:
		virtual ch8 const *f_GetThreadNameRaw()
		{
			return "Malterlib_MessageBoxThread";
		}
		virtual NMib::NStr::CStr f_GetThreadName()
		{
			return "Malterlib_MessageBoxThread";
		}
		NMib::NStr::CStrNonTracked m_MessageBoxText;
		NMib::NStr::CStrNonTracked m_MessageBoxHeading;
		uint32 m_MessageBoxFlags;
		uint32 m_bRet;

		aint f_Main()
		{
			m_bRet = ::MessageBoxW(nullptr, NMib::NStr::NPlatform::fg_StrToWindows<NMib::NStr::CWStrNonTracked>(m_MessageBoxText), NMib::NStr::NPlatform::fg_StrToWindows<NMib::NStr::CWStrNonTracked>(m_MessageBoxHeading), m_MessageBoxFlags);
			return 0;
		}
		void f_Run()
		{
			if (NMib::NPlatform::fg_ThisThreadOwnsDllLock() || g_bDoneMalterlibInitAll.f_Load() < 3)
				f_Main();
			else
			{
				f_Start();
				f_Stop();
			}
		}
	};

	CMessageBoxThread MessageBox;

	MessageBox.m_MessageBoxHeading = _Heading;
	MessageBox.m_MessageBoxText = _Message;
	MessageBox.m_MessageBoxFlags = MB_OK;
	MessageBox.m_bRet = 0;
	MessageBox.f_Run();

}

void NMib::NSys::fg_Debug_DiffStrings(const NMib::NStr::CStr &_FirstStr, const NMib::NStr::CStr &_SecondStr, const NMib::NStr::CStr &_FirstName, const NMib::NStr::CStr &_SecondName)
{
#if 1

	try
	{
		NMib::NStr::CStr ExecutablePath = "c:/Program Files/Araxis/Araxis Merge/Merge.exe";
		if (!NMib::NFile::CFile::fs_FileExists(ExecutablePath))
		{
			try
			{
				NMib::NPlatform::CWin32_Registry Reg(NMib::NPlatform::CWin32_Registry::ERegRoot_LocalMachine, "Software\\Thingamahoochie\\WinMerge");
				ExecutablePath = Reg.f_Read_Str("", "Executable", "");
			}
			catch (NException::CException)
			{
			}
		}

		if (!NMib::NFile::CFile::fs_FileExists(ExecutablePath))
		{
			try
			{
				NMib::NPlatform::CWin32_Registry Reg(NMib::NPlatform::CWin32_Registry::ERegRoot_LocalMachine, "Software\\Wow6432Node\\Thingamahoochie\\WinMerge");
				ExecutablePath = Reg.f_Read_Str("", "Executable", "");
			}
			catch (NException::CException)
			{
			}
		}
		if (!NMib::NFile::CFile::fs_FileExists(ExecutablePath))
		{
			try
			{
				NMib::NPlatform::CWin32_Registry Reg(NMib::NPlatform::CWin32_Registry::ERegRoot_CurrentUser, "Software\\Wow6432Node\\Thingamahoochie\\WinMerge");
				ExecutablePath = Reg.f_Read_Str("", "Executable", "");
			}
			catch (NException::CException)
			{
			}
		}
		if (!NMib::NFile::CFile::fs_FileExists(ExecutablePath))
		{
			try
			{
				NMib::NPlatform::CWin32_Registry Reg(NMib::NPlatform::CWin32_Registry::ERegRoot_CurrentUser, "Software\\Thingamahoochie\\WinMerge");
				ExecutablePath = Reg.f_Read_Str("", "Executable", "");
			}
			catch (NException::CException)
			{
			}
		}
		if (!NMib::NFile::CFile::fs_FileExists(ExecutablePath))
		{
			ExecutablePath = "C:/Program Files/Perforce/p4merge.exe";
		}
		{
			uint32 FileHash0 = NMib::NStr::CStr(_FirstStr).f_Hash();
			uint32 FileHash1 = NMib::NStr::CStr(_SecondStr).f_Hash();
			NMib::NStr::CStr TempPath = NSys::NFile::fg_GetTemporaryDirectory();

			NMib::NFile::CFile::fs_CreateDirectory(TempPath);

			NMib::NStr::CStr FileName0 = TempPath + NMib::NStr::CStr(NMib::NStr::CStr::CFormat("/MalterlibTempDiff_{nfh,sf0,sj8}.txt") << FileHash0);
			NMib::NStr::CStr FileName1 = TempPath + NMib::NStr::CStr(NMib::NStr::CStr::CFormat("/MalterlibTempDiff_{nfh,sf0,sj8}.txt") << FileHash1);

			NMib::NFile::CFile::fs_WriteStringToFile(FileName0, _FirstStr);
			NMib::NFile::CFile::fs_WriteStringToFile(FileName1, _SecondStr);

			if (NMib::NFile::CFile::fs_FileExists(ExecutablePath))
			{
				auto Params = NProcess::CProcessLaunchParams::fs_LaunchExecutable
					(
						ExecutablePath
						, NContainer::fg_CreateVector<NMib::NStr::CStr>(FileName0, FileName1)
						, NMib::NFile::CFile::fs_GetPath(ExecutablePath)
						, nullptr
					)
				;

				Params.m_bAllowLaunchedInForeground = true;

				NMib::NProcess::CProcessLaunch Launch(Params, NProcess::EProcessLaunchCloseFlag_None);
			}
		}
	}
	catch (NException::CException)
	{
	}
#endif
}

void NMib::NSys::fg_Debug_GenerateCrashDump(const NMib::NStr::CStr &_Message, const NMib::NStr::CStr &_ExtraLog, NContainer::TCVector<NMib::NStr::CStr> &_GeneratedLogs, bool _bDisplayGUI)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_GenerateCrashDump(_Message, _ExtraLog, _GeneratedLogs, _bDisplayGUI);
}

void NMib::NSys::fg_Debug_GenerateMemoryDump
	(
		NMib::NContainer::TCVector<void*, NMib::NMemory::CAllocator_NonTrackedHeap> const &_Locations
		, NMib::NContainer::TCVector<umint, NMib::NMemory::CAllocator_NonTrackedHeap> const &_Sizes
	)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	SubSystem.f_GenerateMemoryDump(_Locations, _Sizes);
}

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

	return false;
}


NMib::CStackTraceInfo *NMib::NSys::fg_Debug_AquireStackTraceInfo(CMibCodeAddress _Address)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_AquireStackTraceInfo(_Address);
}


void NMib::NSys::fg_Debug_ReleaseStackTraceInfo(CStackTraceInfo *_pInfo)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	if (_pInfo->m_pContext)
		return SubSystem.f_ReleaseStackTraceInfo((CStackTraceInfo *)_pInfo->m_pContext);
	else
		return SubSystem.f_ReleaseStackTraceInfo(_pInfo);
}


NMib::EDebugCheckFailureAction NMib::NSys::fg_Debug_ReportContractFailure(const ch8 *_pFileName, int32 _Line, void *_pCodePointer, const NMib::NStr::CStrNonTracked &_ErrorMessage)
{
	DMibDeadlockDetectorPause;

	NMib::EDebugCheckFailureAction Ret;
	auto fl_DisplayMessage
		= [&] (NThread::CThreadObjectNonTracked *_pThread) -> aint
		{
		#if defined(DDebug) && 0
			// _CrtDbgReportW uses memory manager so it's not optimal to use this
			UndocumentedPEB *pPeb = fg_GetPEB(fg_GetTEB());
			if (pPeb->BeingDebugged)
			{
				Ret = EDebugContractFailureAction_NotHandled;
				return 0;
			}

			auto Module = NMib::NFile::CFile::fs_GetFile(NSys::NFile::fg_GetModulePathNonTracked(_pCodePointer));
			int LocalRet = _CrtDbgReportW(_CRT_ASSERT, NStr::NPlatform::fg_StrToWindows<CWStrNonTracked>(CStrNonTracked(_pFileName)), _Line, fg_StrToWindows<CWStrNonTracked>(Module), str_utf16("%s"), fg_StrToWindows<CWStrNonTracked>(_ErrorMessage).f_GetStr());
			if (LocalRet == 1)
			{
				Ret = EDebugContractFailureAction_Break;
				return 0;
			}

			Ret = EDebugContractFailureAction_Continue;
		#else
			UndocumentedPEB *pPeb = fg_GetPEB(fg_GetTEB());
			if (pPeb->BeingDebugged)
			{
				Ret = EDebugContractFailureAction_NotHandled;
				return 0;
			}

			if (fg_GetSys()->f_GetRunningAsDaemon())
			{
				Ret = EDebugContractFailureAction_Break;
				return 0;
			}

			auto Module = NMib::NFile::CFile::fs_GetFile(NSys::NFile::fg_GetModulePathNonTracked(_pCodePointer));

			NMib::NStr::CStrNonTracked MessageText;
			MessageText += "Assertion failure:\r\n\r\n";
			MessageText += _ErrorMessage;
			MessageText += "\r\n";
			MessageText += NMib::NStr::CStrNonTracked::CFormat("In module: {}. At:\r\n") << Module;
			MessageText += NMib::NStr::CStrNonTracked::CFormat("{}({})\r\n\r\n") << _pFileName << _Line;
			MessageText += "Decide how to proceed.";

			switch (MessageBoxW(nullptr, NMib::NStr::NPlatform::fg_StrToWindows<NMib::NStr::CWStrNonTracked>(MessageText), str_utf16("Assertion failure"), MB_ABORTRETRYIGNORE))
			{
			case IDABORT:
				Ret = EDebugContractFailureAction_Abort;
				return 0;
			case IDRETRY:
				Ret = EDebugContractFailureAction_Break;
				return 0;
			}
			Ret = EDebugContractFailureAction_Continue;
		#endif

			return 0;
		}
	;

	if (NMib::NPlatform::fg_ThisThreadOwnsDllLock() || g_bDoneMalterlibInitAll.f_Load() < 3)
	{
		fl_DisplayMessage(nullptr);
	}
	else
	{
		NStorage::TCUniquePointer<NThread::CThreadObjectNonTracked, NMib::NMemory::CAllocator_NonTrackedHeap> pThread
			= NThread::CThreadObjectNonTracked::fs_StartThread(fl_DisplayMessage, "Report assert display message thread")
		;
	}

	return Ret;
}

void NMib::NSys::fg_Debug_SetCrashDumpUserNotifyFunction(NSys::FCrashDumpUserNotify *_pCrashDumpUserNotify)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_SetCrashDumpUserNotifyFunction(_pCrashDumpUserNotify);
}

void NMib::NSys::fg_Debug_SetCrashDumpUserNotifyFormats(NMib::NStr::CStrNonTracked const &_CustomMessage, NMib::NStr::CStrNonTracked const &_CanContinueMessage, NMib::NStr::CStrNonTracked const &_NoContinueMessage)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_SetCrashDumpUserNotifyFormats( _CustomMessage, _CanContinueMessage, _NoContinueMessage );
}

void NMib::NSys::fg_Debug_EnableCrashDumpCaches()
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_EnableCrashDumpCaches();
}


void NMib::NSys::fg_Debug_UndecorateName(const ch8 *_pName, NMib::NStr::CStr &_Destination)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_UndecorateName(_pName, _Destination);
}

void NMib::NSys::fg_Debug_UndecorateName(const ch8 *_pName, NMib::NStr::CStrNonTracked &_Destination)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_UndecorateName(_pName, _Destination);
}

void NMib::NSys::fg_Debug_UndecorateName(const ch8 *_pName, ch8 *_pDestination, umint _MaxLen)
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;
	return SubSystem.f_UndecorateName(_pName, _pDestination, _MaxLen);
}


void NMib::NSys::fg_Debug_EnableCrashDumps()
{
	auto &SubSystem = *NMib::NDebug::NPlatform::g_SubSystem_Debug_Platform_Windows;

	SubSystem.f_EnableCrashDumps();
}
