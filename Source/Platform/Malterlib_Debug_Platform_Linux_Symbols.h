// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#pragma once

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{

			typedef NStr::CStrNonTracked CSymStr;


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
						,	NPtr::TCUniquePointer<CSymbolsIndex, NMem::CAllocator_NonTrackedHeap>
						,	NMib::CSort_Default
						,	NMem::CAllocator_NonTrackedHeap> mp_IndexLookup;
						
			public:
				CSymbols();
				~CSymbols();

				CStackTraceInfo* f_AcquireStackTraceInfo(mint _Address);
				void f_ReleaseStackTraceInfo(CStackTraceInfo* _pInfo);
			};

			CSymbols& fg_GetSymbols();
		}
	}
}
