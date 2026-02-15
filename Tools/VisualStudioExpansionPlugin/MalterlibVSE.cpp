// Copyright © 2015 Hansoft AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <tchar.h>

#include <Mib/Core/Core>

#include "custview.h"

#include "MalterlibVSE.h"

// Helper routine that converts a system time into ASCII


template <typename t_CStrType>
HRESULT WINAPI VSE_Str(uint64 dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved, bool _bDecodeAddress)
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}

	try
	{
		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000 || !_bDecodeAddress)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		uint32 Processor = pHelper->GetProcessorType(pHelper);
		bool b64Bit = false;
		if (Processor == 2)
			b64Bit = true;

		ch8 const *pPrepend = "? ";
		if (sizeof(t_CStrType::CChar) == 1)
			pPrepend = "a8 ";
		else if (sizeof(t_CStrType::CChar) == 2)
			pPrepend = "a16 ";
		else if (sizeof(t_CStrType::CChar) == 4)
			pPrepend = "a32 ";

		if (b64Bit)
		{
			uint64 String = 0;
			uint32 nGot = 0;

			// read system time from debuggee memory space
			if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(String), &String, &nGot)!=S_OK)
			{
				fg_StrCopy(pResult, (CStr::CFormat("PtrFail(0x{nfh,sf0,sj16}, {})") << Address << sizeof(String)).f_GetStr());
				return S_OK;
			}
			if (nGot!=sizeof(String))
			{
				fg_StrCopy(pResult, "nGot!=sizeof(String) failed");
				return S_OK;
			}

			uint64 Data = (uint64)String;

			{
				if (Data)
				{
					class CTempData
					{
					public:
						int64 m_Ref;
						uint64 m_Len;
						uint64 m_StrLen:sizeof(uint64)*8-2;
						// TODO(Str): Fix this
						uint64 m_Type:2;
					};
					CTempData StrData;
					StrData.m_Ref = 0;
					StrData.m_Len = 0;
					StrData.m_StrLen = 0;
					StrData.m_Type = 0;
					if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data, sizeof(StrData), &StrData, &nGot)!=S_OK)
					{
						fg_StrCopy(pResult, (CStr::CFormat("StrFail(0x{nfh,sf0,sj16}, {})") << Data << sizeof(StrData)).f_GetStr());
						return S_OK;
					}
					if (nGot!=sizeof(StrData))
					{
						fg_StrCopy(pResult, "nGot!=sizeof(StrData) failed");
						return S_OK;
					}
					if (StrData.m_Len < StrData.m_StrLen)
					{
						fg_StrCopy(pResult, "StrData.m_Len<StrData.m_StrLen failed");
						return S_OK;
					}

					t_CStrType Temp;
					int Len = fg_Max(fg_Min((int)StrData.m_Len, 1000), 0) * sizeof(t_CStrType::CChar);
					t_CStrType::CChar *pStr = Temp.f_GetStr(Len);
					if (Len)
					{
						if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data + sizeof(CTempData), Len, pStr, &nGot)!=S_OK)
						{
							fg_StrCopy(pResult, (CStr::CFormat("DataFail(0x{nfh,sf0,sj16}, {})") << (Data + sizeof(CTempData)) << Len).f_GetStr());
							return S_OK;
						}
						if (nGot!=Len)
						{
							fg_StrCopy(pResult, "nGot!=Len failed");
							return S_OK;
						}
					}
					pStr[Len/sizeof(t_CStrType::CChar)] = 0;
					if (StrData.m_Type > EStrType_UTF)
					{
						fg_StrCopy(pResult, "Invalid String Type");
					}
					else
					{
						if (StrData.m_Type == EStrType_UTF)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "utf8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "utf6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "utf32 ";
						}
						else if (StrData.m_Type == EStrType_Unicode)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "ch8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "ch6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "ch32 ";
						}
						Temp.f_SetType((EStrType)StrData.m_Type);

						CStr Return = Temp;
						ch8 Bom[] = {(int8)uint8(0xEF), (int8)uint8(0xBB), (int8)uint8(0xBF), 0};
						ch8 *pDest = pResult;
						//pDest = fg_StrCopy(pDest, Bom);
						pDest = fg_StrCopy(pDest, pPrepend);
						pDest = fg_StrCopy(pDest, Return.f_GetStr(), max - 1 - (pDest - pResult));
						*pDest = 0;
						pResult[max - 1] = 0;
					}
				}
				else
				{
					fg_StrCopy(pResult, "\"\"");
		//			*pResult = 0;
				}
			}
		}
		else
		{

			uint32 String = 0;
			uint32 nGot = 0;

			// read system time from debuggee memory space
			if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(String), &String, &nGot)!=S_OK)
			{
				fg_StrCopy(pResult, (CStr::CFormat("PtrFail(0x{nfh,sf0,sj8}, {})") << Address << sizeof(String)).f_GetStr());
				return S_OK;
			}
			if (nGot!=sizeof(String))
			{
				fg_StrCopy(pResult, "nGot!=sizeof(String) failed");
				return S_OK;
			}

			uint32 Data = (uint32)String;

			{
				if (Data)
				{
					class CTempData
					{
					public:
						int32 m_Ref;
						uint32 m_Len;
						uint32 m_StrLen:sizeof(uint32)*8-2;
						uint32 m_Type:2;
					};
					CTempData StrData;
					StrData.m_Ref = 0;
					StrData.m_Len = 0;
					StrData.m_StrLen = 0;

					if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data, sizeof(StrData), &StrData, &nGot)!=S_OK)
					{
						fg_StrCopy(pResult, (CStr::CFormat("StrFail(0x{nfh,sf0,sj8}, {})") << Data << sizeof(StrData)).f_GetStr());
						return S_OK;
					}
					if (nGot!=sizeof(StrData))
					{
						fg_StrCopy(pResult, "nGot!=sizeof(StrData) failed");
						return S_OK;
					}
					if (StrData.m_Len < StrData.m_StrLen)
					{
						fg_StrCopy(pResult, "StrData.m_Len<StrData.m_StrLen failed");
						return S_OK;
					}
					t_CStrType Temp;
					int Len = fg_Max(fg_Min((int)StrData.m_Len, 1000), 0) * sizeof(t_CStrType::CChar);
					t_CStrType::CChar *pStr = Temp.f_GetStr(Len);
					if (Len)
					{
						if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data + sizeof(CTempData), Len, pStr, &nGot)!=S_OK)
						{
							fg_StrCopy(pResult, (CStr::CFormat("DataFail(0x{nfh,sf0,sj8}, {})") << (Data + sizeof(CTempData)) << Len).f_GetStr());
							return S_OK;
						}
						if (nGot!=Len)
						{
							fg_StrCopy(pResult, "nGot!=Len failed");
							return S_OK;
						}
					}
					pStr[Len/sizeof(t_CStrType::CChar)] = 0;

					if (StrData.m_Type > EStrType_UTF)
					{
						fg_StrCopy(pResult, "Invalid String Type");
					}
					else
					{
						if (StrData.m_Type == EStrType_UTF)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "utf8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "utf6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "utf32 ";
						}
						else if (StrData.m_Type == EStrType_Unicode)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "ch8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "ch6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "ch32 ";
						}
						Temp.f_SetType((EStrType)StrData.m_Type);
						CStr Return = Temp;
						ch8 Bom[] = {(int8)uint8(0xEF), (int8)uint8(0xBB), (int8)uint8(0xBF), 0};
						ch8 *pDest = pResult;
						//pDest = fg_StrCopy(pDest, Bom);
						pDest = fg_StrCopy(pDest, pPrepend);
						pDest = fg_StrCopy(pDest, Return.f_GetStr(), max - 1 - (pDest - pResult));
						*pDest = 0;
						pResult[max - 1] = 0;
					}
				}
				else
				{
					fg_StrCopy(pResult, "\"\"");
		//			*pResult = 0;
				}
			}
		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		return E_FAIL;
	}
}

ADDIN_API HRESULT WINAPI VSE_CStr(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	return VSE_Str<CStr>(dwAddress, pHelper, nBase, bUniStrings, pResult, max, reserved, true);
}

ADDIN_API HRESULT WINAPI VSE_CWStr(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	return VSE_Str<CWStr>(dwAddress, pHelper, nBase, bUniStrings, pResult, max, reserved, true);
}

ADDIN_API HRESULT WINAPI VSE_CUStr(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	return VSE_Str<CUStr>(dwAddress, pHelper, nBase, bUniStrings, pResult, max, reserved, true);
}

template <typename t_CStrType>
HRESULT WINAPI VSE_FStr(uint64 dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved, bool _bDecodeAddress)
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}

	try
	{
		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000 || !_bDecodeAddress)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		ch8 const *pPrepend = "? ";
		if (sizeof(t_CStrType::CChar) == 1)
			pPrepend = "a8 ";
		else if (sizeof(t_CStrType::CChar) == 2)
			pPrepend = "a16 ";
		else if (sizeof(t_CStrType::CChar) == 4)
			pPrepend = "a32 ";

		uint32 Processor = pHelper->GetProcessorType(pHelper);
		bool b64Bit = false;
		if (Processor == 2)
			b64Bit = true;

		if (b64Bit)
		{
			uint64 Data = (uint64)Address;
			uint32 nGot = 0;

			{
				if (Data)
				{
					class CTempData
					{
					public:
						uint64 m_Len:sizeof(uint64)*8-2;
						uint64 m_Type:2;
					};
					CTempData StrData;
					StrData.m_Len = 0;
					StrData.m_Type = 0;
					if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data, sizeof(StrData), &StrData, &nGot)!=S_OK)
					{
						fg_StrCopy(pResult, (CStr::CFormat("StrFail(0x{nfh,sf0,sj16}, {})") << Data << sizeof(StrData)).f_GetStr());
						return S_OK;
					}
					if (nGot!=sizeof(StrData))
					{
						fg_StrCopy(pResult, "nGot!=sizeof(StrData) failed");
						return S_OK;
					}

					t_CStrType Temp;
					int Len = fg_Max(fg_Min((int)StrData.m_Len, 1000), 0) * sizeof(t_CStrType::CChar);
					t_CStrType::CChar *pStr = Temp.f_GetStr(Len);
					if (Len)
					{
						if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data + sizeof(CTempData), Len, pStr, &nGot)!=S_OK)
						{
							fg_StrCopy(pResult, (CStr::CFormat("DataFail(0x{nfh,sf0,sj16}, {})") << (Data + sizeof(CTempData)) << Len).f_GetStr());
							return S_OK;
						}
						if (nGot!=Len)
						{
							fg_StrCopy(pResult, "nGot!=Len failed");
							return S_OK;
						}
					}
					pStr[Len/sizeof(t_CStrType::CChar)] = 0;
					if (StrData.m_Type > EStrType_UTF)
					{
						fg_StrCopy(pResult, "Invalid String Type");
					}
					else
					{
						if (StrData.m_Type == EStrType_UTF)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "utf8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "utf6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "utf32 ";
						}
						else if (StrData.m_Type == EStrType_Unicode)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "ch8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "ch6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "ch32 ";
						}

						Temp.f_SetType((EStrType)StrData.m_Type);
						CStr Return = Temp;
						ch8 Bom[] = {(int8)uint8(0xEF), (int8)uint8(0xBB), (int8)uint8(0xBF), 0};
						ch8 *pDest = pResult;
						//pDest = fg_StrCopy(pDest, Bom);
						pDest = fg_StrCopy(pDest, pPrepend);
						pDest = fg_StrCopy(pDest, Return.f_GetStr(), max - 1 - (pDest - pResult));
						*pDest = 0;
						pResult[max - 1] = 0;
					}
				}
				else
				{
					fg_StrCopy(pResult, "\"\"");
		//			*pResult = 0;
				}
			}
		}
		else
		{
			uint32 Data = (uint32)Address;
			uint32 nGot = 0;

			{
				if (Data)
				{
					class CTempData
					{
					public:
						uint32 m_Len:sizeof(uint32)*8-2;
						uint32 m_Type:2;
					};
					CTempData StrData;
					StrData.m_Len = 0;
					StrData.m_Type = 0;

					if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data, sizeof(StrData), &StrData, &nGot)!=S_OK)
					{
						fg_StrCopy(pResult, (CStr::CFormat("StrFail(0x{nfh,sf0,sj8}, {})") << Data << sizeof(StrData)).f_GetStr());
						return S_OK;
					}
					if (nGot!=sizeof(StrData))
					{
						fg_StrCopy(pResult, "nGot!=sizeof(StrData) failed");
						return S_OK;
					}
					t_CStrType Temp;
					int Len = fg_Max(fg_Min((int)StrData.m_Len, 1000), 0) * sizeof(t_CStrType::CChar);
					t_CStrType::CChar *pStr = Temp.f_GetStr(Len);
					if (Len)
					{
						if (pHelper->ReadDebuggeeMemoryEx(pHelper, Data + sizeof(CTempData), Len, pStr, &nGot)!=S_OK)
						{
							fg_StrCopy(pResult, (CStr::CFormat("DataFail(0x{nfh,sf0,sj8}, {})") << (Data + sizeof(CTempData)) << Len).f_GetStr());
							return S_OK;
						}
						if (nGot!=Len)
						{
							fg_StrCopy(pResult, "nGot!=Len failed");
							return S_OK;
						}
					}
					pStr[Len/sizeof(t_CStrType::CChar)] = 0;

					if (StrData.m_Type > EStrType_UTF)
					{
						fg_StrCopy(pResult, "Invalid String Type");
					}
					else
					{
						if (StrData.m_Type == EStrType_UTF)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "utf8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "utf6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "utf32 ";
						}
						else if (StrData.m_Type == EStrType_Unicode)
						{
							if (sizeof(t_CStrType::CChar) == 1)
								pPrepend = "ch8 ";
							else if (sizeof(t_CStrType::CChar) == 2)
								pPrepend = "ch6 ";
							else if (sizeof(t_CStrType::CChar) == 4)
								pPrepend = "ch32 ";
						}

						Temp.f_SetType((EStrType)StrData.m_Type);
						CStr Return = Temp;
						ch8 Bom[] = {(int8)uint8(0xEF), (int8)uint8(0xBB), (int8)uint8(0xBF), 0};
						ch8 *pDest = pResult;
						//pDest = fg_StrCopy(pDest, Bom);
						pDest = fg_StrCopy(pDest, pPrepend);
						pDest = fg_StrCopy(pDest, Return.f_GetStr(), max - 1 - (pDest - pResult));
						*pDest = 0;
						pResult[max - 1] = 0;
					}
				}
				else
				{
					fg_StrCopy(pResult, "\"\"");
		//			*pResult = 0;
				}
			}
		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		return E_FAIL;
	}
}

ADDIN_API HRESULT WINAPI VSE_CFUStr(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	return VSE_FStr<CUStr>(dwAddress, pHelper, nBase, bUniStrings, pResult, max, reserved, true);
}

ADDIN_API HRESULT WINAPI VSE_CFWStr(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	return VSE_FStr<CWStr>(dwAddress, pHelper, nBase, bUniStrings, pResult, max, reserved, true);
}

ADDIN_API HRESULT WINAPI VSE_CFStr(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	return VSE_FStr<CStr>(dwAddress, pHelper, nBase, bUniStrings, pResult, max, reserved, true);
}

ADDIN_API HRESULT WINAPI VSE_CMStr(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}

	try
	{
		class CMStren
		{
		public:
			union
			{
				EMStr_Type m_Type;
				uint32 m_Type_uint32;
			};
		};
		CMStren String;
		uint32 nGot;

		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		uint32 Processor = pHelper->GetProcessorType(pHelper);
		uint32 Mul64 = 1;
		if (Processor == 2)
			Mul64 = 2;

		// read system time from debuggee memory space
		if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(String), &String, &nGot)!=S_OK)
		{
			return E_FAIL;
		}

		if (nGot!=sizeof(String))
		{
			return E_FAIL;
		}

		{
			fg_StrCopy(pResult, "");
			switch (String.m_Type)
			{
			case EMStr_Type_CStr:
				{
					return VSE_Str<CStr>(Address+sizeof(uint32)*Mul64, pHelper, nBase, bUniStrings, pResult, max, reserved, false);
				}
				break;
			case EMStr_Type_CWStr:
				{
					return VSE_Str<CWStr>(Address+sizeof(uint32)*Mul64, pHelper, nBase, bUniStrings, pResult, max, reserved, false);
				}
				break;
			case EMStr_Type_CUStr:
				{
					return VSE_Str<CUStr>(Address+sizeof(uint32)*Mul64, pHelper, nBase, bUniStrings, pResult, max, reserved, false);
				}
				break;
			case EMStr_Type_None:
				break;
			default:
				fg_StrCopy(pResult, "Invalid Type");
				break;
			}

		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		fg_StrCopy(pResult, "Exception");
//		return E_FAIL;
	}
}


ADDIN_API HRESULT WINAPI VSE_CTime(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}

	try
	{
		CTime Time;
		uint32 nGot = 0;

		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		// read system time from debuggee memory space
		if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(Time), &Time, &nGot)!=S_OK)
		{
			return E_FAIL;
		}
		if (nGot!=sizeof(Time))
		{
			return E_FAIL;
		}

		{
			if (Time.f_IsValid())
			{
				const ch8 *Days[] = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"};
				CTimeConvert::CDateTime DateTime;
				CTimeConvert(Time).f_ExtractDateTime(DateTime);
				CTimeConvert_ISOWeek::CDateTime DateTime2;
				CTimeConvert_ISOWeek(Time).f_ExtractDateTime(DateTime2);

				CTimeConvert::CDateTime LocalDateTime;
				CTimeConvert(Time.f_ToLocal()).f_ExtractDateTime(LocalDateTime);
				CTimeConvert_ISOWeek::CDateTime LocalDateTime2;
				CTimeConvert_ISOWeek(Time.f_ToLocal()).f_ExtractDateTime(LocalDateTime2);

				CFStr1024 Return;
				Return = CFStr1024::CFormat
					(
						"{}-{sj2,sf0}-{sj2,sf0} {sj2,sf0}:{sj2,sf0}:{sj2,sf0}.{sj3,sf0} | {}-W{sj2,sf0} | {} | DayOfYear: {} | IsLeapYear: {}\r\n"
						"{}-{sj2,sf0}-{sj2,sf0} {sj2,sf0}:{sj2,sf0}:{sj2,sf0}.{sj3,sf0} | {}-W{sj2,sf0} | {} | DayOfYear: {} | IsLeapYear: {}"
					)
					<< DateTime.m_Year << DateTime.m_Month << DateTime.m_DayOfMonth
					<< DateTime.m_Hour << DateTime.m_Minute << DateTime.m_Second << (DateTime.m_Fraction * 1000.0).f_ToInt()
					<< DateTime2.m_Year << DateTime2.m_Week << Days[DateTime.m_DayOfWeek]
					<< DateTime.m_DayOfYear << DateTime.m_bIsLeapYear
					<< LocalDateTime.m_Year << LocalDateTime.m_Month << LocalDateTime.m_DayOfMonth
					<< LocalDateTime.m_Hour << LocalDateTime.m_Minute << LocalDateTime.m_Second << (LocalDateTime.m_Fraction * 1000.0).f_ToInt()
					<< LocalDateTime2.m_Year << LocalDateTime2.m_Week << Days[LocalDateTime.m_DayOfWeek]
					<< LocalDateTime.m_DayOfYear << LocalDateTime.m_bIsLeapYear
					;

				fg_StrCopy(pResult, Return.f_GetStr(), max - 1);
				pResult[max - 1] = 0;
			}
			else
			{
				fg_StrCopy(pResult, "Invalid Date");
			}
		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		return E_FAIL;
	}
}

ADDIN_API HRESULT WINAPI VSE_CTimeSpan(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}
	try
	{
		CTimeSpan Time;
		uint32 nGot = 0;

		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		// read system time from debuggee memory space
		if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(Time), &Time, &nGot)!=S_OK)
		{
			return E_FAIL;
		}
		if (nGot!=sizeof(Time))
		{
			return E_FAIL;
		}

		{
			if (Time.f_IsValid())
			{
				CFStr1024 Return;
				Return = CFStr1024::CFormat("{} Weeks | {} Days | {} Hours | {} Minutes | {}.{sj2,sf0} Seconds | {} Hours {} Minutes {}.{sj2,sf0} Seconds")
					<< CTimeSpanConvert(Time).f_GetWeeks() << CTimeSpanConvert(Time).f_GetDays()
					<< CTimeSpanConvert(Time).f_GetHours() << CTimeSpanConvert(Time).f_GetMinutes()
					<< CTimeSpanConvert(Time).f_GetSeconds() << (CTimeSpanConvert(Time).f_GetFraction() * 100.0).f_ToInt()
					<< CTimeSpanConvert(Time).f_GetHours() << CTimeSpanConvert(Time).f_GetMinuteOfHour()
					<< CTimeSpanConvert(Time).f_GetSecondOfMinute() << (CTimeSpanConvert(Time).f_GetFraction() * 100.0).f_ToInt()
					;

				fg_StrCopy(pResult, Return.f_GetStr(), max - 1);
				pResult[max - 1] = 0;
			}
			else
			{
				fg_StrCopy(pResult, "Invalid Date");
			}
		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		return E_FAIL;
	}
}


ADDIN_API HRESULT WINAPI VSE_fp32(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}
	try
	{
		fp32 Variable;
		uint32 nGot = 0;

		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		// read system time from debuggee memory space
		if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(Variable), &Variable, &nGot)!=S_OK)
		{
			return E_FAIL;
		}
		if (nGot!=sizeof(Variable))
		{
			return E_FAIL;
		}

		{
			fg_StrCopy(pResult, (CFStr1024::CFormat("{fsi,fsd,fsn}") << Variable).f_GetStr().f_GetStr(), max - 1);
			pResult[max - 1] = 0;
		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		return E_FAIL;
	}
}

ADDIN_API HRESULT WINAPI VSE_fp64(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}
	try
	{
		fp64 Variable;
		uint32 nGot = 0;

		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		// read system time from debuggee memory space
		if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(Variable), &Variable, &nGot)!=S_OK)
		{
			return E_FAIL;
		}
		if (nGot!=sizeof(Variable))
		{
			return E_FAIL;
		}

		{
			fg_StrCopy(pResult, (CFStr1024::CFormat("{fsi,fsd,fsn}") << Variable).f_GetStr().f_GetStr(), max - 1);
			pResult[max - 1] = 0;
		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		return E_FAIL;
	}
}

ADDIN_API HRESULT WINAPI VSE_fp128(DWORD dwAddress, DEBUGHELPER *pHelper, int nBase, BOOL bUniStrings, char *pResult, size_t max, DWORD reserved )
{
	if (bUniStrings)
	{
		fg_StrCopy(pResult, "Does not support unicode strings");
		return S_OK;
	}
	try
	{
		fp128 Variable;
		uint32 nGot = 0;

		DWORDLONG Address = 0;
		if (pHelper->dwVersion<0x20000)
		{
			// Visual C++ 6.0 version
			Address = dwAddress;
		}
		else
		{
			Address = pHelper->GetRealAddress(pHelper);
		}

		// read system time from debuggee memory space
		if (pHelper->ReadDebuggeeMemoryEx(pHelper, Address, sizeof(Variable), &Variable, &nGot)!=S_OK)
		{
			return E_FAIL;
		}
		if (nGot!=sizeof(Variable))
		{
			return E_FAIL;
		}

		{
			fg_StrCopy(pResult, (CFStr1024::CFormat("{fsi,fsd,fsn}") << Variable).f_GetStr().f_GetStr(), max - 1);
			pResult[max - 1] = 0;
		}

		return S_OK;
	}
	catch (...)
	{
		fg_StrCopy(pResult, "Exception");
		return S_OK;
//		return E_FAIL;
	}
}



DMibAppNoClass;
DMibPMain;
