// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include <Mib/Debug/Debug>
#include <Mib/Core/PlatformSpecific/WindowsFilePath>
#include <Mib/Core/PlatformSpecific/WindowsOptional>
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

			typedef struct _LDR_DLL_LOADED_NOTIFICATION_DATA 
			{
				ULONG Flags;                    //Reserved.
				PCUNICODE_STRING FullDllName;   //The full path name of the DLL module.
				PCUNICODE_STRING BaseDllName;   //The base file name of the DLL module.
				PVOID DllBase;                  //A pointer to the base address for the DLL in memory.
				ULONG SizeOfImage;              //The size of the DLL image, in bytes.
			} LDR_DLL_LOADED_NOTIFICATION_DATA, *PLDR_DLL_LOADED_NOTIFICATION_DATA;

			typedef struct _LDR_DLL_UNLOADED_NOTIFICATION_DATA 
			{
				ULONG Flags;                    //Reserved.
				PCUNICODE_STRING FullDllName;   //The full path name of the DLL module.
				PCUNICODE_STRING BaseDllName;   //The base file name of the DLL module.
				PVOID DllBase;                  //A pointer to the base address for the DLL in memory.
				ULONG SizeOfImage;              //The size of the DLL image, in bytes.
			} LDR_DLL_UNLOADED_NOTIFICATION_DATA, *PLDR_DLL_UNLOADED_NOTIFICATION_DATA;

			typedef union _LDR_DLL_NOTIFICATION_DATA 
			{
				LDR_DLL_LOADED_NOTIFICATION_DATA Loaded;
				LDR_DLL_UNLOADED_NOTIFICATION_DATA Unloaded;
			} LDR_DLL_NOTIFICATION_DATA, *PLDR_DLL_NOTIFICATION_DATA;

	
			typedef VOID (NTAPI *PLDR_DLL_NOTIFICATION_FUNCTION )(ULONG NotificationReason, const PLDR_DLL_NOTIFICATION_DATA NotificationData, PVOID Context);

			static VOID NTAPI DllLoadedCallback(ULONG NotificationReason, const PLDR_DLL_NOTIFICATION_DATA NotificationData, PVOID Context)
			{
				CSubSystem_Debug_Platform_Windows *pThis = (CSubSystem_Debug_Platform_Windows *)Context;
				pThis->m_bPollCheckExceptionFilterTimes = 1000/25;
				pThis->m_ExceptionFilterPoller.m_EventWantQuit.f_Signal();
				if (!fg_GetSys()->f_DestroyingThreadSpecific() && pThis->m_bExceptionFilterPollerInstalled.f_Exchange(1) == 0)
					pThis->m_ExceptionFilterPoller.f_Start();

				/*if (NotificationReason == 1)
					DMibTraceSafe("Loaded: {}\r\n", NotificationData->Loaded.FullDllName->Buffer);
				else if (NotificationReason == 2)
					DMibTraceSafe("Unlaoded: {}\r\n", NotificationData->Unloaded.FullDllName->Buffer);
				else
					DMibTraceSafe("Unknown loaded code", 0);*/
			}


			NStr::CStr CSubSystem_Debug_Platform_Windows::CExceptionFilterPoller::f_GetThreadName()
			{
				return "Malterlib_Core_PlatformImp_ExceptionFilterPoller";
			}

			CSubSystem_Debug_Platform_Windows::CExceptionFilterPoller::CExceptionFilterPoller()
			{
			}
		
			CSubSystem_Debug_Platform_Windows::CExceptionFilterPoller::~CExceptionFilterPoller()
			{
			}

			inline_never void CSubSystem_Debug_Platform_Windows::CExceptionFilterPoller::f_PollFilter()
			{
				if (m_pSystem->m_bPollCheckExceptionFilter || m_pSystem->m_bPollCheckExceptionFilterTimes)
				{
					int64 Timer = NMib::NTime::NPlatform::fg_TimerRaw_PreciseGet();
					//DMibDTrace("Checking Exception Filter {} {}\r\n", m_pSystem->m_bPollCheckExceptionFilterTimes << Timer);
					if (m_pSystem->m_bPollCheckExceptionFilterTimes)
						--m_pSystem->m_bPollCheckExceptionFilterTimes;
					LPTOP_LEVEL_EXCEPTION_FILTER pTop = SetUnhandledExceptionFilter(&CSubSystem_Debug_Platform_Windows::fsp_UnhandledException);
					if (pTop != &CSubSystem_Debug_Platform_Windows::fsp_UnhandledException)
					{
						DMibDTrace("ATTENTION: ATTENTION: ATTENTION: ATTENTION: ATTENTION: ATTENTION: Unhandled exception filter was lost({} != {}): {}\n", pTop << &CSubSystem_Debug_Platform_Windows::fsp_UnhandledException << Timer);
						//m_pSystem->m_pPrevExceptionFilter = pTop;
					}
				}
			}

			aint CSubSystem_Debug_Platform_Windows::CExceptionFilterPoller::f_Main()
			{
				while (f_GetState() != NThread::EThreadState_EventWantQuit)
				{
					f_PollFilter();

					if (m_pSystem->m_bPollCheckExceptionFilterTimes)
						m_EventWantQuit.f_WaitTimeout(0.025);
					else if (m_pSystem->m_bPollCheckExceptionFilter)
						m_EventWantQuit.f_WaitTimeout(5.0);
					else
						m_EventWantQuit.f_Wait();
				}

				return 0;
			}

			void CSubSystem_Debug_Platform_Windows::f_InstallExceptionFilterCallback(bool _bDoInstall)
			{
				m_ExceptionFilterPoller.m_pSystem = this;
				m_bPollCheckExceptionFilter = true;
				m_pDllNotificationCookie = nullptr;
				if (_bDoInstall)
				{
					HMODULE pNTDll = NLocal::g_hNtDll;
					if (pNTDll)
					{
						NTSTATUS (NTAPI *pLdrRegisterDllNotification)(ULONG Flags, PLDR_DLL_NOTIFICATION_FUNCTION NotificationFunction, PVOID Context, PVOID *Cookie);

						(FARPROC &)pLdrRegisterDllNotification = GetProcAddress(pNTDll, "LdrRegisterDllNotification");

						if (pLdrRegisterDllNotification)
						{
							m_bPollCheckExceptionFilter = false;
							pLdrRegisterDllNotification(0, DllLoadedCallback, this, &m_pDllNotificationCookie);
						}
					}

					if (m_bPollCheckExceptionFilter)
					{
						if (m_bExceptionFilterPollerInstalled.f_Exchange(1) == 0)
							m_ExceptionFilterPoller.f_Start();
					}
				}
			}

			void CSubSystem_Debug_Platform_Windows::f_UninstallExceptionFilterCallback()
			{
				m_ExceptionFilterPoller.f_Stop();
				if (m_pDllNotificationCookie)
				{
					HMODULE pNTDll = NLocal::g_hNtDll;
					if (pNTDll)
					{
						NTSTATUS (NTAPI *pLdrUnregisterDllNotification)(PVOID Cookie);

						(FARPROC &)pLdrUnregisterDllNotification = GetProcAddress(pNTDll, "LdrUnregisterDllNotification");

						if (pLdrUnregisterDllNotification)
						{
							pLdrUnregisterDllNotification(m_pDllNotificationCookie);
							m_pDllNotificationCookie = nullptr;
						}
					}
				}

			}
		}
	}
}
