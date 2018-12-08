// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include "Malterlib_Debug_Platform_OSX_Symbols.h"
#include <mach-o/loader.h>
#include <mach-o/dyld.h>

namespace NMib
{
	namespace NDebug
	{
		namespace NPlatform
		{

			struct CSubSystem_Debug_Platform_OSX_Symbols : public CSubSystem
			{
				CSymbols m_Symbols;
				~CSubSystem_Debug_Platform_OSX_Symbols()
				{
				}
			};
			
			TCSubSystem<CSubSystem_Debug_Platform_OSX_Symbols, ESubSystemDestruction_BeforeNonTrackedMemoryManager> g_SubSystem_Debug_Platform_OSX_Symbols = {DAggregateInit};
			
			CSymbols &fg_GetSymbols()
			{
				return g_SubSystem_Debug_Platform_OSX_Symbols->m_Symbols;
			}
			
			template <typename t_CSorter, typename t_CFind>
			aint fg_BinarySearchLowerBound(mint _nItems, t_CSorter &&_Sorter, const t_CFind &_ToFind)
			{
				mint Len = _nItems;

				mint Low = 0;
				mint High = Len;

				while(Low < High)
				{
					mint Mid = (Low + High) >> 1;
					if(fg_Forward<t_CSorter>(_Sorter)(Mid, _ToFind))
						Low = Mid + 1;
					else
						High = Mid;
				}

				return Low;
			}

			CSymbols::CSymbols()
				: mp_AddressOffset(0)
				, mp_pSymbols(nullptr)
			{
				mach_header const* pHeader = (mach_header const*)_dyld_get_image_header(0);

				if (pHeader)
				{
					unsigned long Slide = _dyld_get_image_vmaddr_slide(0);

					if (pHeader->magic == MH_MAGIC)
					{
						struct load_command const* pCmd = reinterpret_cast<struct load_command const*>(pHeader + 1);

						for (unsigned int iCmd = 0
							;iCmd < pHeader->ncmds
							;++iCmd)
						{
							struct segment_command const* pSegment = reinterpret_cast<struct segment_command const*>(pCmd);

							if (!NStr::fg_StrCmp(pSegment->segname, "__TEXT"))
							{
								mp_AddressOffset = pSegment->vmaddr + Slide;
								break;
							}

							pCmd = reinterpret_cast<struct load_command*>( (char*)pCmd + pCmd->cmdsize );
						}
					}
					else if (pHeader->magic == MH_MAGIC_64)
					{
						mach_header_64 const* pHeader64 = (mach_header_64 const*)_dyld_get_image_header(0);

						struct load_command const* pCmd = reinterpret_cast<struct load_command const*>(pHeader64 + 1);

						for (unsigned int iCmd = 0
							;iCmd < pHeader64->ncmds
							;++iCmd)
						{
							struct segment_command_64 const* pSegment = reinterpret_cast<struct segment_command_64 const*>(pCmd);

							if (!NStr::fg_StrCmp(pSegment->segname, "__TEXT"))
							{
								mp_AddressOffset = pSegment->vmaddr + Slide;
								break;
							}

							pCmd = reinterpret_cast<struct load_command*>( (char*)pCmd + pCmd->cmdsize );
						}
					}
				}

				mp_SymbolsFilename
					= CSymStr::CFormat("{}/{}.symbols")
					<< NMib::NFile::CFile::fs_GetProgramDirectory<CSymStr>()
					<< NMib::NFile::CFile::fs_GetFileNoExt(NMib::NFile::CFile::fs_GetProgramPath<CSymStr>())
				;
			}

			CSymbols::~CSymbols()
			{
				fp_Unload();
			}
			
			void CSymbols::f_SetSymbolsFile(char const* _pFilename)
			{
				DMibLock(mp_Lock);

				fp_Unload();
				mp_SymbolsFilename = _pFilename;
			}

			bint CSymbols::fp_EnsureLoaded()
			{
				if (mp_pSymbols)
					return true;

				try
				{
					if (NMib::NFile::CFile::fs_FileExists(mp_SymbolsFilename, NFile::EFileAttrib_File))
					{
						mp_pSymbols = NSys::NFile::fg_Open(mp_SymbolsFilename, NFile::EFileOpen_Read | NFile::EFileOpen_ShareRead, NFile::EFileAttrib_None);
						if (!mp_pSymbols)
							return false;

						NMib::NSys::NFile::fg_Read(mp_pSymbols, &mp_Header, 0, sizeof(mp_Header));

						fp_LoadFunctionCache();
					}
					else
						return false;
				}
				catch(NMib::NFile::CExceptionFile& _Ex)
				{
					return false;
				}


				return true;
			}

			void CSymbols::fp_Unload()
			{
				if (mp_pSymbols)
					NMib::NSys::NFile::fg_Close(mp_pSymbols);
				mp_pSymbols = nullptr;
			}

			CSymStr CSymbols::fp_ReadString(uint32 _Offset)
			{
				uint32 Offset = _Offset + mp_Header.m_StringDataOffset;
				
				uint32 nBytes;
				NMib::NSys::NFile::fg_Read(mp_pSymbols, &nBytes, Offset, sizeof(nBytes));
				Offset += sizeof(nBytes);

				CSymStr Str;
				char* pRawStr = Str.f_GetStr(nBytes + 1);
				NMib::NSys::NFile::fg_Read(mp_pSymbols, pRawStr, Offset, nBytes);
				Offset += nBytes;
				pRawStr[nBytes] = 0;
				
				return fg_Move(Str);
			}

			void CSymbols::fp_LoadFunctionCache()
			{
				// If things get slow this is where you cache the functions :-)
			}

			CSymbols::CFunction const* CSymbols::fp_ReadFunction(uint32 _FuncIndex, CFunction* _pTmp)
			{
				uint32 Offset = mp_Header.m_FunctionsOffset + BytesPerFunction * _FuncIndex;
				NMib::NSys::NFile::fg_Read(mp_pSymbols, _pTmp, Offset, sizeof(CFunction));
				Offset += sizeof(CFunction);

				return _pTmp;
			}


			bint CSymbols::f_Lookup(mint _Address, CAddressInfo& _oInfo)
			{			
				DMibLock(mp_Lock);

				if (!fp_EnsureLoaded())
					return false;

				// Adjust the incoming address to be relative to the image segment start.
				_Address -= mp_AddressOffset;

				try
				{

					// Find function
					CFunction TmpFunc;

					aint iFoundFunc = fg_BinarySearchLowerBound(
							mp_Header.m_nFunctions
						,	[&](mint _FuncIndex, mint _Address) -> bint
							{
								CFunction const* pFunc = fp_ReadFunction(_FuncIndex, &TmpFunc);

								if (pFunc)
									return pFunc->m_Address < _Address;
								else
									return false;
							}
						,	_Address
						);

					if (iFoundFunc >= mp_Header.m_nFunctions)
						return false;

					CFunction const* pFunc = fp_ReadFunction(iFoundFunc, &TmpFunc);

					if (	_Address >= pFunc->m_Address
						&&	_Address < (pFunc->m_Address + pFunc->m_Size))
					{
						_oInfo.m_Address = _Address;
						_oInfo.m_Function = fp_ReadString(pFunc->m_NameOffset);
						_oInfo.m_File = CSymStr();
						_oInfo.m_Line = 0;

						// Find line info if present.
						CLinesHeader LinesHeader;

						uint32 Offset = pFunc->m_FirstLine;
						NMib::NSys::NFile::fg_Read(mp_pSymbols, (char*)&LinesHeader, Offset, sizeof(LinesHeader));
						Offset += sizeof(LinesHeader);
						
						aint iFoundLine = fg_BinarySearchLowerBound(
								LinesHeader.m_nLines
							,	[&](mint _LineIndex, mint _Address) -> bint
								{
									CLine Line;

									uint32 Offset = pFunc->m_FirstLine + BytesPerFunctionLines + BytesPerLine * _LineIndex;
									NMib::NSys::NFile::fg_Read(mp_pSymbols, &Line, Offset, sizeof(Line));
									Offset += sizeof(Line);

									return Line.m_Address < _Address;
								}
							,	_Address);

						if (iFoundLine < LinesHeader.m_nLines)
						{
							CLine Line;

							uint32 Offset = pFunc->m_FirstLine + BytesPerFunctionLines + BytesPerLine * iFoundLine;
							NMib::NSys::NFile::fg_Read(mp_pSymbols, &Line, Offset, sizeof(Line));
							Offset += sizeof(Line);

							if (	_Address >= Line.m_Address
								&&	_Address <= (Line.m_Address + Line.m_Size) )
							{
								_oInfo.m_Line = Line.m_Line;

								if (Line.m_FileOffset != ~(uint32)0)
									_oInfo.m_File = fp_ReadString(Line.m_FileOffset);
								else
									_oInfo.m_File = CSymStr("<Unknown>");
							}
						}

						return true;
					}
					else
					{
						return false;
					}
				}
				catch(NFile::CExceptionFile const&)
				{
					return false;
				}
			}
			
			extern NMib::NStorage::TCAggregateSimple<CSymbols> g_Symbols;

			/*
			// TODO: Move into TVector
			template <typename t_CVector, typename t_CSorter, typename t_CFind>
			aint fg_BinarySearchLowerBound(t_CVector const& _lVector, t_CSorter &&_Sorter, const t_CFind &_ToFind, aint _nMax = -1)
			{
				mint Len = _lVector.f_GetLen();
				if (_nMax >= 0)
					Len = fg_Min(mint(_nMax), Len);
				mint Low = 0;
				mint High = Len;
				typename t_CVector::CData const*pArray = _lVector.f_GetArray();

				while(Low < High)
				{
					mint Mid = (Low + High) >> 1;
					if(fg_Forward<t_CSorter>(_Sorter)(pArray[Mid], _ToFind))
						Low = Mid + 1;
					else
						High = Mid;
				}
				if(Low >= 0 && Low < Len && !fg_Forward<t_CSorter>(_Sorter)(pArray[Low], _ToFind) && !fg_Forward<t_CSorter>(_Sorter)(_ToFind, pArray[Low]))
					return Low;
				else
					return Low;
			}

			class CFileLineReader
			{
			private:
				enum
				{
					EReadBufferBytes = 1024,
				};

				NFile::CFile mp_File;
				CMibFilePos mp_nFileBytes;

				mint mp_nBufferBytes;
				TCVector<char> mp_Buffer;

				bint mp_bEOF;


				void fp_FillBuffer()
				{
					CMibFilePos nBytesLeft = mp_nFileBytes - mp_File.f_GetPosition();

					CMibFilePos nToRead = fg_Min(nBytesLeft, CMibFilePos(EReadBufferBytes));

					if (nToRead > (CMibFilePos)mp_Buffer.f_GetLen())
						mp_Buffer.f_SetLen(nToRead);

					mp_File.f_Read( mp_Buffer.f_GetArray(), (mint)nToRead );
					mp_nBufferBytes = nToRead;

					if (nToRead < CMibFilePos(EReadBufferBytes))
						mp_bEOF = true;
				}

			public:
				CFileLineReader(CSymStr const& _Filename)
					: mp_nFileBytes(0)
					, mp_nBufferBytes(0)
					, mp_bEOF(false)
				{
					mp_File.f_Open(_Filename, NFile::EFileOpen_Read);
					mp_nFileBytes = mp_File.f_GetLength();
				}

				~CFileLineReader()
				{
					mp_File.f_Close(false);
				}

				bint f_EOF() const { return mp_bEOF && !mp_nBufferBytes; }

				bint f_ReadLine(CSymStr& _oLine)
				{
					CSymStr LineStr;
					bint bTerm = false;

					while(!bTerm)
					{
						if (!mp_nBufferBytes)
						{
							if (mp_bEOF)
								return false;
							fp_FillBuffer();
						}

						mint iB = 0;
						for (iB = 0
							;iB < mp_nBufferBytes
							;++iB)
						{
							if (mp_Buffer[iB] == '\n')
							{
								bTerm = true;
								break;
							}
						}

						LineStr += CSymStr(mp_Buffer.f_GetArray(), iB);

						while (		iB < mp_nBufferBytes
								&&	mp_Buffer[iB] == '\n')
						{
							++iB;
						}

						if (iB < mp_nBufferBytes)
						{
							memmove(mp_Buffer.f_GetArray(), mp_Buffer.f_GetArray() + iB, mp_nBufferBytes - iB);
						}

						mp_nBufferBytes -= iB;
					}

					_oLine = fg_Move(LineStr);
					return true;
				}
			};


			struct CFileSorter
			{
				bint operator()(CFile const& _A, CFile const& _B) const
				{
					return _A.m_Index < _B.m_Index;
				}
				bint operator()(CFile const& _A, mint _B) const
				{
					return _A.m_Index < _B;
				}
				bint operator()(mint _A, CFile const& _B) const
				{
					return _A < _B.m_Index;
				}
			};

			struct CFunctionSorter
			{
				bint operator()(CFunction const& _A, CFunction const& _B) const
				{
					return _A.m_Address < _B.m_Address;
				}

				bint operator()(CFunction const& _A, mint _B) const
				{
					return _A.m_Address < _B;
				}

				bint operator()(mint _A, CFunction const& _B) const
				{
					return _A < _B.m_Address;
				}
			};

			struct CLineSorter
			{
				bint operator()(CLine const& _A, CLine const& _B) const
				{
					return _A.m_Address < _B.m_Address;
				}
				bint operator()(CLine const& _A, mint _B) const
				{
					return _A.m_Address < _B;
				}
				bint operator()(mint _A, CLine const& _B) const
				{
					return _A < _B.m_Address;
				}
			};

			CSymbols::CSymbols()
			{
			}

			CSymbols::~CSymbols()
			{
				f_Clear();
			}

			bint CSymbols::f_Load(char const* _pFilename)
			{
				try
				{
					CFileLineReader Reader(_pFilename);

					CSymStr CurLine;
					CSymStr WholeLine;
					CSymStr FirstToken;
					TCVector<CSymStr> lErrors;
					mint iLine = 0;
					aint iCurFunc = -1;

					while (Reader.f_ReadLine(WholeLine))
					{
						CurLine = WholeLine;
						FirstToken = fg_GetStrSep(CurLine, " ");

						if (FirstToken == "FILE")
						{
							CFile NewFile;

							aint nParsed = -1;
							(CSymStr::CParse("{} {}") >> NewFile.m_Index >> NewFile.m_Name).f_Parse(CurLine, nParsed);

							if (nParsed == 2)
							{
								mp_lFiles.f_Insert(fg_Move(NewFile));
							}
							else								
							{
								lErrors.f_Insert(CSymStr::CFormat("Invalid FILE line at line # {}") << iLine);
							}
						}
						else if (FirstToken == "FUNC")
						{
							CFunction NewFunc;

							aint nParsed = -1;
							(CSymStr::CParse("{nfh} {nfh} {nfh} {}") 
									>> NewFunc.m_Address
									>> NewFunc.m_Size
									>> NewFunc.m_StackParamSize
									>> NewFunc.m_Name
									).f_Parse(CurLine, nParsed);

							if (nParsed == 4)
							{
								mp_lFunctions.f_Insert(fg_Move(NewFunc));
								iCurFunc = mp_lFunctions.f_GetLen() - 1;
							}
							else
							{
								lErrors.f_Insert(CSymStr::CFormat("Invalid FUNC line at line # {}") << iLine);
							}
						}
						else if (FirstToken == "PUBLIC")
						{
							// Unused
						}					
						else if (FirstToken == "STACK")
						{
							// Unused
						}
						else if (FirstToken == "MODULE")
						{
							// Unused
						}
						else
						{ // Assume a line.
							CLine NewLine;

							aint nParsed = -1;
							(CSymStr::CParse("{nfh} {nfh} {} {}") 
									>> NewLine.m_Address
									>> NewLine.m_Size
									>> NewLine.m_Line
									>> NewLine.m_File
									).f_Parse(WholeLine, nParsed);

							if (nParsed == 4)
							{
								if (iCurFunc != -1)
								{
									mp_lFunctions[iCurFunc].m_lLines.f_Insert(fg_Move(NewLine));
								}
								else
								{
									lErrors.f_Insert(CSymStr::CFormat("Invalid LINE outside of function at line # {}") << iLine);
								}
							}
							else
							{
								lErrors.f_Insert(CSymStr::CFormat("Invalid LINE line at line # {}") << iLine);
							}

						}

						++iLine;
					}
				}
				catch(NMib::NFile::CExceptionFile& _Ex)
				{
					DMibTrace("LoadError: {}", _Ex.f_GetErrorStr());
					f_Clear();
					return false;
				}

				// Is this required?
				mp_lFiles.f_Sort(CFileSorter());
				mp_lFunctions.f_Sort(CFunctionSorter());
				CLineSorter LineSorter;
				for (auto FIter = mp_lFunctions.f_GetIterator()
					;FIter
					;++FIter)
				{
					(*FIter).m_lLines.f_Sort(LineSorter);
				}
				
				return true;
			}

			void CSymbols::f_Clear()
			{
				mp_lFiles.f_Clear();
				mp_lFunctions.f_Clear();
			}


			bint CSymbols::f_Lookup(mint _Address, CAddressInfo& _oInfo)
			{
				{
					mach_header_64 const* pHeader = (mach_header_64 const*)_dyld_get_image_header(0);

					if (!pHeader)
						return false;

					unsigned long Slide = _dyld_get_image_vmaddr_slide(0);

					struct load_command const* pCmd = reinterpret_cast<struct load_command const*>(pHeader + 1);

					for (unsigned int iCmd = 0
						;iCmd < pHeader->ncmds
						;++iCmd)
					{
						struct segment_command_64 const* pSegment = reinterpret_cast<struct segment_command_64 const*>(pCmd);

						if (!strcmp(pSegment->segname, "__TEXT"))
						{
							_Address -= (pSegment->vmaddr + Slide);
							break;
						}

						pCmd = reinterpret_cast<struct load_command*>( (char*)pCmd + pCmd->cmdsize );
					}
				}

				CFunctionSorter FunctionSorter;
				CLineSorter LineSorter;

				aint iFoundFunc = fg_BinarySearchLowerBound(mp_lFunctions, FunctionSorter, _Address);

				if (iFoundFunc == -1 || iFoundFunc >= mp_lFunctions.f_GetLen())
					return false;

				CFunction const& Func = mp_lFunctions[iFoundFunc];

				if (	_Address >= Func.m_Address
					&&	_Address < (Func.m_Address + Func.m_Size))
				{
					_oInfo.m_Address = _Address;
					_oInfo.m_Function = Func.m_Name;
					_oInfo.m_File = CSymStr();
					_oInfo.m_Line = 0;

					aint iFoundLine = fg_BinarySearchLowerBound(Func.m_lLines, LineSorter, _Address);
					if (iFoundLine != -1 && iFoundLine <= Func.m_lLines.f_GetLen())
					{
						CLine const& Line = Func.m_lLines[iFoundLine];
						if (	_Address >= Line.m_Address
							&&	_Address <= (Line.m_Address + Line.m_Size) )
						{
							_oInfo.m_Line = Line.m_Line;

							CFileSorter FileSorter;
							aint iFile = mp_lFiles.f_BinarySearch(FileSorter, Line.m_File);
							if (iFile != -1)
								_oInfo.m_File = mp_lFiles[iFile].m_Name;
							else
								_oInfo.m_File = CSymStr("<Unknown>");
						}
					}

					return true;
				}
				else
				{
					return false;
				}
			}
	*/
		}
	}
}
