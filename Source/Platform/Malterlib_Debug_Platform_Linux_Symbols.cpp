// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include "Malterlib_Debug_Platform_Linux_Symbols.h"
#include "Malterlib_Debug_Platform_Linux_SymbolsIndex.h"
#include <cxxabi.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "libdwarf.h"
#include "dwarf.h"
#include <cxxabi.h>
#include <dlfcn.h>
#include <cstddef>
//#include "libelftc.h"

extern "C"
{
	module_export void nontracked_free (void *__ptr) __THROW;
}

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			struct CSubSystem_Debug_Platform_Linux_Symbols : public CSubSystem
			{
				CSymbols m_Symbols;
				~CSubSystem_Debug_Platform_Linux_Symbols()
				{
				}
			};
			
			TCSubSystem<CSubSystem_Debug_Platform_Linux_Symbols, ESubSystemDestruction_BeforeNonTrackedMemoryManager> g_SubSystem_Debug_Platform_Linux_Symbols = {DAggregateInit};
			
			CSymbols &fg_GetSymbols()
			{
				return g_SubSystem_Debug_Platform_Linux_Symbols->m_Symbols;
			}

			// 
			// CSymbolsIndex Imp
			//

			CSymbolsIndex::CSymbolsIndex(char const* _pFilename, mint _BaseAddress)
				: mp_bOK(false)
				, mp_Dwarf(nullptr)
				, mp_ModuleFilename(_pFilename)
				, mp_BaseAddress(_BaseAddress)
				, mp_pElf(nullptr)
			{
				int FD = open(_pFilename, O_RDONLY);
				if (FD < 0)
					return;

				Dwarf_Error Error;

				if (dwarf_init(FD, DW_DLC_READ, nullptr, nullptr, &mp_Dwarf, &Error))
				{
					mp_ErrorMessage = CSymStr::CFormat("dwarf_init: {}") << dwarf_errmsg(Error);
					return;
				}

				if (dwarf_get_elf(mp_Dwarf, &mp_pElf, &Error) != DW_DLV_OK)
				{
					mp_ErrorMessage = CSymStr::CFormat("dwarf_init: {}") << dwarf_errmsg(Error);
					return;
				}

				mp_bOK = true;

				mp_bOK = mp_bOK && fp_CollectUnits();
			}

			CSymbolsIndex::~CSymbolsIndex()
			{

				if (mp_Dwarf)
				{
					for (auto UnitIter = mp_lUnits.f_GetIterator()
						;UnitIter
						;++UnitIter)
					{
						dwarf_srclines_dealloc(mp_Dwarf, (*UnitIter).m_lLines, (*UnitIter).m_nLines);
						dwarf_dealloc(mp_Dwarf, (*UnitIter).m_pDie, DW_DLA_DIE);
					}

					Dwarf_Error Error;
					dwarf_finish(mp_Dwarf, &Error);
				}

				if (mp_pElf)
				{
					elf_end(mp_pElf);
				}
			}

			bool CSymbolsIndex::f_OK() const
			{
				return mp_bOK;
			}

			CLinuxStackTraceInfo* CSymbolsIndex::f_Lookup(mint _Address)
			{
				// Dumb interval search for now.
				for (auto UnitIter = mp_lUnits.f_GetIterator()
					;UnitIter
					;++UnitIter)
				{
					if ( (*UnitIter).Contains(_Address) )
					{
						// Possible match.
						Dwarf_Signed iLine = fp_LookupLineInUnit(_Address, *UnitIter);
						if (iLine == -1)
							continue;

						// Match
						{
							CSymStr FunctionName;
							CSymStr ModuleName = mp_ModuleFilename;
							CSymStr FileName;
							Dwarf_Unsigned LineNumber;
							Dwarf_Error Error;

							// Get file line number
							if (dwarf_lineno( (*UnitIter).m_lLines[iLine], &LineNumber, &Error) != DW_DLV_OK)
							{
								LineNumber = -1; // ?
							}

							// Search for the filename by examining the containing line entry and 
							// then searching backwards if we don't find a file source entry.
							{
								char const* pFileName = "unknown";
								dwarf_linesrc((*UnitIter).m_lLines[iLine], const_cast<char**>(&pFileName), &Error);
								/*
								for (Dwarf_Signed iL = iLine; iL >= 0; --iL)
								Dwarf_Signed iL = iLine;
								{
									if (dwarf_linesrc((*UnitIter).m_lLines[iL], const_cast<char**>(&pFileName), &Error) == DW_DLV_OK)
									{
										break;
									}							
								}
								*/
								FileName = pFileName;
							}

							// Find function
							CFunction const* pFunc = fp_LookupFunctionInUnit(_Address, (*UnitIter));
							if (pFunc)
							{
								{
									//CDisableHeapOverrideScope Scope;
									int Status = -1;
									char *pDemangled = abi::__cxa_demangle(pFunc->m_pName, nullptr, nullptr, &Status);
									
									if (Status == 0)
									{
										FunctionName = pDemangled;
	#ifdef _LIBCPP_BUILD_STATIC
										nontracked_free(pDemangled);
	#else
										free(pDemangled);
	#endif
									}
									else
									{
										FunctionName = pFunc->m_pName;
									}
								}
							}

							NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap> pInfo
								= fg_Construct(std::move(FunctionName), std::move(ModuleName), std::move(FileName), LineNumber);

							return pInfo.f_Detach();
						}
					}
				}
				
				return nullptr;
			}

			void CSymbolsIndex::f_Return(CStackTraceInfo* _pInfo)
			{
				NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap> pInfo = NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap>((CLinuxStackTraceInfo*)_pInfo);
			}

			//
			// CSymbolsIndex Private Methods
			//


			Dwarf_Signed CSymbolsIndex::fp_LookupLineInUnit(mint _Address, CUnit const& _Unit) const
			{

				aint iLowerBound = _Unit.m_lSortedLines.f_BinarySearchLowerBound
					(
							[&](CLineEntry const& _Entry, mint _ToFind)
							{
								return _Entry.m_PC < _ToFind;
							}
						,	_Address					
					)
				;

				if (iLowerBound >= 0 && iLowerBound < _Unit.m_lSortedLines.f_GetLen())
				{
					aint iLine = iLowerBound;

					if (_Address < _Unit.m_lSortedLines[iLine].m_PC)
					{
						if (iLine == 0)
						{
							return -1;
						}

						--iLine;
					}
				
					return _Unit.m_lSortedLines[iLine].m_iLine;
				}
				else
				{
					return -1;
				}
			}

			CFunction const* CSymbolsIndex::fp_LookupFunctionInUnit(mint _Address, CUnit const& _Unit) const
			{
				if ( ! (_Unit.m_Flags & CUnit::EFlag_ReadFunctions) )
				{
					CUnit& Unit = const_cast<CUnit&>(_Unit);
					fp_IndexUnitFunctions(Unit);
					Unit.m_Flags |= CUnit::EFlag_ReadFunctions;
				}

				aint iFunc = _Unit.m_lSortedFunctions.f_BinarySearchLowerBound
					(
							[&](CFunction const& _Func, mint _Address)
							{
								return _Func.m_LowPC < _Address;
							}
						,	_Address
					)
				;

				if (iFunc < _Unit.m_lSortedFunctions.f_GetLen())
				{			
					if (_Address < _Unit.m_lSortedFunctions[iFunc].m_LowPC)
					{
						if (iFunc == 0)
							return nullptr;

						--iFunc;
					}

					if (_Unit.m_lSortedFunctions[iFunc].m_HighPC > _Address)
					{
						return &_Unit.m_lSortedFunctions[iFunc];
					}
				}

				return nullptr;
			}

			bool CSymbolsIndex::fp_CollectUnits()
			{		
				int Result;
				Dwarf_Error Error;
				Dwarf_Die pDie;
				Dwarf_Die pRetDie;
				Dwarf_Half Tag;

				while ( (Result = dwarf_next_cu_header_b(mp_Dwarf, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, &Error)) ==  DW_DLV_OK )
				{
					pDie = nullptr;

					while (dwarf_siblingof(mp_Dwarf, pDie, &pRetDie, &Error) == DW_DLV_OK)
					{
						if (pDie)
							dwarf_dealloc(mp_Dwarf, pDie, DW_DLA_DIE);
						pDie = pRetDie;

						if (dwarf_tag(pDie, &Tag, &Error) != DW_DLV_OK)
						{
							dwarf_dealloc(mp_Dwarf, pDie, DW_DLA_DIE);

							mp_ErrorMessage = CSymStr::CFormat("dwarf_tag: {}") << dwarf_errmsg(Error);
							return false;
						}

						if (Tag == DW_TAG_compile_unit)
							break;
					}

					if (pDie == nullptr || Tag != DW_TAG_compile_unit)
					{
						if (pDie)
							dwarf_dealloc(mp_Dwarf, pDie, DW_DLA_DIE);

						continue;
					}

					CUnit CurUnit;
					CurUnit.m_pDie = pDie;

					Dwarf_Unsigned LowPC, HighPC;

					// If we have a low & high pc use those, otherwise just make the
					// unit span the whole space for now.
					// (This will be corrected if line info is available)
					if (dwarf_attrval_unsigned(pDie, DW_AT_low_pc, &LowPC, &Error) == DW_DLV_OK)
					{
						CurUnit.m_LowPC = LowPC;
					}
					else
					{
						CurUnit.m_LowPC = 0;
					}

					if (dwarf_attrval_unsigned(pDie, DW_AT_high_pc, &HighPC, &Error) == DW_DLV_OK)
					{
						CurUnit.m_HighPC = HighPC;
					}
					else
					{
						CurUnit.m_HighPC = ~(mint)0;
					}

	/* TODO: Currently do not handle ranges as clang is not generating them.
					Dwarf_Unsigned RangesPtr;
					if (dwarf_attrval_unsigned(pDie, DW_AT_ranges, &RangesPtr, &Error) == DW_DLV_OK)
					{
						DMibTraceRaw("\tUnit has ranges\n");
					}
					else
					{
						DMibTraceRaw("\tUnit does not have ranges\n");
					}
	*/

					if (dwarf_srclines(pDie, &CurUnit.m_lLines, &CurUnit.m_nLines, &Error) == DW_DLV_OK)
					{
						// Examine all lines to find address space range and also build sorted list of lines.

						CurUnit.m_lSortedLines.f_SetLen(CurUnit.m_nLines);

						Dwarf_Addr LineAddr;
						mint nValidLines = 0;

						for (Dwarf_Signed iL = 0; iL < CurUnit.m_nLines; ++iL)
						{
							if (dwarf_lineaddr(CurUnit.m_lLines[iL], &LineAddr, &Error) == DW_DLV_OK)
							{
								CurUnit.m_lSortedLines[nValidLines] = { (mint)LineAddr, (mint)iL };
								++nValidLines;
							}
						}

						CurUnit.m_lSortedLines.f_SetLen(nValidLines);

						CurUnit.m_lSortedLines.f_Sort(
								[](CLineEntry const& _A, CLineEntry const& _B) -> bool
								{
									return _A.m_PC < _B.m_PC;
								});

						if (!CurUnit.m_lSortedLines.f_IsEmpty())
						{
							CurUnit.m_LowPC = CurUnit.m_lSortedLines[0].m_PC;
							CurUnit.m_HighPC = CurUnit.m_lSortedLines[CurUnit.m_lSortedLines.f_GetLen() - 1].m_PC;
						}

						CurUnit.m_Flags |= CUnit::EFlag_ReadLines;

					}
					else
					{
						// No line info
					}

					mp_lUnits.f_Insert(std::move(CurUnit));
				}

				// Reset internal CU pointer. (Not actually required by us atm)
				{
					while (Result != DW_DLV_NO_ENTRY)
					{
						if (Result == DW_DLV_ERROR)
						{
							mp_ErrorMessage = CSymStr::CFormat("dwarf_next_cu_header: {}") << dwarf_errmsg(Error);
							return false;
						}
						Result = dwarf_next_cu_header_b(mp_Dwarf, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, &Error);
					}
				}
				return true;
			}

			bool CSymbolsIndex::fp_IndexUnitFunctions(CUnit& _Unit) const
			{

				Dwarf_Error Error;
				dwarf_set_cu_from_die(mp_Dwarf, _Unit.m_pDie, &Error);

	//			fp_CollectFunctions(_Unit.m_pDie, _Unit);
				fp_CollectFunction(_Unit.m_pDie, _Unit);

				_Unit.m_lSortedFunctions.f_Sort(
						[](CFunction const& _A, CFunction const& _B) -> bool
						{
							return _A.m_LowPC < _B.m_HighPC;
						}
					);

				return true;
			}

			// Does not deallocate _pDie.
			bool CSymbolsIndex::fp_CollectFunction(Dwarf_Die _pDie, CUnit& _Unit) const
			{
				Dwarf_Half Tag;
				Dwarf_Error Error;
				Dwarf_Unsigned LowPC, HighPC;

				if (dwarf_tag(_pDie, &Tag, &Error) == DW_DLV_OK)
				{
					if (0)
					{ // DEBUG
						char const* pTagName = nullptr;
						if ( dwarf_get_TAG_name(Tag, &pTagName) == DW_DLV_OK)
							DMibTrace("Tag: {}\n", pTagName);
						else
							DMibTraceRaw("Tag: <unknown>\n");
					}
					if (	Tag == DW_TAG_subprogram
						&&	dwarf_attrval_unsigned(_pDie, DW_AT_low_pc, &LowPC, &Error) == DW_DLV_OK
						)
					{
						CFunction NewFunc;

						if (dwarf_attrval_unsigned(_pDie, DW_AT_high_pc, &HighPC, &Error) != DW_DLV_OK)
							HighPC = LowPC;

						NewFunc.m_LowPC = LowPC;
						NewFunc.m_HighPC = HighPC;
						NewFunc.m_pName = "unknown";
			
						Dwarf_Attribute NameAttr, SpecAttr;
						char* pFuncName;

						int Ret = dwarf_attr(_pDie, DW_AT_name, &NameAttr, &Error);
						if (	dwarf_attr(_pDie, DW_AT_name, &NameAttr, &Error) == DW_DLV_OK
							&&	dwarf_formstring(NameAttr, &pFuncName, &Error) == DW_DLV_OK)
						{
							NewFunc.m_pName = pFuncName;
						}
						else if (Ret == DW_DLV_ERROR)
						{

						}
						else
						{ // Try using spec.
							Dwarf_Off Ref;
							Dwarf_Die SpecDie;
							char const* pFuncName2;
							if (	dwarf_attr(_pDie, DW_AT_specification, &SpecAttr, &Error) == DW_DLV_OK
								&&	dwarf_global_formref(SpecAttr, &Ref, &Error) == DW_DLV_OK)
							{
								if (dwarf_offdie(mp_Dwarf, Ref, &SpecDie, &Error) == DW_DLV_OK)
								{
									if(dwarf_attrval_string(SpecDie, DW_AT_name, &pFuncName2, &Error) == DW_DLV_OK)
									{
										NewFunc.m_pName = pFuncName2;
									}
									dwarf_dealloc(mp_Dwarf, SpecDie, DW_DLA_DIE);
									SpecDie = nullptr;
								}
							}
						}

						_Unit.m_lSortedFunctions.f_Insert(std::move(NewFunc));
					}
					/* clang does not generate ranges for subprograms atm
					else if ( Tag == DW_TAG_subprogram)
					{
						Dwarf_Unsigned RangesPtr;
						if (dwarf_attrval_unsigned(_pDie, DW_AT_ranges, &RangesPtr, &Error) == DW_DLV_OK)
						{
							DMibTraceRaw("\tSub program has ranges\n");
						}
						else
						{
							DMibTraceRaw("\tSub program does not have ranges\n");
						}
					}
					//*/

				}

				int Ret;
				bool bRecurseRet = true;

				Dwarf_Die pRetDie;

				/* Search children. */
				Ret  = dwarf_child(_pDie, &pRetDie, &Error);
				if (Ret == DW_DLV_ERROR)
				{
					mp_ErrorMessage = CSymStr::CFormat("fp_CollectFunctions: dwarf_child: {}") << dwarf_errmsg(Error);
					return false;
				}
				else if (Ret == DW_DLV_OK)
				{
					bRecurseRet = fp_CollectFunctions(pRetDie, _Unit);
				}

				if (!bRecurseRet)
					return false;

				return true;
			}

			// Always deallocated _pDie
			bool CSymbolsIndex::fp_CollectFunctions(Dwarf_Die _pDie, CUnit& _Unit) const
			{
				fp_CollectFunction(_pDie, _Unit);

				int Ret = DW_DLV_OK;
				bool bRecurseRet = true;

				Dwarf_Die pRetDie;
				Dwarf_Die pPrevDie;

				// Check siblings
				Dwarf_Error Error;

				pPrevDie = nullptr;

				while (_pDie && Ret == DW_DLV_OK)
				{
					Ret = dwarf_siblingof(mp_Dwarf, _pDie, &pRetDie, &Error);
					
					dwarf_dealloc(mp_Dwarf, _pDie, DW_DLA_DIE);
					_pDie = nullptr;

					if (Ret == DW_DLV_ERROR)
					{
						mp_ErrorMessage = CSymStr::CFormat("fp_CollectFunctions: dwarf_siblingof: {}") << dwarf_errmsg(Error);
						return false;
					}
					else if (Ret == DW_DLV_OK)
					{
						_pDie = pRetDie;
						bRecurseRet = fp_CollectFunction(_pDie, _Unit);		
					}
					else
					{
						// Is this possible? Is it an error?
						break;
					}

					if (!bRecurseRet)
						return false;
				}

				return true;
			}

			//
			// CSymbols
			//

			bool fg_FindModuleInfo(char const* _pFilename)
			{
				return false;
			}

			CSymbols::CSymbols()
			{

			}

			CSymbols::~CSymbols()
			{
			}


			CStackTraceInfo* CSymbols::f_AcquireStackTraceInfo(mint _Address)
			{
	#if 1
				Dl_info Info;
				NMem::fg_MemClear(Info);
				if (!dladdr((void*)_Address, &Info))
				{
					NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap> pTemp = fg_Construct(CSymStr("dladdr failed"), CSymStr(), CSymStr(), 0);
					return pTemp.f_Detach();
				}

				CSymStr FunctionName;
				if (Info.dli_sname)
				{
					int Status = -1;
					char *pDemangled = nullptr;
					pDemangled = abi::__cxa_demangle(Info.dli_sname, nullptr, nullptr, &Status);
					
					if (pDemangled && Status == 0)
					{
						FunctionName = (const char *)pDemangled;
	#ifdef _LIBCPP_BUILD_STATIC
						nontracked_free(pDemangled);
	#else
						free(pDemangled);
	#endif
					}
					else
						FunctionName = Info.dli_sname;
				}
				
				NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap> pTemp = fg_Construct(fg_Move(FunctionName), CSymStr(Info.dli_fname ? Info.dli_fname : ""), CSymStr(), 0);
				return pTemp.f_Detach();
	#else
				DMibLock(mp_Lock);

				CSymStr ModuleFilename;
				mint ModuleBase = 0;

				// Find out which module the address is in (exe or shared lib)
				Dl_info Info;
				NMem::fg_MemClear(Info);
				if (dladdr((void*)_Address, &Info))
				{
					ModuleFilename = Info.dli_fname;
					ModuleBase = reinterpret_cast<mint>(Info.dli_fbase);
	//				DMibTrace("dladdr name: {}\n", (Info.dli_sname ? Info.dli_sname : ""));
				}
				else if (dladdr((void*)&fg_FindModuleInfo, &Info))
				{
					ModuleFilename = Info.dli_fname;
					ModuleBase = reinterpret_cast<mint>(Info.dli_fbase);
					NMem::fg_MemClear(Info);
				}

				CSymbolsIndex* pIndex = nullptr;

				NPtr::TCUniquePointer<CSymbolsIndex, NMem::CAllocator_NonTrackedHeap>* pStoredIndex
					= mp_IndexLookup.f_FindEqual(ModuleFilename);

				if (pStoredIndex)
					pIndex = (*pStoredIndex).f_Get();
				else
				{
	//				DMibTrace("Creating index for {}\n", ModuleFilename);
					NPtr::TCUniquePointer<CSymbolsIndex, NMem::CAllocator_NonTrackedHeap> pNewIndex = fg_Construct(ModuleFilename.f_GetStr(), ModuleBase);

					if (!pNewIndex->f_OK())
						pNewIndex.f_Clear();

					pIndex = pNewIndex.f_Get();

					mp_IndexLookup[ModuleFilename] = std::move(pNewIndex);				
				}

				if (pIndex)
				{
					CLinuxStackTraceInfo* pInfo = pIndex->f_Lookup(_Address);

					if (pInfo && pInfo->m_FunctionName.f_IsEmpty() && Info.dli_sname != nullptr)
					{
						pInfo->m_FunctionName = Info.dli_sname;
						pInfo->m_pFunctionName = pInfo->m_FunctionName.f_GetStr();
					}
					
					if (!pInfo)
					{
						NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap> pTemp = fg_Construct(CSymStr(Info.dli_sname ? Info.dli_sname : ""), CSymStr(ModuleFilename), CSymStr(""), 0);
						pInfo = pTemp.f_Detach();
					}

					return pInfo;
				}
				else
				{
					CSymStr FunctionName = Info.dli_sname ? Info.dli_sname : "";
					CSymStr ModuleName = Info.dli_fname ? Info.dli_fname : "";
					CSymStr FileName = "<unknown>";
					int LineNumber = -1;

					NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap> pInfo
						= fg_Construct(std::move(FunctionName), std::move(ModuleName), std::move(FileName), LineNumber);
					
					return pInfo.f_Detach();
				}
	#endif
			}

			void CSymbols::f_ReleaseStackTraceInfo(CStackTraceInfo* _pInfo)
			{
				DMibLock(mp_Lock);

				NPtr::TCUniquePointer<CLinuxStackTraceInfo, NMem::CAllocator_NonTrackedHeap> pInfo = fg_Explicit((CLinuxStackTraceInfo*)_pInfo);
			}
		}
	}
}
