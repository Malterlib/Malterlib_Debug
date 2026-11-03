// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <Mib/Core/Core>

#pragma warning(disable:4091)
#include <Windows.h>
#include <DbgHelp.h>

#include <Mib/Debug/Debug>

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			struct CStackTraceContext
			{
				CStackTraceContext();
				~CStackTraceContext();

				struct CAVLCompare_CLocalStackTraceInfo;

				struct CLocalStackTraceInfo : public CStackTraceInfo
				{
					CLocalStackTraceInfo();

					NIntrusive::TCAVLLink<> m_AvlLink;
					DMibListLinkD_Link(CLocalStackTraceInfo, m_UnusedList);
					umint m_Address;
					umint m_RefCount;
				};

				struct CAVLCompare_CLocalStackTraceInfo
				{
					inline_small umint const &operator () (CLocalStackTraceInfo const &_Node) const
					{
						return _Node.m_Address;
					}
				};

				bool f_InitDll(NStr::CFStr256 &_Error);
				bool f_Init(NStr::CStrNonTracked &_Error);

				void f_UndecorateName(ch8 const *_pName, NStr::CStr &_Destination);
				void f_UndecorateName(ch8 const *_pName, NStr::CStrNonTracked &_Destination);
				void f_UndecorateName(ch8 const *_pName, ch8 *_pDestination, umint _MaxLen);
				CLocalStackTraceInfo *f_AquireStackTraceInfo(umint _Address);
				void f_RemoveUnused();
				void f_ReleaseStackTraceInfo(CLocalStackTraceInfo *_pInfo);

				using FSymInitialize = BOOL __stdcall (IN HANDLE _pProcess, IN PWSTR _pUserSearchPath, IN BOOL _bInvadeProcess);
				using FSymCleanup = BOOL __stdcall (IN HANDLE _pProcess);
				using FSymRefreshModuleList = BOOL __stdcall (__in HANDLE _pProcess);
				using FSymGetSymFromAddr64 = BOOL __stdcall (IN HANDLE _pProcess, IN DWORD64 _Address, OUT PDWORD64 o_pDisplacement, IN OUT PIMAGEHLP_SYMBOL64 o_pSymbol);
				using FSymGetLineFromAddr64 = BOOL __stdcall (IN HANDLE _pProcess, IN DWORD64 _Address, OUT PDWORD o_pDisplacement, OUT PIMAGEHLP_LINE64 o_pLine);
				using FSymGetModuleInfo64 = BOOL __stdcall (IN HANDLE _pProcess, IN DWORD64 _Address, OUT PIMAGEHLP_MODULE64 o_pModuleInfo);
				using FMiniDumpWriteDump = BOOL __stdcall
					(
						HANDLE _pProcess
						, DWORD _ProcessID
						, HANDLE _pFile
						, MINIDUMP_TYPE _DumpType
						, PMINIDUMP_EXCEPTION_INFORMATION _pExceptionParam
						, PMINIDUMP_USER_STREAM_INFORMATION _pUserStreamParam
						, PMINIDUMP_CALLBACK_INFORMATION _pCallbackParam
					)
				;
				using FUnDecorateSymbolName = DWORD __stdcall (PCSTR _pDecoratedName, PSTR o_pUndecoratedName, DWORD _UndecoratedLength, DWORD _Flags);

				NTime::CStopwatch m_Stopwatch;

				NIntrusive::TCAVLTree<&CLocalStackTraceInfo::m_AvlLink, CAVLCompare_CLocalStackTraceInfo> m_TraceInfoTree;
				DMibListLinkD_List(CLocalStackTraceInfo, m_UnusedList) m_Usused;

				NThread::CMutual m_Lock;

				FSymInitialize *m_fSymInitialize;
				FSymCleanup *m_fSymCleanup;
				FSymRefreshModuleList *m_fSymRefreshModuleList;
				FSymGetSymFromAddr64 *m_fSymGetSymFromAddr64;
				FSymGetLineFromAddr64 *m_fSymGetLineFromAddr64;
				FSymGetModuleInfo64 *m_fSymGetModuleInfo64;
				FMiniDumpWriteDump *m_fMiniDumpWriteDump;
				FUnDecorateSymbolName *m_fUnDecorateSymbolName;

				HMODULE m_pDbgHelp;
				HMODULE m_pSymSrv;
				IMAGEHLP_SYMBOL64 *m_pSymbolInfo;
				HANDLE m_pProcess;

				bool m_bInitialized;
				bool m_bInitializedDll;
				bool m_bFailedInitialize;
				bool m_bFailedInitializeDll;
			};
		}
	}
}

