// Copyright © 2015 Hansoft AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

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
			class CStackTraceContext
			{
			public:
				CStackTraceContext();
				~CStackTraceContext();

				class CAVLCompare_CLocalStackTraceInfo;

				class CLocalStackTraceInfo : public CStackTraceInfo
				{
				public:
					CLocalStackTraceInfo();

					NIntrusive::TCAVLLink<> m_AvlLink;
					DMibListLinkD_Link(CLocalStackTraceInfo, m_UnusedList);
					umint m_Address;
					umint m_RefCount;
				};

				class CAVLCompare_CLocalStackTraceInfo
				{
				public:
					inline_small const umint &operator () (CLocalStackTraceInfo const &_Node) const
					{
						return _Node.m_Address;
					}
				};

				bool f_InitDll(NStr::CFStr256 &_Error);
				bool f_Init(NStr::CStrNonTracked &_Error);

				void f_UndecorateName(const ch8 *_pName, NStr::CStr &_Destination);
				void f_UndecorateName(const ch8 *_pName, NStr::CStrNonTracked &_Destination);
				void f_UndecorateName(const ch8 *_pName, ch8 *_pDestination, umint _MaxLen);
				CLocalStackTraceInfo *f_AquireStackTraceInfo(umint _Address);
				void f_RemoveUnused();
				void f_ReleaseStackTraceInfo(CLocalStackTraceInfo *_pInfo);

				using FSymInitialize = BOOL __stdcall (IN HANDLE hProcess, IN PWSTR UserSearchPath, IN BOOL fInvadeProcess);
				using FSymCleanup = BOOL __stdcall (IN HANDLE hProcess);
				using FSymRefreshModuleList = BOOL __stdcall (__in HANDLE hProcess);
				using FSymGetSymFromAddr64 = BOOL __stdcall (IN HANDLE hProcess,IN DWORD64 Address,OUT PDWORD64 Displacement,IN OUT PIMAGEHLP_SYMBOL64 Symbol);
				using FSymGetLineFromAddr64 = BOOL __stdcall (IN HANDLE hProcess,IN DWORD64 dwAddr, OUT PDWORD pdwDisplacement, OUT PIMAGEHLP_LINE64 Line);
				using FSymGetModuleInfo64 = BOOL __stdcall (IN HANDLE hProcess,IN DWORD64 qwAddr, OUT PIMAGEHLP_MODULE64 ModuleInfo);
				using FMiniDumpWriteDump = BOOL __stdcall (HANDLE hProcess,DWORD ProcessId,HANDLE hFile,MINIDUMP_TYPE DumpType,PMINIDUMP_EXCEPTION_INFORMATION ExceptionParam,PMINIDUMP_USER_STREAM_INFORMATION UserStreamParam,PMINIDUMP_CALLBACK_INFORMATION CallbackParam);
				using FUnDecorateSymbolName = DWORD __stdcall (PCSTR DecoratedName, PSTR UnDecoratedName, DWORD UndecoratedLength, DWORD Flags);

				NTime::CStopwatch m_Stopwatch;

				NIntrusive::TCAVLTree<&CLocalStackTraceInfo::m_AvlLink, CAVLCompare_CLocalStackTraceInfo> m_TraceInfoTree;
				DMibListLinkD_List(CLocalStackTraceInfo, m_UnusedList) m_Usused;

				NThread::CMutual m_Lock;

				FSymInitialize *SymInitialize;
				FSymCleanup *SymCleanup;
				FSymRefreshModuleList *SymRefreshModuleList;
				FSymGetSymFromAddr64 *SymGetSymFromAddr64;
				FSymGetLineFromAddr64 *SymGetLineFromAddr64;
				FSymGetModuleInfo64 *SymGetModuleInfo64;
				FMiniDumpWriteDump *MiniDumpWriteDump;
				FUnDecorateSymbolName *UnDecorateSymbolName;

				HMODULE m_hDbgHelp;
				HMODULE m_hSymSrv;
				IMAGEHLP_SYMBOL64 *m_pSymbolInfo;
				HANDLE m_hProcess;

				bool m_bInitialized;
				bool m_bInitializedDll;
				bool m_bFailedInitialize;
				bool m_bFailedInitializeDll;
			};
		}
	}
}

