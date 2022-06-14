// Copyright © 2015 Hansoft AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

/*
	Author:			Michael Wynne

	Contents:		NMib::NDebug::NPlatform::CSymbols

	Comments:		CSymbols implements looking up symbols in a .symbols files generated from a
					dSym via the patched google breakpad dump_syms utility.

					Currently no caching is performed of the symbols file.

					If required simlple optimisations are:

					*	Just load all the function headers into memory. :-)
						*	Could change the on disk layout to split functions into two
							arrays with the cached array just consisting of Address + Size

					*	Build an in-memory binary tree (in a vector) of the first N functions.
						Note this means caching functions at indices:
							nFuncs / 2
							(nFuncs / 2) + (nFuncs / 4)
							(nFuncs / 2) - (nFuncs / 4)
							etc...

					If you do not specify a symbols file it assumes there is one in the same
					folder as the exe with the same name, but with a .symbols extension.

					The symbols file is opened the first time a symbol is requested.

*/

#pragma once

#include <Mib/Core/Core>

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{

			typedef NMib::NStr::CStrNonTracked CSymStr;

			struct CAddressInfo
			{
				mint m_Address;
				CSymStr m_File;
				mint m_Line;
				CSymStr m_Function;
			};

			struct CMacOSStackTraceInfo : public CStackTraceInfo
			{
				CMacOSStackTraceInfo()
				{
					this->m_pContext = nullptr;
				}
				CSymStr m_FunctionName;
				CSymStr m_ModuleName;
				CSymStr m_FileName;
			};

			struct CAddressInfoCache
			{
				CMacOSStackTraceInfo m_StackTraceInfo;
				bool m_bValidCache = false;
				bool m_bSuccessful = false;
				NThread::CLowLevelLock m_Lock;
			};

			/*
			CSymbols implements looking up symbols in a .symbols files generated from a dSym via
			the patched google breakpad dump_syms utility.
			*/
			class CSymbols
			{
			private:

				struct CHeader
				{
					uint32 m_Version;

					uint32 m_OSOffset;
					uint32 m_ArchOffset;
					uint32 m_UUIDOffset;
					uint32 m_NameOffset;

					uint32 m_FunctionsOffset;
					uint32 m_nFunctions;

					uint32 m_LinesOffset;
					uint32 m_nLines;

					uint32 m_StringDataOffset;
				};

				struct CLinesHeader
				{
					uint32 m_nLines;
				};

				struct CLine
				{
					uint64 m_Address;
					uint64 m_Size;

					uint32 m_Line;
					uint32 m_FileOffset;
				}; // 24 bytes (in file)

				struct CFunction
				{
					uint64 m_Address;
					uint64 m_Size;
					uint64 m_StackParamSize;

					uint32 m_NameOffset;

					uint32 m_FirstLine;

				}; // 32 bytes (in file)

				enum
				{
					BytesPerFunction = 32,
					BytesPerLine = 24,
					BytesPerFunctionLines = 4,
				};

			private:
				mint mp_AddressOffset;

				NMib::NThread::CLowLevelLock mp_Lock;
				CSymStr mp_SymbolsFilename;
				CHeader mp_Header;
				void *mp_pSymbols;

				NThread::CLowLevelLock mp_CacheLock;
				NContainer::TCMap<mint, CAddressInfoCache, CSort_Default, NMib::NMemory::CAllocator_NonTrackedHeap> mp_Cache;

			private:

				// All private methods assume mp_Lock is taken.

				bool fp_EnsureLoaded();
				void fp_Unload();

				CSymStr fp_ReadString(uint32 _Offset);

				void fp_LoadFunctionCache();
				CFunction const* fp_ReadFunction(uint32 _FuncIndex, CFunction* _pTmp);


			public:

				CSymbols();
				~CSymbols();

				void f_SetSymbolsFile(char const* _pFilename);

				bool f_Lookup(mint _Address, CAddressInfo& _oInfo);

				CAddressInfoCache &f_GetCache(mint _Address)
				{
					DMibLock(mp_CacheLock);
					return mp_Cache[_Address];
				}
			};

			CSymbols &fg_GetSymbols();

	/*

			using namespace NMib::NStr;
			using namespace NMib::NContainer;

			typedef CStr CSymStr;

			struct CFile
			{
				mint m_Index;
				CSymStr m_Name;

				CFile()
					: m_Index(0)
				{}

				CFile(CFile&& _ToMove)
					: m_Index(_ToMove.m_Index)
					, m_Name(fg_Move(_ToMove.m_Name))
				{
				}

				CFile& operator=(CFile&& _ToMove)
				{
					m_Index = _ToMove.m_Index;
					m_Name = fg_Move(_ToMove.m_Name);
					return *this;
				}
			};

			struct CLine
			{
				mint m_Address;
				mint m_Size;
				mint m_Line;
				mint m_File;
			};

			struct CFunction
			{
				mint m_Address;
				mint m_Size;
				mint m_StackParamSize;
				CSymStr m_Name;

				TCVector<CLine> m_lLines;	// Sorted by CLine::m_Address

				CFunction()
					: m_Address(0)
					, m_Size(0)
					, m_StackParamSize(0)
				{}

				CFunction(CFunction&& _ToMove)
					: m_Address(_ToMove.m_Address)
					, m_Size(_ToMove.m_Size)
					, m_StackParamSize(_ToMove.m_StackParamSize)
					, m_Name(fg_Move(_ToMove.m_Name))
					, m_lLines(fg_Move(_ToMove.m_lLines))
				{
				}

				CFunction& operator=(CFunction&& _ToMove)
				{
					m_Address = _ToMove.m_Address;
					m_Size = _ToMove.m_Size;
					m_StackParamSize = _ToMove.m_StackParamSize;
					m_Name = fg_Move(_ToMove.m_Name);
					m_lLines = fg_Move(_ToMove.m_lLines);
					return *this;
				}
			};

			struct CAddressInfo
			{
				mint m_Address;
				CSymStr m_File;
				mint m_Line;
				CSymStr m_Function;
			};

			class CSymbols
			{
				private:

					TCVector<CFile> mp_lFiles;			// Sorted by CFile::m_Index
					TCVector<CFunction> mp_lFunctions;	// Sorted by CFunc::m_Address

				public:

					CSymbols();
					~CSymbols();

					bool f_Load(char const* _pFilename);
					void f_Clear();

					bool f_Lookup(mint _Address, CAddressInfo& _oInfo);
			};
			*/
		}
	}
}
