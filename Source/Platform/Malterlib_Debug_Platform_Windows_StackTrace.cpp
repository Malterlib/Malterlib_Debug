// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <Mib/Core/Core>
#include <Mib/Core/PlatformSpecific/WindowsError>
#include <Mib/Core/PlatformSpecific/WindowsString>

#pragma warning(disable:4091)
#include <Windows.h>
#include <DbgHelp.h>

#include "Malterlib_Debug_Platform_Windows_StackTrace.h"

extern int g_MalterlibDisableStackTraceContext;

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			static constexpr umint gc_SymbolSize = sizeof(IMAGEHLP_SYMBOL64) + 4096;

			CStackTraceContext::CStackTraceContext()
			{
				m_bInitialized = false;
				m_bInitializedDll = false;
				m_fSymInitialize = nullptr;
				m_fSymCleanup = nullptr;
				m_DbgHelp = nullptr;
				m_SymSrv = nullptr;
				m_pSymbolInfo = nullptr;
				m_fMiniDumpWriteDump = nullptr;
				m_bFailedInitialize = false;
				m_bFailedInitializeDll = false;
				m_Process = INVALID_HANDLE_VALUE;
				m_Stopwatch.f_Start();
			}

			CStackTraceContext::~CStackTraceContext()
			{
				if (m_bInitialized)
					m_fSymCleanup(m_Process);

				if (m_Process != INVALID_HANDLE_VALUE)
					CloseHandle(m_Process);

				if (m_pSymbolInfo)
					NMemory::CAllocator_NonTrackedHeap::f_Free(m_pSymbolInfo, gc_SymbolSize);

				if (m_DbgHelp)
					FreeLibrary(m_DbgHelp);
				if (m_SymSrv)
					FreeLibrary(m_SymSrv);

				f_RemoveUnused();

				while (m_TraceInfoTree.f_GetRoot())
				{
					CLocalStackTraceInfo *pInfo = m_TraceInfoTree.f_GetRoot();
					if (pInfo->m_pFunctionName)
						NMemory::CAllocator_NonTrackedHeap::f_Free((ch8 *)pInfo->m_pFunctionName, NStr::fg_StrLen(pInfo->m_pFunctionName) + 1);
					if (pInfo->m_pModuleName)
						NMemory::CAllocator_NonTrackedHeap::f_Free((ch8 *)pInfo->m_pModuleName, NStr::fg_StrLen(pInfo->m_pModuleName) + 1);
					if (pInfo->m_pSourceFileName)
						NMemory::CAllocator_NonTrackedHeap::f_Free((ch8 *)pInfo->m_pSourceFileName, NStr::fg_StrLen(pInfo->m_pSourceFileName) + 1);

					m_TraceInfoTree.f_Remove(pInfo);

					NStorage::TCUniquePointer<CLocalStackTraceInfo, NMemory::CAllocator_NonTrackedHeap> pInfoDelete = fg_Explicit(pInfo);
				}
			}

			CStackTraceContext::CLocalStackTraceInfo::CLocalStackTraceInfo()
			{
				m_pFunctionName = nullptr;
				m_pModuleName = nullptr;
				m_pSourceFileName = nullptr;
				this->m_pContext = nullptr;
				m_SourceLine = 0;
				m_RefCount = 1;
			}

			bool CStackTraceContext::f_InitDll(NStr::CFStr256 &_Error)
			{
				DMibLockTyped(NThread::CMutual, m_Lock);
				if (m_bInitializedDll)
					return true;

				if (m_bFailedInitializeDll)
					return false;

				auto InitLambda = [&]() -> bool
					{
#ifdef DArchitecture_x64
#	define DMibPlatformDir "\\x64"
#else
#	define DMibPlatformDir "\\x86"
#endif

						NStr::CStrNonTracked ProgramRoot = fg_GetSys()->f_GetProgramRootNonTracked();
						fg_StrReplaceChar(ProgramRoot, '/', '\\');

						NStr::CStrNonTracked ProgramPath = NMib::NFile::CFile::fs_GetProgramDirectoryNonTracked();
						fg_StrReplaceChar(ProgramPath, '/', '\\');

						if (!m_DbgHelp)
						{
							NStr::CStrNonTracked DebugHelpDLL = "\\DebugHelp" DMibPlatformDir "\\Dbghelp.dll";

							m_DbgHelp = (HMODULE)NSys::fg_LoadLibrary(ProgramRoot + DebugHelpDLL);

							if (!m_DbgHelp)
								m_DbgHelp = (HMODULE)NSys::fg_LoadLibrary(ProgramPath + DebugHelpDLL);

							if (!m_DbgHelp)
								m_DbgHelp = (HMODULE)NSys::fg_LoadLibrary(NStr::CStrNonTracked("Dbghelp.dll"));
						}

						// Apperantly some bug in Dbghelp.dll causes symsrv.dll to be unloaded while other modules are still holding a handle to it. Try to prevent this here by adding a
						// reference to the library.
						if (!m_SymSrv)
						{
							NStr::CStrNonTracked SymServDLL = "\\DebugHelp" DMibPlatformDir "\\SymSrv.dll";

							m_SymSrv = (HMODULE)NSys::fg_LoadLibrary(ProgramRoot + SymServDLL);

							if (!m_SymSrv)
								m_SymSrv = (HMODULE)NSys::fg_LoadLibrary(ProgramPath + SymServDLL);

							if (!m_SymSrv)
								m_SymSrv = (HMODULE)NSys::fg_LoadLibrary(NStr::CStrNonTracked("SymSrv.dll"));
						}

#undef DMibPlatformDir

						if (!m_DbgHelp)
						{
							m_bFailedInitializeDll = true;
							_Error = "Dbghelp.dll not found";
							DMibDTrace("StackTrace: Failed to load DbgHelp.dll\n", 0);

							return false;
						}

						m_fSymInitialize = (FSymInitialize *)GetProcAddress(m_DbgHelp, "SymInitializeW");
						m_fSymCleanup = (FSymCleanup *)GetProcAddress(m_DbgHelp, "SymCleanup");
						m_fSymRefreshModuleList = (FSymRefreshModuleList *)GetProcAddress(m_DbgHelp, "SymRefreshModuleList");
						m_fSymGetSymFromAddr64 = (FSymGetSymFromAddr64 *)GetProcAddress(m_DbgHelp, "SymGetSymFromAddr64");
						m_fSymGetLineFromAddr64 = (FSymGetLineFromAddr64 *)GetProcAddress(m_DbgHelp, "SymGetLineFromAddr64");
						m_fSymGetModuleInfo64 = (FSymGetModuleInfo64 *)GetProcAddress(m_DbgHelp, "SymGetModuleInfo64");
						m_fMiniDumpWriteDump = (FMiniDumpWriteDump *)GetProcAddress(m_DbgHelp, "MiniDumpWriteDump");
						m_fUnDecorateSymbolName = (FUnDecorateSymbolName *)GetProcAddress(m_DbgHelp, "UnDecorateSymbolName");

						if
						(
							!m_fSymInitialize
							|| !m_fSymCleanup
							|| !m_fSymGetSymFromAddr64
							|| !m_fSymGetLineFromAddr64
							|| !m_fSymGetModuleInfo64
							|| !m_fMiniDumpWriteDump
							|| !m_fSymRefreshModuleList
						)
						{
							m_bFailedInitializeDll = true;
							FreeLibrary(m_DbgHelp);
							m_DbgHelp = nullptr;
							_Error
								= "Dbghelp.dll dose not contain !SymInitialize || !SymCleanup || !SymGetSymFromAddr64 || !SymGetLineFromAddr64 || !SymGetModuleInfo64 || !MiniDumpWriteDump"
							;
							DMibDTrace("---------------------------------------------------------------------------------------------------------------------\n", 0);
							for (int iRepeat = 0; iRepeat < 25; ++iRepeat)
								DMibDTrace("StackTrace: DbgHelp.dll does not contain the needed functions\n", 0);
							DMibDTrace("---------------------------------------------------------------------------------------------------------------------\n", 0);
							return false;
						}
						return true;
					}
				;

				bool bReturn = InitLambda();

				if (!bReturn)
					return false;

				m_bInitializedDll = true;
				return true;
			}

			bool CStackTraceContext::f_Init(NStr::CStrNonTracked &_Error)
			{
				DMibLockTyped(NThread::CMutual, m_Lock);
				if (m_bInitialized)
					return true;

				if (m_bFailedInitialize)
					return false;

				NStr::CFStr256 Error;
				if (!f_InitDll(Error))
				{
					_Error = Error;
					return false;
				}

				auto InitLambda = [&]() -> bool
					{
						NStr::CWStrNonTracked Strings = NSys::NFile::fg_GetProgramDirectoryNonTracked();

						NStr::CWStrNonTracked TempStr;
						using namespace NMib::NStr::NPlatform;
						GetEnvironmentVariableW(str_utf16("_NT_SYMBOL_PATH"), TempStr.f_GetStr(gc_MaxWindowsEnvVarLength), gc_MaxWindowsEnvVarLength);

						if (TempStr.f_GetLen())
							Strings = Strings + ";" + TempStr;
						else
						{
							GetEnvironmentVariableW(str_utf16("_NT_ALTERNATE_SYMBOL_PATH"), TempStr.f_GetStr(gc_MaxWindowsEnvVarLength), gc_MaxWindowsEnvVarLength);

							if (TempStr.f_GetLen())
								Strings = Strings + ";" + TempStr;
							else
							{
								GetEnvironmentVariableW(str_utf16("SystemRoot"), TempStr.f_GetStr(gc_MaxWindowsEnvVarLength), gc_MaxWindowsEnvVarLength);

								if (TempStr.f_GetLen())
									Strings = Strings + ";" + TempStr + "\\Symbols";

								GetEnvironmentVariableW(str_utf16("PATH"), TempStr.f_GetStr(gc_MaxWindowsEnvVarLength), gc_MaxWindowsEnvVarLength);

								if (TempStr.f_GetLen())
									Strings = Strings + ";" + TempStr;
							}
						}

						m_Process = OpenProcess(PROCESS_ALL_ACCESS, false, GetCurrentProcessId());
						if (m_Process == INVALID_HANDLE_VALUE)
						{
							DMibDTrace("StackTrace: SymInitialize failed\n", 0);
							_Error = "Could not open process handle";
							m_bFailedInitialize = true;
							return false;
						}

						if (!g_MalterlibDisableStackTraceContext)
						{
							if (!m_fSymInitialize(m_Process, (ch16 *)Strings.f_GetStr(), false))
							{
								if (!m_fSymInitialize(m_Process, nullptr, false))
								{
									_Error = NStr::CStrNonTracked::CFormat("SymInitialize failed with {}") << NMib::NPlatform::fg_Win32_GetLastErrorStr(GetLastError());
									DMibDTraceSafe("{}\n", _Error);
									m_bFailedInitialize = true;
									return false;
								}
							}

							if (!m_pSymbolInfo)
								m_pSymbolInfo = (IMAGEHLP_SYMBOL64 *)NMemory::CAllocator_NonTrackedHeap::f_Alloc(gc_SymbolSize);

							m_fSymRefreshModuleList(m_Process);
						}
						return true;
					}
				;

				bool bReturn = InitLambda();

				if (!bReturn)
					return false;

				m_bInitialized = true;
				return true;
			}

			void CStackTraceContext::f_UndecorateName(ch8 const *_pName, NStr::CStr &_Destination)
			{
				NStr::CStr Dest;
				f_UndecorateName(_pName, Dest.f_GetStr(4096), 4096);
				Dest.f_SetModified();
				_Destination = Dest;
			}

			void CStackTraceContext::f_UndecorateName(ch8 const *_pName, NStr::CStrNonTracked &_Destination)
			{
				NStr::CStrNonTracked Dest;
				f_UndecorateName(_pName, Dest.f_GetStr(4096), 4096);
				Dest.f_SetModified();
				_Destination = Dest;
			}

			void CStackTraceContext::f_UndecorateName(ch8 const *_pName, ch8 *_pDestination, umint _MaxLen)
			{
				if (!m_bInitializedDll)
				{
					NStr::CFStr256 Temp;
					if (!f_InitDll(Temp))
					{
						*_pDestination = 0;
						return;
					}
				}
				if (!m_fUnDecorateSymbolName)
				{
					*_pDestination = 0;
					return;
				}
				uint32 Flags = 0;
#ifndef DArchitecture_x64
				Flags |= UNDNAME_32_BIT_DECODE;
#endif
				umint nChars = m_fUnDecorateSymbolName(_pName, _pDestination, _MaxLen, Flags);
				if (!nChars)
				{
					[[maybe_unused]] HRESULT LastError = GetLastError();
					DMibDTraceSafe("UnDecorateSymbolName: {}\r\n", NMib::NPlatform::fg_Win32_GetLastErrorStr(LastError));
				}
			}

			CStackTraceContext::CLocalStackTraceInfo *CStackTraceContext::f_AquireStackTraceInfo(umint _Address)
			{
				DMibLockTyped(NThread::CMutual, m_Lock);

				if (!m_bInitialized)
				{
					NStr::CStrNonTracked Temp;
					if (!f_Init(Temp))
						return nullptr;
				}

				if (!m_pSymbolInfo)
					return nullptr;

				CLocalStackTraceInfo *pLocalInfo = m_TraceInfoTree.f_FindEqual(_Address);
				if (pLocalInfo)
				{
					if ((++pLocalInfo->m_RefCount) == 1)
						pLocalInfo->m_UnusedList.f_Unlink();
					return pLocalInfo;
				}

				DWORD64 Displacement;
				m_pSymbolInfo->SizeOfStruct = sizeof(IMAGEHLP_SYMBOL64);
				m_pSymbolInfo->MaxNameLength = 4096;
				if (!m_fSymGetSymFromAddr64(m_Process, _Address, &Displacement, m_pSymbolInfo))
					return nullptr;

				pLocalInfo = new(NMemory::CAllocator_NonTrackedHeap::f_Alloc(sizeof(CLocalStackTraceInfo))) CLocalStackTraceInfo();
				pLocalInfo->m_Address = _Address;
				m_TraceInfoTree.f_Insert(pLocalInfo);

				int Len = NStr::fg_StrLen(m_pSymbolInfo->Name);
				ch8 *pStr;
				pLocalInfo->m_pFunctionName = pStr = (ch8 *)NMemory::CAllocator_NonTrackedHeap::f_Alloc(Len + 1);
				NMemory::fg_MemCopy(pStr, m_pSymbolInfo->Name, Len);
				pStr[Len] = 0;

				{
					IMAGEHLP_LINE64 LineInfo;
					LineInfo.SizeOfStruct = sizeof(IMAGEHLP_LINE64);
					DWORD Displacement;
					if (m_fSymGetLineFromAddr64(m_Process, _Address, &Displacement, &LineInfo))
					{
						ch8 const *pName = LineInfo.FileName;
						static constexpr ch8 const *c_pCrtStrip[] =
							{
								"f:\\rtm\\vctools\\crt_bld\\self_x86\\crt\\src\\"
								, "f:\\sp\\vctools\\crt_bld\\self_x86\\crt\\src\\"
								, "f:\\dd\\vctools\\crt_bld\\self_x86\\crt\\src\\"
								// ,"f:\\dd\\vctools\\crt_bld\\self_x86\\crt\\prebuild\\eh\\"
							}
						;

						NStr::CStr Temp;
						for (auto &pStrip : c_pCrtStrip)
						{
							aint CrtPos = NStr::fg_StrFind(pName, pStrip);
							if (CrtPos == 0)
							{
								Temp = "X:\\Apps\\Dev\\VS.2010\\VC\\Crt\\src\\";
								Temp += (pName + NStr::fg_StrLen(pStrip));
								pName = Temp;
								break;
							}
						}

						int Len = NStr::fg_StrLen(pName);
						pLocalInfo->m_pSourceFileName = pStr = (ch8 *)NMemory::CAllocator_NonTrackedHeap::f_Alloc(Len + 1);
						NMemory::fg_MemCopy(pStr, pName, Len);
						pStr[Len] = 0;
						pLocalInfo->m_SourceLine = LineInfo.LineNumber;
					}
					else
					{
						pLocalInfo->m_pSourceFileName = pStr = (ch8 *)NMemory::CAllocator_NonTrackedHeap::f_Alloc(1);
						pStr[0] = 0;
					}
				}
				{
					IMAGEHLP_MODULE64 ModuleInfo;
					ModuleInfo.SizeOfStruct = sizeof(ModuleInfo);
					if (m_fSymGetModuleInfo64(m_Process, _Address, &ModuleInfo))
					{
						int Len = NStr::fg_StrLen(ModuleInfo.ImageName);
						pLocalInfo->m_pModuleName = pStr = (ch8 *)NMemory::CAllocator_NonTrackedHeap::f_Alloc(Len + 1);
						NMemory::fg_MemCopy(pStr, ModuleInfo.ImageName, Len);
						pStr[Len] = 0;
					}
					else
					{
						pLocalInfo->m_pModuleName = pStr = (ch8 *)NMemory::CAllocator_NonTrackedHeap::f_Alloc(1);
						pStr[0] = 0;
					}
				}
				return pLocalInfo;
			}

			void CStackTraceContext::f_RemoveUnused()
			{
				while (m_Usused.f_GetFirst())
				{
					CLocalStackTraceInfo *pInfo = m_Usused.f_Pop();

					m_TraceInfoTree.f_Remove(pInfo);

					if (pInfo->m_pFunctionName)
						NMemory::CAllocator_NonTrackedHeap::f_Free((ch8 *)pInfo->m_pFunctionName, NStr::fg_StrLen(pInfo->m_pFunctionName) + 1);
					if (pInfo->m_pModuleName)
						NMemory::CAllocator_NonTrackedHeap::f_Free((ch8 *)pInfo->m_pModuleName, NStr::fg_StrLen(pInfo->m_pModuleName) + 1);
					if (pInfo->m_pSourceFileName)
						NMemory::CAllocator_NonTrackedHeap::f_Free((ch8 *)pInfo->m_pSourceFileName, NStr::fg_StrLen(pInfo->m_pSourceFileName) + 1);

					NStorage::TCUniquePointer<CLocalStackTraceInfo, NMemory::CAllocator_NonTrackedHeap> pInfoDel = fg_Explicit(pInfo);
				}
			}

			void CStackTraceContext::f_ReleaseStackTraceInfo(CLocalStackTraceInfo *_pInfo)
			{
				DMibLockTyped(NThread::CMutual, m_Lock);

				DMibSafeCheck(m_bInitialized, "If we are here we should be initialized");

				if ((--(_pInfo)->m_RefCount) == 0)
					m_Usused.f_Insert(_pInfo);

				if (m_Stopwatch.f_GetTime() > fp64(10.0))
				{
					f_RemoveUnused();
					m_Stopwatch.f_Start();
				}
			}
		}
	}
}
