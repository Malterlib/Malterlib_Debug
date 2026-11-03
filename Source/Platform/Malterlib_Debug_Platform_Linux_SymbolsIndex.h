// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <Mib/Core/Core>
#include "Malterlib_Debug_Platform_Linux_Symbols.h"

#include "libdwarf.h"
#include "dwarf.h"

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			//
			// CSymbolsIndex
			//

			struct CRange
			{
				umint m_LowPC;
				umint m_HighPC;

				CRange()
				{
				}

				CRange(CRange const &_ToCopy)
					: m_LowPC(_ToCopy.m_LowPC)
					, m_HighPC(_ToCopy.m_HighPC)
				{
				}

				CRange(CRange &&_ToMove)
					: m_LowPC(_ToMove.m_LowPC)
					, m_HighPC(_ToMove.m_HighPC)
				{
				}

				CRange(umint _Low, umint _High)
					: m_LowPC(_Low)
					, m_HighPC(_High)
				{
				}

				bool f_Contains(umint _Value) const
				{
					return (_Value >= m_LowPC) && (_Value < m_HighPC);
				}
			};

			struct CLineEntry
			{
				umint m_PC;
				umint m_iLine; // Index in unit list.
			};

			struct CFunction
			{
				umint m_LowPC;
				umint m_HighPC;
				char const *m_pName; // Memory owned by libdwarf
			};

			struct CUnit : public CRange
			{
				enum EFlag
				{
					EFlag_None            = 0
					, EFlag_ReadFunctions = DMibBit(0)
					, EFlag_ReadLines     = DMibBit(1)
				};

				CUnit()
					: m_Flags(EFlag_None)
				{
				}

				CUnit(CUnit const &_ToCopy)
					: CRange(_ToCopy)
					, m_Flags(_ToCopy.m_Flags)
					, m_pDie(_ToCopy.m_pDie)
					, m_nLines(_ToCopy.m_nLines)
					, m_pLines(_ToCopy.m_pLines)
					, m_SortedLines(_ToCopy.m_SortedLines)
				{
				}

				CUnit(CUnit &&_ToMove)
					: CRange(std::move(_ToMove))
					, m_Flags(_ToMove.m_Flags)
					, m_pDie(_ToMove.m_pDie)
					, m_nLines(_ToMove.m_nLines)
					, m_pLines(_ToMove.m_pLines)
					, m_SortedLines(std::move(_ToMove.m_SortedLines))
				{
				}

				EFlag m_Flags;
				Dwarf_Die m_pDie;
				Dwarf_Signed m_nLines;
				Dwarf_Line *m_pLines;
				NContainer::TCVector<CLineEntry, NMemory::CAllocator_NonTrackedHeap> m_SortedLines;
				NContainer::TCVector<CFunction, NMemory::CAllocator_NonTrackedHeap> m_SortedFunctions;
			};

			struct CSymbolsIndex
			{
				/*
				NOTE:
					Computational unit address ranges MAY overlap.
					Function (Sub Program) address ranges WILL NOT overlap.
				*/
			private:
				bool mp_bOK;
				mutable CSymStr mp_ErrorMessage;

				Elf *mp_pElf;
				Dwarf_Debug mp_pDwarf;

				NContainer::TCVector<CUnit, NMemory::CAllocator_NonTrackedHeap> mp_Units;

				CSymStr mp_ModuleFilename;
				umint mp_BaseAddress;

				Dwarf_Signed fp_LookupLineInUnit(umint _Address, CUnit const &_Unit) const;
				CFunction const *fp_LookupFunctionInUnit(umint _Address, CUnit const &_Unit) const;
				bool fp_CollectUnits();
				bool fp_IndexUnitFunctions(CUnit &_Unit) const;
				bool fp_CollectFunction(Dwarf_Die _pDie, CUnit &_Unit) const;
				bool fp_CollectFunctions(Dwarf_Die _pDie, CUnit &_Unit) const;

			public:
				CSymbolsIndex(char const *_pFilename, umint _BaseAddress);
				~CSymbolsIndex();

				bool f_OK() const;

				CLinuxStackTraceInfo *f_Lookup(umint _Address);
				void f_Return(CStackTraceInfo *_pInfo);
			};
		}
	}
}
