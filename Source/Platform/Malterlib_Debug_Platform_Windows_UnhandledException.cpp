// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include <Mib/Debug/Debug>
#include <Mib/Core/PlatformSpecific/WindowsFilePath>
#include <Mib/Core/PlatformSpecific/WindowsError>
#include <Mib/Core/PlatformSpecific/WindowsUndocumented>
#include <Mib/Core/PlatformSpecific/Windows>
#include "Malterlib_Debug_Platform_Windows.h"

#include <Windows.h>
#include <winnt.h>
#include <Psapi.h>

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			static bool fg_DefaultCrashDumpUserNotify
				(
					NMib::NStr::CStrNonTracked const &_CustomMessage,
					NMib::NStr::CStrNonTracked const &_ProgramName,
					NMib::NStr::CStrNonTracked const &_SupportEmail,
					NMib::NStr::CStrNonTracked const &_FileName,
					NMib::NStr::CStrNonTracked const &_FileNameDumpMini,
					NMib::NStr::CStrNonTracked const &_FileNameDump,
					bool _bAllowContinue
				)
			;
			NStr::CStr CSubSystem_Debug_Platform_Windows::fs_FixLineEndings(NStr::CStr const &_In)
			{
				const ch8 *pParse = _In;
				NStr::CStr Ret;
				while (*pParse)
				{
					if (*pParse == '\n')
					{
						Ret.f_AddStr("\r\n");
						++pParse;
						continue;
					}
					else if (*pParse == '\r')
					{
						Ret.f_AddStr("\r\n");
						++pParse;
						if (*pParse == '\n')
							++pParse;
						continue;
					}
					else
						Ret.f_AddChar(*pParse);

					++pParse;
				}
				return Ret;
			}

			NStr::CStrNonTracked CSubSystem_Debug_Platform_Windows::f_DumpObjects()
			{
				typedef BOOL (WINAPI fEnumProcesses)(DWORD * lpidProcess, DWORD   cb, DWORD * cbNeeded);
				typedef DWORD (WINAPI fGetModuleBaseNameW)(HANDLE hProcess, HMODULE hModule, LPWSTR lpBaseName, DWORD nSize);
				typedef DWORD (WINAPI fGetModuleFileNameExW)(HANDLE hProcess, HMODULE hModule, LPWSTR lpFilename, DWORD nSize);
				typedef DWORD (WINAPI fGetProcessImageFileNameW)(HANDLE hProcess, LPWSTR lpImageFileName, DWORD nSize);


				HMODULE hPSAPI = LoadLibrary(str_utf16("psapi.dll"));
				if (hPSAPI)
				{
					fEnumProcesses *pEnumProcesses = (fEnumProcesses *)GetProcAddress(hPSAPI, "EnumProcesses");
					fGetModuleBaseNameW *pGetModuleBaseName = (fGetModuleBaseNameW *)GetProcAddress(hPSAPI, "GetModuleBaseNameW");
					fGetModuleFileNameExW *pGetModuleFileNameEx = (fGetModuleFileNameExW *)GetProcAddress(hPSAPI, "GetModuleFileNameExW");
					fGetProcessImageFileNameW *pGetProcessImageFileName = (fGetProcessImageFileNameW *)GetProcAddress(hPSAPI, "GetProcessImageFileNameW");
			
					if (pEnumProcesses)
					{
						NStr::CStrNonTracked Ret = "\r\n\r\nDump of GDI and User Objects\r\n\r\n";
						const ch8 * pFormatStr = "{sj128,a-}{sj18,a-}{sj18,a-}\r\n";
						Ret += NStr::CStrNonTracked::CFormat(pFormatStr) << "Process" << "GDI Objects" << "User Objects";
						NContainer::TCVector<DWORD, NMemory::CAllocator_NonTrackedHeap> ProcessIDs;

						ProcessIDs.f_SetLen(65536);

						uint32 nTotalGDI = 0;
						uint32 nTotalUser = 0;

						DWORD nEnum;
						if (pEnumProcesses(ProcessIDs.f_GetArray(), 65536, &nEnum))
						{
							for (mint i = 0; i < nEnum; ++i)
							{
								HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, false, ProcessIDs[i]);
								if (hProcess)
								{
									uint32 nGDI = GetGuiResources(hProcess, GR_GDIOBJECTS);
									uint32 nUser = GetGuiResources(hProcess, GR_USEROBJECTS);

									nTotalGDI += nGDI;
									nTotalUser += nUser;

									NStr::CWStrNonTracked BaseName;
		#if 1
									if (pGetProcessImageFileName)
										pGetProcessImageFileName(hProcess, BaseName.f_GetStr(1024), 1024);
									else 
		#endif
										if (pGetModuleFileNameEx)
										pGetModuleFileNameEx(hProcess, nullptr, BaseName.f_GetStr(1024), 1024);
									else if (pGetModuleBaseName)
										pGetModuleBaseName(hProcess, nullptr, BaseName.f_GetStr(1024), 1024);

									Ret += NStr::CStrNonTracked::CFormat(pFormatStr) << BaseName << nGDI << nUser;

									CloseHandle(hProcess);
								}
							}
						}
						FreeLibrary(hPSAPI);
						Ret += "\r\n";
						Ret += NStr::CStrNonTracked::CFormat(pFormatStr) << "Total" << nTotalGDI << nTotalUser;
						Ret += "\r\n";
						return Ret;
					}
					FreeLibrary(hPSAPI);
				}

				return "";
			}

			NStr::CStrNonTracked CSubSystem_Debug_Platform_Windows::f_DumpModules()
			{
				HANDLE hProcess = GetCurrentProcess();
				NContainer::TCVector<HMODULE, NMemory::CAllocator_NonTrackedHeap> Modules;
				Modules;
				DWORD NeededBytes = 0;
				EnumProcessModules(hProcess, 0, 0, &NeededBytes);
				Modules.f_SetLen((NeededBytes * 2) / sizeof(HMODULE));
				NStr::CStrNonTracked Ret = "\r\n\r\nDump of Process modules\r\n\r\n";
				const ch8 * pFormatStr = "{sj128,a-}{sj19,a-}{sj19,a-}{sj19,a-}\r\n";
				Ret += NStr::CStrNonTracked::CFormat(pFormatStr) << "Module" << "Start" << "End" << "Size";
				if (EnumProcessModules(hProcess, Modules.f_GetArray(), Modules.f_GetLen() * sizeof(HMODULE), &NeededBytes))
				{
					mint nModules = NeededBytes / sizeof(HMODULE);
					for (mint i = 0; i < nModules; ++i)
					{
						HMODULE hModule = Modules[i];
						NStr::CWStrNonTracked ModuleName;
						if (GetModuleFileNameEx(hProcess, hModule, ModuleName.f_GetStr(1024), 1024))
						{
							ModuleName.f_SetModified();
						}
						else
							ModuleName.f_Clear();

						MODULEINFO ModuleInfo;

						if (GetModuleInformation(hProcess, hModule, &ModuleInfo, sizeof(ModuleInfo)))
						{
							Ret 
								+= NStr::CStrNonTracked::CFormat(pFormatStr) 
								<< ModuleName 
								<< NStr::CFStr64(NStr::CFStr64::CFormat("0x{}") << ModuleInfo.lpBaseOfDll)
								<< NStr::CFStr64(NStr::CFStr64::CFormat("0x{}") << (void *)((mint)ModuleInfo.lpBaseOfDll + ModuleInfo.SizeOfImage))
								<< NStr::CFStr64(NStr::CFStr64::CFormat("{}") << ModuleInfo.SizeOfImage)
							;
						}
					}
				}

				Ret += "\r\n";
				return Ret;
			}


			LONG WINAPI CSubSystem_Debug_Platform_Windows::fsp_DumpExceptionInformation
				(
					struct _EXCEPTION_POINTERS *_pExceptionInfo
					, const NStr::CStr &_Message
					, const NStr::CStr &_ExtraLog
					, NContainer::TCVector<NMib::NStr::CStr> *_pGeneratedLogs
					, bint _bDisplayGUI
				)
			{
				DMibDeadlockDetectorPause;

				auto &SubSystem = fg_Debug_Platfrom_Windows();
				DMibLock(SubSystem.m_DumpExceptionInfoLock);

				auto fl_GenerateException
					= [&_Message, &_ExtraLog, _pExceptionInfo, _pGeneratedLogs, _bDisplayGUI] (NThread::CThreadObjectNonTracked *_pThread) -> aint
					{
						mint nCache = EWindowCache;
						auto &SubSystem = fg_Debug_Platfrom_Windows();

						NStr::CStrNonTracked CrashDumpPath = NFile::NPlatform::fg_ConvertFromWindowsPath<NStr::CWStrNonTracked, NStr::CWStrNonTracked>(NSys::fg_Process_GetEnvironmentVariable_NonProtected(NStr::CStrNonTracked("MalterlibCrashDumpDir")));
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

						NStr::CStrNonTracked FileName;
						NStr::CStrNonTracked FileNameDumpMini;
						NStr::CStrNonTracked FileNameDump;

						{
							NTime::CTimeConvert::CDateTime DateTime;
							NTime::CTimeConvert(NTime::CTime::fs_NowLocal()).f_ExtractDateTime(DateTime);

							int32 Fraction = (DateTime.m_Fraction*1000.0).f_ToIntRound();
							if (Fraction >= 1000)
								Fraction = 999;

							uint32 RandomValue = SubSystem.f_GetRandom();

							FileName = CrashDumpPath + (NStr::CStrNonTracked::CFormat("/CrashLog_{}-{sj2,sf0}-{sj2,sf0}_{sj2,sf0}.{sj2,sf0}.{sj2,sf0}.{sj3,sf0}.{sj8,sf0,nfh}.txt")
								<< DateTime.m_Year << DateTime.m_Month << DateTime.m_DayOfMonth << DateTime.m_Hour << DateTime.m_Minute << DateTime.m_Second << Fraction << RandomValue).f_GetStr();
							FileNameDump = CrashDumpPath + (NStr::CStrNonTracked::CFormat("/FullDump_{}-{sj2,sf0}-{sj2,sf0}_{sj2,sf0}.{sj2,sf0}.{sj2,sf0}.{sj3,sf0}.{sj8,sf0,nfh}.dmp")
								<< DateTime.m_Year << DateTime.m_Month << DateTime.m_DayOfMonth << DateTime.m_Hour << DateTime.m_Minute << DateTime.m_Second << Fraction << RandomValue).f_GetStr();
							FileNameDumpMini = CrashDumpPath + (NStr::CStrNonTracked::CFormat("/MiniDump_{}-{sj2,sf0}-{sj2,sf0}_{sj2,sf0}.{sj2,sf0}.{sj2,sf0}.{sj3,sf0}.{sj8,sf0,nfh}.dmp")
								<< DateTime.m_Year << DateTime.m_Month << DateTime.m_DayOfMonth << DateTime.m_Hour << DateTime.m_Minute << DateTime.m_Second << Fraction << RandomValue).f_GetStr();
						}
						// Mini dump
						NStr::CStrNonTracked ExceptionInfo;
						if (!_Message.f_IsEmpty())
						{
							ExceptionInfo += "\r\n";
							ExceptionInfo += _Message;
							ExceptionInfo += "\r\n\r\n";
						}
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
									{
										NFile::CFile File;
										File.f_Open(FileNameDumpMini, NFile::EFileOpen_Write);
										if (File.f_IsValid())
										{
											MINIDUMP_TYPE DumpType = (MINIDUMP_TYPE )(MiniDumpWithHandleData | MiniDumpWithIndirectlyReferencedMemory | MiniDumpWithProcessThreadData);
											if (!SubSystem.m_StackTrace.MiniDumpWriteDump(SubSystem.m_StackTrace.m_hProcess, GetCurrentProcessId(), File.f_GetOSFile(), DumpType, &Info, nullptr, nullptr))
											{
												NStr::CFStr256 ErrorStr = NStr::CFStr256::CFormat("Could not write mini dump. The error was: {}") << NMib::NPlatform::fg_Win32_GetLastErrorStr(GetLastError());
												DMibDTrace("{}\n", ErrorStr);
												ExceptionInfo += ErrorStr + "\r\n\r\n";
												FileNameDumpMini.f_Clear();
											}
											else if (_pGeneratedLogs)
												_pGeneratedLogs->f_Insert(FileNameDumpMini);
										}
									}
									{
										NFile::CFile File;
										File.f_Open(FileNameDump, NFile::EFileOpen_Write);
										if (File.f_IsValid())
										{
											MINIDUMP_TYPE DumpType = (MINIDUMP_TYPE)(MiniDumpWithDataSegs | MiniDumpWithFullMemory | MiniDumpWithHandleData | MiniDumpWithUnloadedModules
												| MiniDumpWithIndirectlyReferencedMemory | MiniDumpWithProcessThreadData | MiniDumpWithPrivateReadWriteMemory);

											if (!SubSystem.m_StackTrace.MiniDumpWriteDump(SubSystem.m_StackTrace.m_hProcess, GetCurrentProcessId(), File.f_GetOSFile(), DumpType, &Info, nullptr, nullptr))
											{
												NStr::CFStr256 ErrorStr = NStr::CFStr256::CFormat("Could not write full dump. The error was: {}") << NMib::NPlatform::fg_Win32_GetLastErrorStr(GetLastError());
												DMibDTrace("{}\n", ErrorStr);
												ExceptionInfo += ErrorStr + "\r\n\r\n";
												FileNameDump.f_Clear();
											}
											else if (_pGeneratedLogs)
												_pGeneratedLogs->f_Insert(FileNameDump);
										}
									}
								}
							}
							else
							{
								NStr::CFStr256 ErrorStr = NStr::CFStr256::CFormat("Could not initialize debug help context. The error was: {}") << StackTraceError;
								DMibDTrace("{}\n", ErrorStr);
								ExceptionInfo += ErrorStr + "\r\n\r\n";
				
							}
						} 

						ExceptionInfo += "Unhandled exception\r\n\r\n";

						// 
						// Type
						//
						NStr::CStrNonTracked Code;
						switch (_pExceptionInfo->ExceptionRecord->ExceptionCode)
						{		
						case EXCEPTION_ACCESS_VIOLATION:
							{
								if (_pExceptionInfo->ExceptionRecord->ExceptionInformation[0])
									Code = NStr::CStrNonTracked::CFormat("Access violation trying to write to address: 0x{nfh,sf0,sj*}") << 
									((mint)_pExceptionInfo->ExceptionRecord->ExceptionInformation[1]) << (sizeof(mint) * 2)
									;
								else
									Code = NStr::CStrNonTracked::CFormat("Access violation trying to read to address: 0x{nfh,sf0,sj*}") <<
									((mint)_pExceptionInfo->ExceptionRecord->ExceptionInformation[1]) << (sizeof(mint) * 2)
									;

							}
							break;
						case EXCEPTION_ARRAY_BOUNDS_EXCEEDED: Code = "Array bounds exceeded";break;
						case EXCEPTION_BREAKPOINT: Code = "Breakpoint";break;
						case EXCEPTION_DATATYPE_MISALIGNMENT: Code = "Datatype misalignment";break;
						case EXCEPTION_FLT_DENORMAL_OPERAND: Code = "Float denormal operand";break;
						case EXCEPTION_FLT_DIVIDE_BY_ZERO: Code = "Float divide by zero";break;
						case EXCEPTION_FLT_INEXACT_RESULT: Code = "Float inexact result";break;
						case EXCEPTION_FLT_INVALID_OPERATION: Code = "Float invalid operation";break;
						case EXCEPTION_FLT_OVERFLOW: Code = "Float overflow";break;
						case EXCEPTION_FLT_STACK_CHECK: Code = "Float stack check";break;
						case EXCEPTION_FLT_UNDERFLOW: Code = "Float underflow";break;
						case EXCEPTION_ILLEGAL_INSTRUCTION: Code = "Illegal instruction";break;
						case EXCEPTION_IN_PAGE_ERROR: Code = "In page error";break;
						case EXCEPTION_INT_DIVIDE_BY_ZERO: Code = "Integer divide by zero";break;
						case EXCEPTION_INT_OVERFLOW: Code = "Integer overflow";break;
						case EXCEPTION_INVALID_DISPOSITION: Code = "Invalid disposition";break;
						case EXCEPTION_NONCONTINUABLE_EXCEPTION: Code = "Noncontinuable exception";break;
						case EXCEPTION_PRIV_INSTRUCTION: Code = "Priviledged instruction";break;
						case EXCEPTION_SINGLE_STEP: Code = "Single step";break;
						case EXCEPTION_STACK_OVERFLOW: Code = "Stack overflow";break;
						default:
							{
								if (_pExceptionInfo->ExceptionRecord && _pExceptionInfo->ExceptionRecord->NumberParameters >= 3 && _pExceptionInfo->ExceptionRecord->ExceptionInformation[0] == 0x19930520)
								{
									NException::CException *pException = (NException::CException *)_pExceptionInfo->ExceptionRecord->ExceptionInformation[1];
									if (pException->f_IsValid())
									{
										Code = NStr::CStrNonTracked::CFormat("{} in {}\r\n" DMibPFileLineFormat " {}") << pException->f_GetClass() << pException->f_GetFunction() << pException->f_GetFile() << pException->f_GetLine() << pException->f_GetErrorStrNonTracked();
									}
								}
						
							}
						}

						if (Code.f_IsEmpty())
							Code = NStr::CStrNonTracked::CFormat("Unknown ({nfh,sf0,sj8})") << _pExceptionInfo->ExceptionRecord->ExceptionCode;

						ExceptionInfo += "Exception type: " + Code + "\r\n\r\n";

						#if defined(DMibContract_AnyEnabled) || DMibEnableSafeCheck > 0
							NStr::CStrNonTracked LastContract = NSys::fg_System_GetContractViolationMessage();;
							if (!LastContract.f_IsEmpty())
							{
								ExceptionInfo += "Last contract violation: \r\n";
								ExceptionInfo += LastContract;
								ExceptionInfo += "\r\n\r\n";
							}
						#endif


						bool bCanContinue = !(_pExceptionInfo->ExceptionRecord->ExceptionFlags & EXCEPTION_NONCONTINUABLE) && _pExceptionInfo->ExceptionRecord->ExceptionCode == EXCEPTION_BREAKPOINT;
				//		if (!bCanContinue)
				//			ExceptionInfo += "Exception is noncontinuable\r\n";

						//
						// Exception address
						//
						CStackTraceInfo *pAddressInfo = _pThread ? SubSystem.f_AquireStackTraceInfo((CMibCodeAddress)_pExceptionInfo->ExceptionRecord->ExceptionAddress) : nullptr;

						if (pAddressInfo)
						{
							ExceptionInfo += NStr::CStrNonTracked::CFormat("Exception address: 0x{nfh,sf0,sj*} ({}!{})\r\n\r\n") << ((mint)_pExceptionInfo->ExceptionRecord->ExceptionAddress) << (sizeof(mint) * 2)
									<< (pAddressInfo->m_pModuleName) << (pAddressInfo->m_pFunctionName);
							SubSystem.f_ReleaseStackTraceInfo(pAddressInfo);
						}
						else
						{
							ExceptionInfo += NStr::CStrNonTracked::CFormat("Exception address: 0x{nfh,sf0,sj*1}\r\n\r\n") << ((mint)_pExceptionInfo->ExceptionRecord->ExceptionAddress) << (sizeof(mint) * 2);
						}		

						//
						// Register information
						//
						if (_pExceptionInfo->ContextRecord->ContextFlags & CONTEXT_INTEGER)
						{
				#ifdef DArchitecture_x64
							ExceptionInfo += NStr::CStrNonTracked::CFormat("Integer registers:\r\n"
								"rdi=0x{} rsi=0x{} rax=0x{}\r\n"
								"rbx=0x{} rcx=0x{} rdx=0x{}\r\n"
								"r8=0x{}  r9=0x{}  r10=0x{}\r\n"
								"r11=0x{} r12=0x{} r13=0x{}\r\n"
								"r14=0x{} r15=0x{}\r\n"
								"\r\n")
								<< ((void *)_pExceptionInfo->ContextRecord->Rdi)
								<< ((void *)_pExceptionInfo->ContextRecord->Rsi)
								<< ((void *)_pExceptionInfo->ContextRecord->Rax)
								<< ((void *)_pExceptionInfo->ContextRecord->Rbx)
								<< ((void *)_pExceptionInfo->ContextRecord->Rcx)
								<< ((void *)_pExceptionInfo->ContextRecord->Rdx)
								<< ((void *)_pExceptionInfo->ContextRecord->R8)
								<< ((void *)_pExceptionInfo->ContextRecord->R9)
								<< ((void *)_pExceptionInfo->ContextRecord->R10)
								<< ((void *)_pExceptionInfo->ContextRecord->R11)
								<< ((void *)_pExceptionInfo->ContextRecord->R12)
								<< ((void *)_pExceptionInfo->ContextRecord->R13)
								<< ((void *)_pExceptionInfo->ContextRecord->R14)
								<< ((void *)_pExceptionInfo->ContextRecord->R15)
								;
				#else
							ExceptionInfo += NStr::CStrNonTracked::CFormat("Integer registers:\r\n"
								"edi=0x{} esi=0x{} eax=0x{}\r\n"
								"ebx=0x{} ecx=0x{} edx=0x{}\r\n\r\n")
								<< ((void *)_pExceptionInfo->ContextRecord->Edi)
								<< ((void *)_pExceptionInfo->ContextRecord->Esi)
								<< ((void *)_pExceptionInfo->ContextRecord->Eax)
								<< ((void *)_pExceptionInfo->ContextRecord->Ebx)
								<< ((void *)_pExceptionInfo->ContextRecord->Ecx)
								<< ((void *)_pExceptionInfo->ContextRecord->Edx)
								;
				#endif
						}
						if (_pExceptionInfo->ContextRecord->ContextFlags & CONTEXT_CONTROL)
						{
				#ifdef DArchitecture_x64
							ExceptionInfo 
								+= NStr::CStrNonTracked::CFormat("Control registers:\r\n"
								"rip=0x{} rbp=0x{} rsp=0x{}\r\n"
								"SegCs=0x{nfh,sj4,sf0} SegDs=0x{nfh,sj4,sf0}\r\n"
								"SegEs=0x{nfh,sj4,sf0} SegFs=0x{nfh,sj4,sf0}\r\n"
								"SegGs=0x{nfh,sj4,sf0} SegSs=0x{nfh,sj4,sf0}\r\n"
								"EFlags=0x{nfh,sj8,sf0}\r\n\r\n")
								<< ((void *)_pExceptionInfo->ContextRecord->Rip)
								<< ((void *)_pExceptionInfo->ContextRecord->Rbp)
								<< ((void *)_pExceptionInfo->ContextRecord->Rsp)
								<< ((uint16)_pExceptionInfo->ContextRecord->SegCs)
								<< ((uint16)_pExceptionInfo->ContextRecord->SegDs)
								<< ((uint16)_pExceptionInfo->ContextRecord->SegEs)
								<< ((uint16)_pExceptionInfo->ContextRecord->SegFs)
								<< ((uint16)_pExceptionInfo->ContextRecord->SegGs)
								<< ((uint16)_pExceptionInfo->ContextRecord->SegSs)
								<< ((uint32)_pExceptionInfo->ContextRecord->EFlags)
							;
				#else
							ExceptionInfo += NStr::CStrNonTracked::CFormat("Control registers:\r\n"
								"eip=0x{} ebp=0x{} esp=0x{}\r\n"
								"SegCs=0x{nfh,sj8,sf0} SegSs=0x{nfh,sj8,sf0} EFlags=0x{nfh,sj8,sf0}\r\n\r\n")
								<< ((void *)_pExceptionInfo->ContextRecord->Eip)
								<< ((void *)_pExceptionInfo->ContextRecord->Ebp)
								<< ((void *)_pExceptionInfo->ContextRecord->Esp)
								<< ((uint32)_pExceptionInfo->ContextRecord->SegCs)
								<< ((uint32)_pExceptionInfo->ContextRecord->SegSs)
								<< ((uint32)_pExceptionInfo->ContextRecord->EFlags)
								;
				#endif
						}

						if (_pExceptionInfo->ContextRecord->ContextFlags & CONTEXT_DEBUG_REGISTERS)
						{
							ExceptionInfo += NStr::CStrNonTracked::CFormat("Debug registers:\r\n"
								"Dr0=0x{} Dr1=0x{} Dr2=0x{}\r\n"
								"Dr3=0x{} Dr6=0x{} Dr7=0x{}\r\n\r\n")
								<< ((mint)_pExceptionInfo->ContextRecord->Dr0)
								<< ((mint)_pExceptionInfo->ContextRecord->Dr1)
								<< ((mint)_pExceptionInfo->ContextRecord->Dr2)
								<< ((mint)_pExceptionInfo->ContextRecord->Dr3)
								<< ((mint)_pExceptionInfo->ContextRecord->Dr6)
								<< ((mint)_pExceptionInfo->ContextRecord->Dr7)
								;
						}

				#ifndef DArchitecture_x64
						if (_pExceptionInfo->ContextRecord->ContextFlags & CONTEXT_SEGMENTS)
						{
							ExceptionInfo += NStr::CStrNonTracked::CFormat("Segment registers:\r\n"
								"SegGs=0x{} SegFs=0x{}\r\n"
								"SegEs=0x{} SegDs=0x{}\r\n\r\n")
								<< ((mint)_pExceptionInfo->ContextRecord->SegGs)
								<< ((mint)_pExceptionInfo->ContextRecord->SegFs)
								<< ((mint)_pExceptionInfo->ContextRecord->SegEs)
								<< ((mint)_pExceptionInfo->ContextRecord->SegDs)
								;
						}

						if (_pExceptionInfo->ContextRecord->ContextFlags & CONTEXT_FLOATING_POINT)
						{
							FLOATING_SAVE_AREA &FloatSaveArea = _pExceptionInfo->ContextRecord->FloatSave;

							ExceptionInfo += NStr::CStrNonTracked::CFormat("Floating point registers:\r\n"
								"ControlWord=0x{nfh,sf0,sj4} StatusWord=0x{nfh,sf0,sj4} TagWord=0x{nfh,sf0,sj4}\r\n"
								"ErrorOffset=0x{} ErrorSelector=0x{} DataOffset=0x{}\r\n"
								"DataSelector=0x{} \r\n")
								<< ((uint16)FloatSaveArea.ControlWord&0xffff)
								<< ((uint16)FloatSaveArea.StatusWord&0xffff)
								<< ((uint64)FloatSaveArea.TagWord&0xffff)
								<< ((mint)FloatSaveArea.ErrorOffset)
								<< ((mint)FloatSaveArea.ErrorSelector)
								<< ((mint)FloatSaveArea.DataOffset)
								<< ((mint)FloatSaveArea.DataSelector)
								;

							ExceptionInfo += NStr::CStrNonTracked::CFormat(
								"St0=0x{nfh,sf0,sj4}{nfh,sf0,sj16} St1=0x{nfh,sf0,sj4}{nfh,sf0,sj16}\r\n"
								"St2=0x{nfh,sf0,sj4}{nfh,sf0,sj16} St3=0x{nfh,sf0,sj4}{nfh,sf0,sj16}\r\n"
								"St4=0x{nfh,sf0,sj4}{nfh,sf0,sj16} St5=0x{nfh,sf0,sj4}{nfh,sf0,sj16}\r\n"
								"St6=0x{nfh,sf0,sj4}{nfh,sf0,sj16} St7=0x{nfh,sf0,sj4}{nfh,sf0,sj16}\r\n\r\n")
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[0*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[0*10]))
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[1*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[1*10]))
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[2*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[2*10]))
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[3*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[3*10]))
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[4*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[4*10]))
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[5*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[5*10]))
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[6*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[6*10]))
								<< (*((uint16 *)&FloatSaveArea.RegisterArea[7*10+8]))
								<< (*((uint64 *)&FloatSaveArea.RegisterArea[7*10]))
								;
						}
				#endif

				#ifndef DArchitecture_x64
						if (_pExceptionInfo->ContextRecord->ContextFlags & CONTEXT_EXTENDED_REGISTERS)
						{
							ExceptionInfo += NStr::CStrNonTracked::CFormat("SSE registers:\r\n"
								"MXCSR=0x{}\r\n"
								"Xmm0=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm1=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
								"Xmm2=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm3=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
								"Xmm4=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm5=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
								"Xmm6=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm7=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n\r\n")
								<< (*((uint32 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[24]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[10*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[10*16]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[11*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[11*16]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[12*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[12*16]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[13*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[13*16]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[14*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[14*16]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[15*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[15*16]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[16*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[16*16]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[17*16+8]))
								<< (*((uint64 *)&_pExceptionInfo->ContextRecord->ExtendedRegisters[17*16]))
								;
						}
				#else
						if (_pExceptionInfo->ContextRecord->ContextFlags & CONTEXT_FLOATING_POINT)
						{
							ExceptionInfo 
								+= NStr::CStrNonTracked::CFormat
								(
									"Floating point registers:\r\n"
									"MXCSR=0x{}\r\n"
									"Xmm0=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm1=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Xmm2=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm3=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Xmm4=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm5=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Xmm6=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm7=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Xmm8=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm9=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Xmm10=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm11=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Xmm12=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm13=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Xmm14=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Xmm15=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"\r\n"
									"Vector registers:\r\n"
									"Vec0=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec1=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec2=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec3=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec4=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec5=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec6=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec7=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec8=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec9=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec10=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec11=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec12=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec13=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec14=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec15=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec16=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec17=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec18=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec19=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec20=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec21=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec22=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec23=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"Vec24=0x{nfh,sf0,sj16}{nfh,sf0,sj16} Vec25=0x{nfh,sf0,sj16}{nfh,sf0,sj16}\r\n"
									"\r\n"
								)
								<< (void *)(mint)_pExceptionInfo->ContextRecord->FltSave.MxCsr
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[0].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[0].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[1].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[1].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[2].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[2].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[3].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[3].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[4].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[4].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[5].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[5].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[6].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[6].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[7].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[7].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[8].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[8].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[9].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[9].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[10].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[10].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[11].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[11].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[12].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[12].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[13].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[13].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[14].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[14].Low
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[15].High
								<< _pExceptionInfo->ContextRecord->FltSave.XmmRegisters[15].Low

								<< _pExceptionInfo->ContextRecord->VectorRegister[0].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[0].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[1].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[1].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[2].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[2].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[3].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[3].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[4].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[4].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[5].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[5].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[6].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[6].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[7].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[7].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[8].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[8].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[9].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[9].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[10].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[10].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[11].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[11].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[12].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[12].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[13].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[13].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[14].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[14].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[15].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[15].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[16].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[16].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[17].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[17].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[18].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[18].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[19].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[19].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[20].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[20].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[21].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[21].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[22].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[22].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[23].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[23].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[24].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[24].Low
								<< _pExceptionInfo->ContextRecord->VectorRegister[25].High
								<< _pExceptionInfo->ContextRecord->VectorRegister[25].Low


							;
						}

				#endif

						//
						// Stack trace
						//
						{
							ExceptionInfo += "StackTrace: \r\n";
							int iMaxDepth = 1024;

							CUndocumentedTEB *pTEB = fg_GetTEB();
							mint StackStart = (mint)pTEB->Tib.StackBase;
							mint StackEnd = (mint)pTEB->Tib.StackLimit;


							try
							{
				#ifdef DArchitecture_x64
								mint StackFrame = _pExceptionInfo->ContextRecord->Rbp;
				#else
								mint StackFrame = _pExceptionInfo->ContextRecord->Ebp;
				#endif
								mint LastCode = (mint)_pExceptionInfo->ExceptionRecord->ExceptionAddress;
								while (iMaxDepth)
								{
									if (!NMib::NPlatform::fg_IsGoodStackPtr((void *)StackFrame, sizeof(mint) * 2, StackStart, StackEnd))
										break;
									mint CodePtr = *((mint *)(StackFrame + sizeof(mint)));

									CStackTraceInfo *pAddressInfo = _pThread ? SubSystem.f_AquireStackTraceInfo((CMibCodeAddress)LastCode) : nullptr;

									if (pAddressInfo)
									{
										ExceptionInfo += NStr::CStrNonTracked::CFormat("0x{nfh,sf0,sj*} {}!{}\r\n{}:{}\r\n") << (mint)LastCode << sizeof(mint) * 2
											<< pAddressInfo->m_pModuleName << pAddressInfo->m_pFunctionName
											<< pAddressInfo->m_pSourceFileName << pAddressInfo->m_SourceLine
											;
										SubSystem.f_ReleaseStackTraceInfo(pAddressInfo);
									}
									else
									{
										ExceptionInfo += NStr::CStrNonTracked::CFormat("0x{nfh,sf0,sj*1}\r\n") << (LastCode) << (sizeof(mint) * 2);
									}		
									ExceptionInfo += NStr::CStrNonTracked::CFormat("StackFrame: 0x{nfh,sf0,sj*1}\r\n") << (StackFrame) << (sizeof(mint) * 2);
									ExceptionInfo += "\r\n";

									LastCode = CodePtr;

									StackFrame = *((mint *)(StackFrame));
									--iMaxDepth;			
								}
							}
							catch(...)
							{
							}

							//
							// Stack
							//

							try
							{
				//				DMibDTrace("StackEnd {nfh,sj8,sf0} StackStart {nfh,sj8,sf0}", StackEnd << StackStart);
								NStr::CStrNonTracked Stack;
								int iRowSize = 32;
								int iRow = iRowSize;			
								Stack += NStr::CStrNonTracked::CFormat("0x{nfh,sf0,sj*1}: ") << (StackEnd) << (sizeof(mint) * 2);
								while (StackEnd < StackStart)
								{
									int iMax = fg_Min((int)StackStart - (int)StackEnd, iRow);
									if (iMax >= 8)
									{
										Stack += NStr::CStrNonTracked::CFormat("{nfh,sf0,sj16} ") << (fg_ByteSwap(*((uint64 *)StackEnd)));
										StackEnd += 8;
										iRow -= 8;
									}
									else if (iMax >= 4)
									{
										Stack += NStr::CStrNonTracked::CFormat("{nfh,sf0,sj8}") << (fg_ByteSwap(*((uint32 *)StackEnd)));
										StackEnd += 4;
										iRow -= 4;
									}
									else if (iMax >= 2)
									{
										Stack += NStr::CStrNonTracked::CFormat("{nfh,sf0,sj4}") << (fg_ByteSwap(*((uint16 *)StackEnd)));
										StackEnd += 2;
										iRow -= 2;
									}
									else if (iMax >= 1)
									{
										Stack += NStr::CStrNonTracked::CFormat("{nfh,sf0,sj2}") << (*((uint8 *)StackEnd));
										StackEnd += 1;
										iRow -= 1;
									}

									if (iRow <= 0)
									{
										iRow = iRowSize;
										Stack += "\r\n";
										Stack += NStr::CStrNonTracked::CFormat("0x{nfh,sf0,sj*1}: ") << (StackEnd) << (sizeof(mint) * 2);
									}
								}

								ExceptionInfo += Stack;
							}
							catch (...)
							{
							}
						}

						NStr::CStrNonTracked GDIDump = SubSystem.f_DumpObjects();

						ExceptionInfo += GDIDump;

						NStr::CStrNonTracked ModuleDump = SubSystem.f_DumpModules();

						ExceptionInfo += ModuleDump;

						if (!_ExtraLog.f_IsEmpty())
						{
							ExceptionInfo += fs_FixLineEndings(_ExtraLog);
						}

						{ 
							NFile::CFile::fs_WriteStringToFile(FileName, ExceptionInfo);
							if (_pGeneratedLogs)
								_pGeneratedLogs->f_Insert(FileName);
						}

						//
						// Message box
						//
						NStr::CStrNonTracked ProgramName = fg_GetSys()->f_GetProgramNameNonTracked();
						if (ProgramName.f_IsEmpty())
							ProgramName = "The program";

						NStr::CStrNonTracked ProgramNameCopy = ProgramName;
						ProgramName = NStr::CStrNonTracked::CFormat("{} ({})") << ProgramNameCopy << (mint)GetCurrentProcessId();
						NStr::CStrNonTracked SupportEmail = fg_GetSys()->f_GetSupportEmailNonTracked();
						if (SupportEmail.f_IsEmpty())
							SupportEmail = "unknown@example.com";
						bint bDaemon = fg_GetSys()->f_GetRunningAsDaemon();
		
						bint bContinue = (!_Message.f_IsEmpty() || _pGeneratedLogs != nullptr);
						if (!bDaemon)
						{
							for (mint i = 0; i < nCache; ++i)
							{
								if (SubSystem.m_CacheWindows[i])
								{
									DestroyWindow(SubSystem.m_CacheWindows[i]);
									SubSystem.m_CacheWindows[i] = nullptr;
								}
							}

							if (_bDisplayGUI)
							{

								if (SubSystem.m_pCrashDumpUserNotifyFunction && !NMib::NSys::fg_ConsoleErrorOutputValid())
								{
									bContinue = (*(SubSystem.m_pCrashDumpUserNotifyFunction))(_Message, ProgramName, SupportEmail, FileName, FileNameDumpMini, FileNameDump, bCanContinue);
								}
								else
								{
									bContinue = fg_DefaultCrashDumpUserNotify(_Message, ProgramName, SupportEmail, FileName, FileNameDumpMini, FileNameDump, bCanContinue);
								}
							}
						}

						if (bContinue)
						{
							if (!_pGeneratedLogs)
							{
					#ifdef DArchitecture_x64
								_pExceptionInfo->ContextRecord->Rip++;
					#else
								_pExceptionInfo->ContextRecord->Eip++;
					#endif
							}
							return EXCEPTION_CONTINUE_EXECUTION;
						}
						else
						{
							if (g_fOrgTerminateProcess)
								g_fOrgTerminateProcess(GetCurrentProcess(), 201);
							else
								TerminateProcess(GetCurrentProcess(), 201);
						}



						return EXCEPTION_CONTINUE_SEARCH;
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

			static bool fg_DefaultCrashDumpUserNotify
				(
					NStr::CStrNonTracked const &_CustomMessage
					, NStr::CStrNonTracked const &_ProgramName
					, NStr::CStrNonTracked const &_SupportEmail
					, NStr::CStrNonTracked const &_FileName
					, NStr::CStrNonTracked const &_FileNameDumpMini
					, NStr::CStrNonTracked const &_FileNameDump
					, bool _bAllowContinue
				)
			{
				NStr::CStrNonTracked MessageText;

				auto &SubSystem = fg_Debug_Platfrom_Windows();

				if (_CustomMessage.f_IsEmpty())
				{
					if (_bAllowContinue)
					{
						if (SubSystem.m_CrashDumpUserNotifyFormat_CanContinueMessage.f_IsEmpty())
							MessageText = NStr::CStrNonTracked::CFormat("{0} has encountered an unhandled exception. Please send the following crash log files to {1}"\
							" along with a description of what you were doing when the program crashed.\r\n\r\n"\
							"{2}\r\n"\
							"{3}\r\n"\
							"\r\nAlso please save the following crash log file for future reference:\r\n\r\n"\
							"{4}\r\n"\
							"\r\nDo you want to continue execution?") << _ProgramName << _SupportEmail << _FileName << _FileNameDumpMini << _FileNameDump;
						else
							MessageText = NStr::CStrNonTracked::CFormat(SubSystem.m_CrashDumpUserNotifyFormat_CanContinueMessage)
								<< _ProgramName << _SupportEmail << _FileName << _FileNameDumpMini << _FileNameDump;
					}
					else
					{
						if (SubSystem.m_CrashDumpUserNotifyFormat_NoContinueMessage.f_IsEmpty())
							MessageText = NStr::CStrNonTracked::CFormat("{0} has encountered an unhandled exception. Please send the following crash log files to {1}"\
							" along with a description of what you were doing when the program crashed.\r\n\r\n"\
							"{2}\r\n"\
							"{3}\r\n"\
							"\r\nAlso please save the following crash log file for future reference:\r\n\r\n"\
							"{4}\r\n") << _ProgramName << _SupportEmail << _FileName << _FileNameDumpMini << _FileNameDump;
						else
							MessageText = NStr::CStrNonTracked::CFormat(SubSystem.m_CrashDumpUserNotifyFormat_NoContinueMessage)
								<< _ProgramName << _SupportEmail << _FileName << _FileNameDumpMini << _FileNameDump;
					}
				}
				else
				{
					if (SubSystem.m_CrashDumpUserNotifyFormat_CustomMessage.f_IsEmpty())
						MessageText = NStr::CStrNonTracked::CFormat(
						"{0}\r\n\r\n"\
						"{1}\r\n"\
						"{2}\r\n"\
						"\r\nAlso please save the following crash log file for future reference:\r\n\r\n" \
						"{3}") << _CustomMessage << _FileName << _FileNameDumpMini << _FileNameDump;
					else
						MessageText = NStr::CStrNonTracked::CFormat( SubSystem.m_CrashDumpUserNotifyFormat_CustomMessage ) 
							<< _CustomMessage << _FileName << _FileNameDumpMini << _FileNameDump;
				}

				if (NMib::NSys::fg_ConsoleErrorOutputValid())
				{
					DMibConErrOut("{}" DMibNewLine, MessageText);
					if (_CustomMessage.f_IsEmpty())
						return false;
					else
						return true;
				}
				else
				{
					class CMessageBoxThread : public NMib::NThread::CThread
					{
					public:
						virtual ch8 const *f_GetThreadNameRaw()
						{
							return "Malterlib_MessageBoxThread";
						}
						virtual NStr::CStr f_GetThreadName()
						{
							return "Malterlib_MessageBoxThread";
						}
						NStr::CStrNonTracked m_MessageBoxText;
						NStr::CStrNonTracked m_MessageBoxHeading;
						uint32 m_MessageBoxFlags;
						uint32 m_bRet;

						aint f_Main()
						{
							m_bRet = MessageBoxW(nullptr, NStr::NPlatform::fg_StrToWindows<NStr::CWStrNonTracked>(m_MessageBoxText), NStr::NPlatform::fg_StrToWindows<NStr::CWStrNonTracked>(m_MessageBoxHeading), m_MessageBoxFlags);
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

					if (_CustomMessage.f_IsEmpty())
					{
						if (_bAllowContinue)
						{
							CMessageBoxThread MessageBox;

							MessageBox.m_MessageBoxHeading = "Exception";
							MessageBox.m_MessageBoxText = MessageText;
							MessageBox.m_MessageBoxFlags = MB_YESNO | MB_ICONERROR;
							MessageBox.m_bRet = 0;
							MessageBox.f_Run();
							return MessageBox.m_bRet == IDYES;
						}
						else
						{
							CMessageBoxThread MessageBox;

							MessageBox.m_MessageBoxHeading = "Exception";
							MessageBox.m_MessageBoxText = MessageText;
							MessageBox.m_MessageBoxFlags = MB_OK | MB_ICONERROR;
							MessageBox.m_bRet = 0;
							MessageBox.f_Run();
							return false;
						}
					}
					else
					{
						CMessageBoxThread MessageBox;

						MessageBox.m_MessageBoxHeading = "Exception";
						MessageBox.m_MessageBoxText = MessageText;
						MessageBox.m_MessageBoxFlags = MB_OK | MB_ICONERROR;
						MessageBox.m_bRet = 0;
						MessageBox.f_Run();

						return true;
					}
				}
			}

			LONG WINAPI CSubSystem_Debug_Platform_Windows::fsp_UnhandledException(struct _EXCEPTION_POINTERS *_pExceptionInfo)
			{
				return fsp_DumpExceptionInformation(_pExceptionInfo, NStr::CStr(), NStr::CStr(), nullptr, true);
			}
		}
	}
}
