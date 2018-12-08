// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include <Mib/Debug/Debug>
#include <Mib/Core/PlatformSpecific/WindowsFilePath>
#include <Mib/Core/PlatformSpecific/WindowsOptional>
#include <Mib/Core/PlatformSpecific/WindowsError>
#include <Mib/Core/PlatformSpecific/Windows>
#include "Malterlib_Debug_Platform_Windows.h"

#include <Windows.h>
#include <winnt.h>
#include <winternl.h>

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			class CExceptionData
			{
			public:
				bint m_bDisplayGUI;
				NMib::NContainer::TCVector<NMib::NStr::CStr> &m_GeneratedLogs;
				CExceptionData(NContainer::TCVector<NMib::NStr::CStr> &_GeneratedLogs, bint _bDisplayGUI) 
					: m_GeneratedLogs(_GeneratedLogs)
					, m_bDisplayGUI(_bDisplayGUI)
				{
				}
				NStr::CStr m_Message;
				NStr::CStr m_ExtraLog;
			};

			LONG CSubSystem_Debug_Platform_Windows::fsp_ExceptionGenerateHandler(struct _EXCEPTION_POINTERS *_pExceptionInfo, void *_pData)
			{
				CExceptionData *pData = (CExceptionData *)_pData;
				fsp_DumpExceptionInformation(_pExceptionInfo, pData->m_Message, pData->m_ExtraLog, &pData->m_GeneratedLogs, pData->m_bDisplayGUI);

				return EXCEPTION_EXECUTE_HANDLER;
			}

			void CSubSystem_Debug_Platform_Windows::f_EnableCrashDumpCaches()
			{
				if (!g_bIsDll)
				{
					for (mint i = 0; i < EWindowCache; ++i)
					{
						if (!m_CacheWindows[i])
							m_CacheWindows[i] = CreateWindowA("MalterlibCrashDumpWindowCache", "MalterlibCrashDumpWindowCache", 0, 0, 0, 0, 0, HWND_MESSAGE, 0, 0, 0);
					}
				}
			}

			void CSubSystem_Debug_Platform_Windows::f_GenerateCrashDump(const NStr::CStr &_Message, const NStr::CStr &_ExtraLog, NContainer::TCVector<NMib::NStr::CStr> &_GeneratedLogs, bint _bDisplayGUI)
			{

				CExceptionData Data(_GeneratedLogs, _bDisplayGUI);
				Data.m_Message = _Message;
				Data.m_ExtraLog = _ExtraLog;

				NMib::NPlatform::fg_GenerateExcetionHandler(&Data, &CSubSystem_Debug_Platform_Windows::fsp_ExceptionGenerateHandler);
			}

			class CSubSystem_Debug_Platform_Windows::CExceptionMemoryData
			{
			public:
				NMib::NContainer::TCVector<void*, NMemory::CAllocator_NonTrackedHeap> const& m_Locations;
				NMib::NContainer::TCVector<mint, NMib::NMemory::CAllocator_NonTrackedHeap> const& m_Sizes;
				mint m_iCurrentLocation;

				CExceptionMemoryData
					(
						NMib::NContainer::TCVector<void*, NMemory::CAllocator_NonTrackedHeap> const& _Locations
						, NMib::NContainer::TCVector<mint, NMib::NMemory::CAllocator_NonTrackedHeap> const& _Sizes
					) 
					: m_Locations(_Locations)
					, m_Sizes(_Sizes)
					, m_iCurrentLocation(0)
				{
				}
			};

			LONG CSubSystem_Debug_Platform_Windows::fsp_ExceptionGenerateHandlerMemory(struct _EXCEPTION_POINTERS *_pExceptionInfo, void *_pData)
			{
				CExceptionMemoryData *pData = (CExceptionMemoryData *)_pData;
				fsp_DumpExceptionMemory(_pExceptionInfo, pData);

				return EXCEPTION_EXECUTE_HANDLER;
			}

			void CSubSystem_Debug_Platform_Windows::f_GenerateMemoryDump
				(
					NMib::NContainer::TCVector<void*, NMemory::CAllocator_NonTrackedHeap> const& _Locations
					, NMib::NContainer::TCVector<mint, NMib::NMemory::CAllocator_NonTrackedHeap> const& _Sizes
				)
			{
				CExceptionMemoryData Data(_Locations, _Sizes);
				NMib::NPlatform::fg_GenerateExcetionHandler(&Data, &fsp_ExceptionGenerateHandlerMemory);
			}

	
			void CSubSystem_Debug_Platform_Windows::f_SetCrashDumpUserNotifyFunction(NSys::FCrashDumpUserNotify *_pCrashDumpUserNotify)
			{
				m_pCrashDumpUserNotifyFunction = _pCrashDumpUserNotify;
			}

			void CSubSystem_Debug_Platform_Windows::f_SetCrashDumpUserNotifyFormats(const NStr::CStrNonTracked &_CustomMessage, const NStr::CStrNonTracked &_CanContinueMessage, const NStr::CStrNonTracked &_NoContinueMessage)
			{
				m_CrashDumpUserNotifyFormat_CustomMessage = _CustomMessage;
				m_CrashDumpUserNotifyFormat_CanContinueMessage = _CanContinueMessage;
				m_CrashDumpUserNotifyFormat_NoContinueMessage = _NoContinueMessage;
			}

			BOOL CALLBACK CSubSystem_Debug_Platform_Windows::fp_DumpExceptionMemoryCallback
				(
					PVOID _pParam, 
					const PMINIDUMP_CALLBACK_INPUT _pInput, 
					PMINIDUMP_CALLBACK_OUTPUT _pOutput 
				) 
			{
				if (_pInput->CallbackType == MemoryCallback)
				{
					CExceptionMemoryData & Data = *(CExceptionMemoryData *)_pParam;

					if (Data.m_iCurrentLocation < Data.m_Locations.f_GetLen())
					{
						_pOutput->MemoryBase = (ULONG64)Data.m_Locations[Data.m_iCurrentLocation];
						_pOutput->MemorySize = Data.m_Sizes[Data.m_iCurrentLocation];

						++Data.m_iCurrentLocation;
						return true;
					}
					else
						return false;
				}

				return true;
			}

			LONG WINAPI CSubSystem_Debug_Platform_Windows::fsp_DumpExceptionMemory
				(
					struct _EXCEPTION_POINTERS *_pExceptionInfo
					, CExceptionMemoryData * _pExceptionMemoryData
				)
			{
				DMibDeadlockDetectorPause;
				auto &SubSystem = fg_Debug_Platfrom_Windows();
				DMibLock(SubSystem.m_DumpExceptionInfoLock);

				auto fl_GenerateException
					= [&_pExceptionMemoryData, _pExceptionInfo](NThread::CThreadObjectNonTracked *_pThread) -> aint
					{
						mint nCache = EWindowCache;
						auto &SubSystem = fg_Debug_Platfrom_Windows();

						NStr::CStrNonTracked CrashDumpPath = NFile::NPlatform::fg_ConvertFromWindowsPath<NStr::CWStrNonTracked, NStr::CWStrNonTracked>(NSys::fg_Process_GetEnvironmentVariable_NonProtected(NStr::CStrNonTracked("IdsCrashDumpDir")));
						if (CrashDumpPath.f_IsEmpty() || !fs_CheckAccessRights(CrashDumpPath))
						{
							CrashDumpPath = NMib::NFile::CFile::fs_AppendPath(NMib::fg_GetSys()->f_GetProgramRootNonTracked(), NStr::CStrNonTracked("CrashDumps"));
							if (!fs_CheckAccessRights(CrashDumpPath))
							{
								CrashDumpPath = NMib::NFile::CFile::fs_AppendPath(NFile::CFile::fs_GetProgramDirectoryNonTracked(), NStr::CStrNonTracked("CrashDumps"));
								if (!fs_CheckAccessRights(CrashDumpPath))
								{
									CrashDumpPath = NMib::NFile::CFile::fs_AppendPath(NFile::CFile::fs_GetUserLocalProgramDirectoryNonTracked(), NStr::CStrNonTracked("CrashDumps"));
									if (!fs_CheckAccessRights(CrashDumpPath))
									{
										return EXCEPTION_CONTINUE_SEARCH;
									}
								}
							}
						}

						NStr::CStrNonTracked FileNameDumpMini;

						{
							NTime::CTimeConvert::CDateTime DateTime;
							NTime::CTimeConvert(NTime::CTime::fs_NowLocal()).f_ExtractDateTime(DateTime);

							int32 Fraction = (DateTime.m_Fraction*1000.0).f_ToIntRound();
							if (Fraction >= 1000)
								Fraction = 999;

							uint32 RandomValue = SubSystem.f_GetRandom();

							FileNameDumpMini = CrashDumpPath + (NStr::CStrNonTracked::CFormat("/MemoryDump_{}-{sj2,sf0}-{sj2,sf0}_{sj2,sf0}.{sj2,sf0}.{sj2,sf0}.{sj3,sf0}.{sj8,sf0,nfh}.dmp")
								<< DateTime.m_Year << DateTime.m_Month << DateTime.m_DayOfMonth << DateTime.m_Hour << DateTime.m_Minute << DateTime.m_Second << Fraction << RandomValue).f_GetStr();
						}
						// Mini dump
						{
							NStr::CStrNonTracked StackTraceError;
							bint bRet;
							if (_pThread)
								bRet = SubSystem.m_StackTrace.f_Init(StackTraceError);
							else
							{
								NStr::CFStr256 Info;
								bRet = SubSystem.m_StackTrace.f_InitDll(Info);
								StackTraceError = Info;
							}
					
							if (bRet)
							{
								if (SubSystem.m_StackTrace.MiniDumpWriteDump)
								{
									MINIDUMP_EXCEPTION_INFORMATION Info;
									Info.ClientPointers = false;
									Info.ExceptionPointers = _pExceptionInfo;
									Info.ThreadId = GetCurrentThreadId();
							
									MINIDUMP_CALLBACK_INFORMATION CallbackInfo; 
									CallbackInfo.CallbackRoutine = (MINIDUMP_CALLBACK_ROUTINE)&fp_DumpExceptionMemoryCallback; 
									CallbackInfo.CallbackParam = (void*)_pExceptionMemoryData;

									NFile::CFile File;
									File.f_Open(FileNameDumpMini, NFile::EFileOpen_Write);
									if (File.f_IsValid())
									{
										MINIDUMP_TYPE DumpType = (MINIDUMP_TYPE )(MiniDumpWithHandleData | MiniDumpWithIndirectlyReferencedMemory | MiniDumpWithProcessThreadData);
										if (!SubSystem.m_StackTrace.MiniDumpWriteDump(SubSystem.m_StackTrace.m_hProcess, GetCurrentProcessId(), File.f_GetOSFile(), DumpType, &Info, nullptr, &CallbackInfo))
										{
											NStr::CFStr256 ErrorStr = NStr::CFStr256::CFormat("Could not write mini dump. The error was: {}") << NMib::NPlatform::fg_Win32_GetLastErrorStr(GetLastError());
											DMibDTrace("{}\n", ErrorStr);
										}
									}
								}
							}
						} 

						return EXCEPTION_CONTINUE_EXECUTION;
					}
				;
		
				if (NMib::NPlatform::fg_ThisThreadOwnsDllLock() || g_bDoneMalterlibInitAll.f_Load() < 3)
				{
					// If Dll lock is held we will get a deadlock here
					return fl_GenerateException(nullptr);
				}
				else
				{
					NStorage::TCUniquePointer<NThread::CThreadObjectNonTracked, NMemory::CAllocator_NonTrackedHeap> pThread
						= NThread::CThreadObjectNonTracked::fs_StartThread(fl_GenerateException, "DumpExceptionsThread")
					;
					pThread->f_Stop();
					return pThread->f_GetReturnValue();
				}
			}	

		}
	}
}
