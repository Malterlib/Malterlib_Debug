// Copyright © 2015 Hansoft AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

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
			static constexpr mint gc_SymbolSize = sizeof(IMAGEHLP_SYMBOL64) + 4096;

			CStackTraceContext::CStackTraceContext()
			{
				m_bInitialized = false;
				m_bInitializedDll = false;
				SymInitialize = nullptr;
				SymCleanup = nullptr;
				m_hDbgHelp = nullptr;
				m_hSymSrv = nullptr;
				m_pSymbolInfo = nullptr;
				MiniDumpWriteDump = nullptr;
				m_bFailedInitialize = false;
				m_bFailedInitializeDll = false;
				m_hProcess = INVALID_HANDLE_VALUE;
				m_Stopwatch.f_Start();
			}

			CStackTraceContext::~CStackTraceContext()
			{
				if (m_bInitialized)
					SymCleanup(m_hProcess);

				if (m_hProcess != INVALID_HANDLE_VALUE)
				{
					CloseHandle(m_hProcess);
				}

				if (m_pSymbolInfo)
					NMemory::CAllocator_NonTrackedHeap::f_Free(m_pSymbolInfo, gc_SymbolSize);

				if (m_hDbgHelp)
					FreeLibrary(m_hDbgHelp);
				if (m_hSymSrv)
					FreeLibrary(m_hSymSrv);

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
						#define DMibPlatformDir "\\x64"
					#else
						#define DMibPlatformDir "\\x86"
					#endif

					NStr::CStrNonTracked ProgramRoot = fg_GetSys()->f_GetProgramRootNonTracked();
					fg_StrReplaceChar(ProgramRoot, '/', '\\');

					NStr::CStrNonTracked ProgramPath = NMib::NFile::CFile::fs_GetProgramDirectoryNonTracked();
					fg_StrReplaceChar(ProgramPath, '/', '\\');

					if (!m_hDbgHelp)
					{
						NStr::CStrNonTracked DebugHelpDLL = "\\DebugHelp" DMibPlatformDir "\\Dbghelp.dll";

						m_hDbgHelp = (HMODULE)NSys::fg_LoadLibrary(ProgramRoot + DebugHelpDLL);

						if (!m_hDbgHelp)
							m_hDbgHelp = (HMODULE)NSys::fg_LoadLibrary(ProgramPath + DebugHelpDLL);

						if (!m_hDbgHelp)
							m_hDbgHelp = (HMODULE)NSys::fg_LoadLibrary(NStr::CStrNonTracked("Dbghelp.dll"));
					}

					// Apperantly some bug in Dbghelp.dll causes symsrv.dll to be unloaded while other modules are still holding a handle to it. Try to prevent this here by adding a reference to the library.
					if (!m_hSymSrv)
					{
						NStr::CStrNonTracked SymServDLL = "\\DebugHelp" DMibPlatformDir "\\SymSrv.dll";

						m_hSymSrv = (HMODULE)NSys::fg_LoadLibrary(ProgramRoot + SymServDLL);

						if (!m_hSymSrv)
							m_hSymSrv = (HMODULE)NSys::fg_LoadLibrary(ProgramPath + SymServDLL);

						if (!m_hSymSrv)
							m_hSymSrv = (HMODULE)NSys::fg_LoadLibrary(NStr::CStrNonTracked("SymSrv.dll"));
					}

					#undef DMibPlatformDir

					if (!m_hDbgHelp)
					{
						m_bFailedInitializeDll = true;
						_Error = "Dbghelp.dll not found";
						DMibDTrace("StackTrace: Failed to load DbgHelp.dll\n", 0);

						return false;
					}

					this->SymInitialize = (FSymInitialize*)GetProcAddress(m_hDbgHelp, "SymInitializeW");
					this->SymCleanup = (FSymCleanup*)GetProcAddress(m_hDbgHelp, "SymCleanup");
					this->SymRefreshModuleList = (FSymRefreshModuleList*)GetProcAddress(m_hDbgHelp, "SymRefreshModuleList");
					this->SymGetSymFromAddr64 = (FSymGetSymFromAddr64*)GetProcAddress(m_hDbgHelp, "SymGetSymFromAddr64");
					this->SymGetLineFromAddr64 = (FSymGetLineFromAddr64*)GetProcAddress(m_hDbgHelp, "SymGetLineFromAddr64");
					this->SymGetModuleInfo64 = (FSymGetModuleInfo64*)GetProcAddress(m_hDbgHelp, "SymGetModuleInfo64");
					this->MiniDumpWriteDump = (FMiniDumpWriteDump*)GetProcAddress(m_hDbgHelp, "MiniDumpWriteDump");
					this->UnDecorateSymbolName = (FUnDecorateSymbolName*)GetProcAddress(m_hDbgHelp, "UnDecorateSymbolName");


					if (!this->SymInitialize || !this->SymCleanup || !this->SymGetSymFromAddr64 || !this->SymGetLineFromAddr64 || !this->SymGetModuleInfo64 || !this->MiniDumpWriteDump || !this->SymRefreshModuleList)
					{
						m_bFailedInitializeDll = true;
						FreeLibrary(m_hDbgHelp);
						m_hDbgHelp = nullptr;
						_Error = "Dbghelp.dll dose not contain !SymInitialize || !SymCleanup || !SymGetSymFromAddr64 || !SymGetLineFromAddr64 || !SymGetModuleInfo64 || !MiniDumpWriteDump";
						DMibDTrace("---------------------------------------------------------------------------------------------------------------------\n", 0);
						for (int i = 0; i < 25; ++i)
						{
							DMibDTrace("StackTrace: DbgHelp.dll does not contain the needed functions\n", 0);

						}
						DMibDTrace("---------------------------------------------------------------------------------------------------------------------\n", 0);
						return false;
					}
					return true;
				};

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

					m_hProcess = OpenProcess(PROCESS_ALL_ACCESS, false, GetCurrentProcessId());
					if (m_hProcess == INVALID_HANDLE_VALUE)
					{
						DMibDTrace("StackTrace: SymInitialize failed\n", 0);
						_Error = "Could not open process handle";
						m_bFailedInitialize = true;
						return false;
					}

					if (!g_MalterlibDisableStackTraceContext)
					{
						if (!this->SymInitialize(m_hProcess, (ch16 *)Strings.f_GetStr(), false))
						{
							if (!this->SymInitialize(m_hProcess, nullptr, false))
							{
								_Error = NStr::CStrNonTracked::CFormat("SymInitialize failed with {}") << NMib::NPlatform::fg_Win32_GetLastErrorStr(GetLastError());
								DMibDTraceSafe("{}\n", _Error);
								m_bFailedInitialize = true;
								return false;
							}
						}

						if (!m_pSymbolInfo)
						{
							m_pSymbolInfo = (IMAGEHLP_SYMBOL64 *)NMemory::CAllocator_NonTrackedHeap::f_Alloc(gc_SymbolSize);
						}

						this->SymRefreshModuleList(m_hProcess);
					}
					return true;
				};

				bool bReturn = InitLambda();

				if (!bReturn)
					return false;

				m_bInitialized = true;
				return true;
			}


			void CStackTraceContext::f_UndecorateName(const ch8 *_pName, NStr::CStr &_Destination)
			{
				NStr::CStr Dest;
				f_UndecorateName(_pName, Dest.f_GetStr(4096), 4096);
				Dest.f_SetModified();
				_Destination = Dest;
			}

			void CStackTraceContext::f_UndecorateName(const ch8 *_pName, NStr::CStrNonTracked &_Destination)
			{
				NStr::CStrNonTracked Dest;
				f_UndecorateName(_pName, Dest.f_GetStr(4096), 4096);
				Dest.f_SetModified();
				_Destination = Dest;
			}

			void CStackTraceContext::f_UndecorateName(const ch8 *_pName, ch8 *_pDestination, mint _MaxLen)
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
				if (!UnDecorateSymbolName)
				{
					*_pDestination = 0;
					return;
				}
				uint32 Flags = 0;
		#ifndef DArchitecture_x64
				Flags |= UNDNAME_32_BIT_DECODE;
		#endif
				mint nChars = UnDecorateSymbolName(_pName, _pDestination, _MaxLen, Flags);
				if (!nChars)
				{
					[[maybe_unused]] HRESULT LastError = GetLastError();
					DMibDTraceSafe("UnDecorateSymbolName: {}\r\n", NMib::NPlatform::fg_Win32_GetLastErrorStr(LastError));
				}
			}

			CStackTraceContext::CLocalStackTraceInfo *CStackTraceContext::f_AquireStackTraceInfo(mint _Address)
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
					{
						pLocalInfo->m_UnusedList.f_Unlink();
					}
					return pLocalInfo;
				}

				DWORD64 Displacement;
				m_pSymbolInfo->SizeOfStruct = sizeof(IMAGEHLP_SYMBOL64);
				m_pSymbolInfo->MaxNameLength = 4096;
				if (!SymGetSymFromAddr64(m_hProcess, _Address, &Displacement, m_pSymbolInfo))
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
					if (SymGetLineFromAddr64(m_hProcess, _Address, &Displacement, &LineInfo))
					{
						const ch8 *pName = LineInfo.FileName;
						constexpr static const ch8 *c_pCrtStrip[] =
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
					if (SymGetModuleInfo64(m_hProcess, _Address, &ModuleInfo))
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
