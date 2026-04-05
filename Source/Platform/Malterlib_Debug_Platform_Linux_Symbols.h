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

			class CLinuxStackTraceInfo : public CStackTraceInfo
			{
			public:
				CSymStr m_FunctionName;
				CSymStr m_ModuleName;
				CSymStr m_FileName;

				CLinuxStackTraceInfo(CSymStr&& _FuncName, CSymStr&& _ModuleName, CSymStr&& _FileName, int _iLine)
					: m_FunctionName(std::move(_FuncName))
					, m_ModuleName(std::move(_ModuleName))
					, m_FileName(std::move(_FileName))
				{
					this->m_pContext = nullptr;
					m_pFunctionName = m_FunctionName.f_GetStr();
					m_pModuleName = m_ModuleName.f_GetStr();
					m_pSourceFileName = m_FileName.f_GetStr();
					m_SourceLine = _iLine;
				}
			};

			//
			// CSymbols
			//

			class CSymbolsIndex;

			class CSymbols
			{
			public:
			private:
				NThread::CMutual mp_Lock;

				NContainer::TCMap<
							CSymStr
						,	NStorage::TCUniquePointer<CSymbolsIndex, NMemory::CAllocator_NonTrackedHeap>
						,	NMib::CSort_Default
						,	NMemory::CAllocator_NonTrackedHeap> mp_IndexLookup;

			public:
				CSymbols();
				~CSymbols();

				CStackTraceInfo* f_AcquireStackTraceInfo(umint _Address);
				void f_ReleaseStackTraceInfo(CStackTraceInfo* _pInfo);
			};

			CSymbols& fg_GetSymbols();
		}
	}
}
