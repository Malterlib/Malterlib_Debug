// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{
			using CSymStr = NStr::CStrNonTracked;

			//
			// CLinuxStackTraceInfo
			//

			struct CLinuxStackTraceInfo : public CStackTraceInfo
			{
				CLinuxStackTraceInfo(CSymStr &&_FuncName, CSymStr &&_ModuleName, CSymStr &&_FileName, int _iLine);

				CSymStr m_FunctionName;
				CSymStr m_ModuleName;
				CSymStr m_FileName;
			};

			//
			// CSymbols
			//

			struct CSymbolsIndex;

			struct CSymbols
			{
				CSymbols();
				~CSymbols();

				CStackTraceInfo *f_AcquireStackTraceInfo(umint _Address);
				void f_ReleaseStackTraceInfo(CStackTraceInfo *_pInfo);

			private:
				NThread::CMutual mp_Lock;

				NContainer::TCMap<CSymStr, NStorage::TCUniquePointer<CSymbolsIndex, NMemory::CAllocator_NonTrackedHeap>, NMib::CSort_Default, NMemory::CAllocator_NonTrackedHeap>
					mp_IndexLookup
				;
			};

			CSymbols &fg_GetSymbols();
		}
	}
}
