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

					DMibIntrusiveLink(CLocalStackTraceInfo, NIntrusive::TCAVLLink<>, m_AvlLink);
					DMibListLinkD_Link(CLocalStackTraceInfo, m_UnusedList);
					mint m_Address;
					mint m_RefCount;
				};

				class CAVLCompare_CLocalStackTraceInfo
				{
				public:
					inline_small const mint &operator () (CLocalStackTraceInfo const &_Node) const
					{
						return _Node.m_Address;
					}
				};

				bint f_InitDll(NStr::CFStr256 &_Error);
				bint f_Init(NStr::CStrNonTracked &_Error);

				void f_UndecorateName(const ch8 *_pName, NStr::CStr &_Destination);
				void f_UndecorateName(const ch8 *_pName, NStr::CStrNonTracked &_Destination);
				void f_UndecorateName(const ch8 *_pName, ch8 *_pDestination, mint _MaxLen);
				CLocalStackTraceInfo *f_AquireStackTraceInfo(mint _Address);
				void f_RemoveUnused();
				void f_ReleaseStackTraceInfo(CLocalStackTraceInfo *_pInfo);


				typedef BOOL (__stdcall FSymInitialize)(IN HANDLE hProcess, IN PWSTR UserSearchPath, IN BOOL fInvadeProcess);
				typedef BOOL (__stdcall FSymCleanup)(IN HANDLE hProcess);
				typedef BOOL (__stdcall FSymRefreshModuleList)(__in HANDLE hProcess);

				typedef BOOL (__stdcall FSymGetSymFromAddr64)(IN HANDLE hProcess,IN DWORD64 Address,OUT PDWORD64 Displacement,IN OUT PIMAGEHLP_SYMBOL64 Symbol);
				typedef BOOL (__stdcall FSymGetLineFromAddr64)(IN HANDLE hProcess,IN DWORD64 dwAddr, OUT PDWORD pdwDisplacement, OUT PIMAGEHLP_LINE64 Line);
				typedef BOOL (__stdcall FSymGetModuleInfo64)(IN HANDLE hProcess,IN DWORD64 qwAddr, OUT PIMAGEHLP_MODULE64 ModuleInfo);
				typedef BOOL (__stdcall FMiniDumpWriteDump)(HANDLE hProcess,DWORD ProcessId,HANDLE hFile,MINIDUMP_TYPE DumpType,PMINIDUMP_EXCEPTION_INFORMATION ExceptionParam,PMINIDUMP_USER_STREAM_INFORMATION UserStreamParam,PMINIDUMP_CALLBACK_INFORMATION CallbackParam);

				typedef DWORD (__stdcall FUnDecorateSymbolName)(PCSTR DecoratedName, PSTR UnDecoratedName, DWORD UndecoratedLength, DWORD Flags);

				NTime::CClock m_Timer;

				NIntrusive::TCAVLTree<CLocalStackTraceInfo::CLinkTraits_m_AvlLink, CAVLCompare_CLocalStackTraceInfo> m_TraceInfoTree;
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

				bint m_bInitialized;
				bint m_bInitializedDll;
				bint m_bFailedInitialize;
				bint m_bFailedInitializeDll;
			};
		}
	}
}

