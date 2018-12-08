// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

using namespace NMib;

#ifdef DPlatformFamily_OSX
	#include <Mib/Debug/PlatformSpecific/OSXSymbols>
#elif defined(DPlatformFamily_Linux)
	#include <dlfcn.h>
#endif

inline_never void *fg_GetInstructionPointer()
{
#if defined(DCompiler_clang)
	return __builtin_return_address(0);
#elif defined(DCompiler_MSVC)
	return _ReturnAddress();
#else
#error "Implement this"
#endif
}

inline_never void* fg_LookupThisFunc()
{
	volatile static int Test = DMibPLine;
	NSys::fg_Compiler_MakeActive(0, &Test);
	void * volatile pRet = fg_GetInstructionPointer();
	return pRet;
}

inline_never mint fg_AcquireStackTraceFromHere(CMibCodeAddress* _pStack, mint _MaxDepth)
{
	volatile static int Test = DMibPLine;
	NSys::fg_Compiler_MakeActive(0, &Test);
	volatile mint Value = NMib::NSys::fg_System_GetStackTrace(_pStack, _MaxDepth);
	return Value;
}



#include "Test_Malterlib_Debug.h"
#include <Mib/Storage/Reference>
#include <Mib/String/Mixed>
#include <Mib/Encoding/JSON>
#include <Mib/Encoding/EJSON>

class CDebug_Tests : public NMib::NTest::CTest
{
public:

	inline_never static void* fs_LookupThisStaticMemberFunc()
	{
		volatile static int Test = DMibPLine;
		NSys::fg_Compiler_MakeActive(0, &Test);
		void * volatile pRet = fg_GetInstructionPointer();
		return pRet;
	}
	
	void f_DoTests()
	{
#ifdef DPlatformFamily_Linux
		ETest ExpectLinuxFail = ETest_ExpectFail;
#else
		ETest ExpectLinuxFail = ETest_Fail;
#endif
		DMibTestSuite("StackTrace")
		{
			//DMibTrace("&fg_AcquireStackTraceFromHere: {}\n", (void*)&fg_AcquireStackTraceFromHere );

			CMibCodeAddress Stack[64];
			mint nStack = fg_AcquireStackTraceFromHere(Stack, 64);

			bool bFound = false;

			for (mint i = 0; i < nStack; ++i)
			{
				CStackTraceInfo *pInfo = NSys::fg_Debug_AquireStackTraceInfo(Stack[i]);
				if (pInfo)
				{
//					if (pInfo->m_pFunctionName)
//						DMibTrace("FuncName: \"{}\"\n", pInfo->m_pFunctionName);
//					if (pInfo->m_pSourceFileName)
//						DMibTrace("   FileName: \"{}\"\n", pInfo->m_pSourceFileName);
//					DMibTrace("   FileLine: {}\n", pInfo->m_SourceLine);
					if ( pInfo->m_pFunctionName && NStr::fg_StrFindNoCase(pInfo->m_pFunctionName, "fg_AcquireStackTraceFromHere") != -1)
					{
						if ( pInfo->m_pSourceFileName && *pInfo->m_pSourceFileName)
						{
							if (NStr::fg_StrFindNoCase(pInfo->m_pSourceFileName, "Test_Malterlib_Debug.cpp") != -1)
								bFound = true;
						}
						else
							bFound = true;
					}
					NSys::fg_Debug_ReleaseStackTraceInfo(pInfo);
					if (bFound)
						break;
				}
			}

			DMibTest(DMibExpr(bFound) == DMibExpr(true))(ExpectLinuxFail);
		};

		DMibTestSuite("StackTraceInfo")
		{
			{
				CMibCodeAddress volatile pLookup = (CMibCodeAddress)fg_LookupThisFunc();
				CStackTraceInfo *pInfo = NSys::fg_Debug_AquireStackTraceInfo(pLookup);

				DMibTest(DMibExpr(pInfo) != DMibExpr(nullptr))(ETest_FailAndStop);

				if (pInfo)
				{
					DMibTest(DMibExpr((void*)pInfo->m_pFunctionName) != DMibExpr(nullptr));
					if ( pInfo->m_pFunctionName)
					{
						DMibTest(DMibExpr(NStr::fg_StrFindNoCase(pInfo->m_pFunctionName, "fg_LookupThisFunc")) != DMibExpr(-1))(ExpectLinuxFail);
					}

#ifndef DPlatformFamily_OSX
					DMibTest(DMibExpr((void*)pInfo->m_pSourceFileName) != DMibExpr(nullptr));
					if ( pInfo->m_pSourceFileName)
					{
						DMibTest(DMibExpr(NStr::fg_StrFindNoCase(pInfo->m_pSourceFileName, "Test_Malterlib_Debug.cpp")) != DMibExpr(-1))(ExpectLinuxFail);
					}
#endif

					NSys::fg_Debug_ReleaseStackTraceInfo(pInfo);
				}
			}
		};
#if defined(DPlatformFamily_Linux)
		DMibTestSuite("StackTraceInfoExternal")
		{
			{
				CStackTraceInfo *pInfo = NSys::fg_Debug_AquireStackTraceInfo((CMibCodeAddress)&dlopen);

				DMibTest(DMibExpr(pInfo) != DMibExpr(nullptr))(ETest_FailAndStop);

				if (pInfo)
				{
//					DMibTrace("pInfo->m_pFunctionName: {}\n", (pInfo->m_pFunctionName ? pInfo->m_pFunctionName : "") );
//					DMibTrace("pInfo->m_pSourceFileName: {}\n", (pInfo->m_pSourceFileName ? pInfo->m_pSourceFileName : "") );
//					DMibTrace("pInfo->m_SourceLine; {}\n", pInfo->m_SourceLine);

					DMibTest(DMibExpr((void*)pInfo->m_pFunctionName) != DMibExpr(nullptr));
					if ( pInfo->m_pFunctionName)
					{
						DMibTest(DMibExpr(NStr::fg_StrFindNoCase(pInfo->m_pFunctionName, "dlopen")) != DMibExpr(-1));
					}

					DMibTest(DMibExpr((void*)pInfo->m_pModuleName) != DMibExpr(nullptr));
					if ( pInfo->m_pModuleName)
					{
						DMibTest(DMibExpr(NStr::fg_StrFindNoCase(pInfo->m_pModuleName, "libdl")) != DMibExpr(-1));
					}

					NSys::fg_Debug_ReleaseStackTraceInfo(pInfo);
				}
			}
		};
#endif
		DMibTestSuite("StackTraceInfo_StaticMember")
		{	
			{
				CStackTraceInfo *pInfo = NSys::fg_Debug_AquireStackTraceInfo((CMibCodeAddress)fs_LookupThisStaticMemberFunc());
				//DMibTrace("&f_LookupThisStaticMemberFunc: {}\n", (void*)&f_LookupThisStaticMemberFunc );

				DMibTest(DMibExpr(pInfo) != DMibExpr(nullptr))(ETest_FailAndStop);

				if (pInfo)
				{
//					DMibTrace("pInfo->m_pFunctionName: {}\n", pInfo->m_pFunctionName);
//					DMibTrace("pInfo->m_pSourceFileName: {}\n", (void*)pInfo->m_pSourceFileName);

					DMibTest(DMibExpr((void*)pInfo->m_pFunctionName) != DMibExpr(nullptr));
					if (pInfo->m_pFunctionName)
						DMibTest(DMibExpr(NStr::fg_StrFindNoCase(pInfo->m_pFunctionName, "fs_LookupThisStaticMemberFunc")) != DMibExpr(-1))(ExpectLinuxFail);

#ifndef DPlatformFamily_OSX
					DMibTest(DMibExpr((void*)pInfo->m_pSourceFileName) != DMibExpr(nullptr));
					if ( pInfo->m_pSourceFileName)
					{
						DMibTest(DMibExpr(NStr::fg_StrFindNoCase(pInfo->m_pSourceFileName, "Test_Malterlib_Debug.cpp")) != DMibExpr(-1))(ExpectLinuxFail);
					}
#endif

					NSys::fg_Debug_ReleaseStackTraceInfo(pInfo);
				}
			}
		};
//*/
	#if defined(DPlatformFamily_OSX) && 0
		DMibTestSuite("OSXSymbols")
		{
			auto &Symbols = NMib::NDebug::NPlatform::fg_GetSymbols();

//			Symbols.f_SetSymbolsFile("/CompiledFiles/Build/Products/Debug Inlined 10.7/Exe_Certifier.symbols");

			NMib::NDebug::NPlatform::CAddressInfo Info;
			bint bLookup = Symbols.f_Lookup((mint)&fg_LookupThisFunc, Info);

			DMibTest(DMibExpr(bLookup) == DMibExpr(true));
			
			DMibTest(DMibExpr(Info.m_File.f_Find("Test_Malterlib_Debug.cpp")) != DMibExpr(-1));
			DMibTest(DMibExpr(Info.m_Function.f_Find("fg_LookupThisFunc()")) != DMibExpr(-1));
			
			/*
			DMibTrace("File: {}\nLine: {}\nFunc: {}\n", 
						Info.m_File
					<<	Info.m_Line

					<<	Info.m_Function);
		     */
		};
	#endif

		DMibTestSuite("Visualizers")
		{
			using namespace NMib::NStr;
			using namespace NMib::NContainer;
			using namespace NMib::NIntrusive;
			using namespace NMib::NAtomic;
			using namespace NMib::NStorage;
			using namespace NMib;
			
			CStr Str0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CWStr Str1(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			CUStr Str2(str_utf32("CUStr 実際にあっ 24bit:𠀀"));
			
			ch8 RawStr0[256];
			ch16 RawStr1[256];
			ch32 RawStr2[256];
			
			ch8 const *pRawStr0 = Str0;
			ch16 const *pRawStr1 = Str1;
			ch32 const *pRawStr2 = Str2;
						
			NStr::fg_StrCopy(RawStr0, pRawStr0);
			NStr::fg_StrCopy(RawStr1, pRawStr1);
			NStr::fg_StrCopy(RawStr2, pRawStr2);

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> Str0_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> Str1_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> Str2_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			CStrAggregate &Str3 = Str0;
			CWStrAggregate &Str4 = Str1;
			CUStrAggregate &Str5 = Str2;

			TCStrAggregate<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> &Str3_0 = Str0_0;
			TCStrAggregate<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> &Str4_0 = Str1_0;
			TCStrAggregate<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> &Str5_0 = Str2_0;
			
			CFStr128 Str6(str_utf8("CFStr128 実際にあっ 24bit:𠀀"));
			CFStr256 Str7(str_utf8("CFStr256 実際にあっ 24bit:𠀀"));
			CFWStr128 Str8(str_utf16("CFWStr128 実際にあっ 24bit:𠀀"));
			CFWStr256 Str9(str_utf16("CFWStr256 実際にあっ 24bit:𠀀"));
			CFUStr128 Str10(str_utf16("CFUStr128 実際にあっ 24bit:𠀀"));
			CFUStr256 Str11(str_utf16("CFUStr256 実際にあっ 24bit:𠀀"));

			CFStrAggregate128 &Str6_0 = Str6;
			CFStrAggregate256 &Str7_0 = Str7;
			CFWStrAggregate128 &Str8_0 = Str8;
			CFWStrAggregate256 &Str9_0 = Str9;
			CFUStrAggregate128 &Str10_0 = Str10;
			CFUStrAggregate256 &Str11_0 = Str11;

			CStrVMem Str12(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CWStrVMem Str13(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			CUStrVMem Str14(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> Str12_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> Str13_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> Str14_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStrAggregate<CStrTraits_CStrVMem> &Str15 = Str12;
			TCStrAggregate<CStrTraits_CWStrVMem> &Str16 = Str13;
			TCStrAggregate<CStrTraits_CUStrVMem> &Str17 = Str14;

			TCStrAggregate<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> &Str15_0 = Str12_0;
			TCStrAggregate<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> &Str16_0 = Str13_0;
			TCStrAggregate<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> &Str17_0 = Str14_0;

			CStrSecure Str18(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CWStrSecure Str19(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			CUStrSecure Str20(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> Str18_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> Str19_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> Str20_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStrAggregate<CStrTraits_CStrSecure> &Str21 = Str18;
			TCStrAggregate<CStrTraits_CWStrSecure> &Str22 = Str19;
			TCStrAggregate<CStrTraits_CUStrSecure> &Str23 = Str20;

			TCStrAggregate<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> &Str21_0 = Str18_0;
			TCStrAggregate<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> &Str22_0 = Str19_0;
			TCStrAggregate<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> &Str23_0 = Str20_0;

			CStrNonTracked Str24(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CWStrNonTracked Str25(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			CUStrNonTracked Str26(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> Str24_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> Str25_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> Str26_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStrAggregate<CStrTraits_CStrNonTracked> &Str27 = Str24;
			TCStrAggregate<CStrTraits_CWStrNonTracked> &Str28 = Str25;
			TCStrAggregate<CStrTraits_CUStrNonTracked> &Str29 = Str26;

			TCStrAggregate<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> &Str27_0 = Str24_0;
			TCStrAggregate<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> &Str28_0 = Str25_0;
			TCStrAggregate<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> &Str29_0 = Str26_0;

			CStrPtr Str30; Str30.f_SetConstPtr(str_utf8("CStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf8("CStrPtr 実際にあっ 24bit:𠀀")));
			CWStrPtr Str31; Str31.f_SetConstPtr(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀")));
			CUStrPtr Str32; Str32.f_SetConstPtr(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀")));

			TCStr<TCStrTraitsPtr<ch8, EStrType_UTF>::CType> Str30_0; Str30_0.f_SetConstPtr(str_utf8("CStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf8("CStrPtr 実際にあっ 24bit:𠀀")));
			TCStr<TCStrTraitsPtr<ch16, EStrType_UTF>::CType> Str31_0; Str31_0.f_SetConstPtr(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀")));
			TCStr<TCStrTraitsPtr<ch32, EStrType_Unicode>::CType> Str32_0; Str32_0.f_SetConstPtr(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀")));
			
			TCStrAggregate<CStrTraitsPtr_CStr> &Str33 = Str30;
			TCStrAggregate<CStrTraitsPtr_CWStr> &Str34 = Str31;
			TCStrAggregate<CStrTraitsPtr_CUStr> &Str35 = Str32;

			TCStrAggregate<TCStrTraitsPtr<ch8, EStrType_UTF>::CType> &Str33_0 = Str30_0;
			TCStrAggregate<TCStrTraitsPtr<ch16, EStrType_UTF>::CType> &Str34_0 = Str31_0;
			TCStrAggregate<TCStrTraitsPtr<ch32, EStrType_Unicode>::CType> &Str35_0 = Str32_0;
			
			CMStrDeprecated MixedStr8(CStr(str_utf8("CStr")));
			CMStrDeprecated MixedStr16(CStr(str_utf8("CWStr 実際にあっ")));
			CMStrDeprecated MixedStr32(CStr(str_utf8("CUStr 実際にあっ 24bit:𠀀")));
			
			CAnsiStr AnsiStr;
			NMib::NSys::NStr::fg_SystemEncodeAnsiStr(CStr(str_utf8("CStr ÄäÅåÖ")), AnsiStr, '?');

			CStr UnicodeStr = CMStrDeprecated(CStr(str_utf8("CStr ÄäÅåÖ")));
			
			CFStr256 TestUTF8(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CFStr256 TestUnicode8 = UnicodeStr;
			CFStr256 TestAnsi8 = AnsiStr;

			CFWStr256 TestUTF16 = CWStr(str_utf16("CStr 実際にあっ 24bit:𠀀"));
			CFWStr256 TestUnicode16 = CMStrDeprecated(CWStr(str_utf16("CStr 実際にあっ")));

			CFUStr256 TestUnicode32 = CUStr(str_utf32("CStr 実際にあっ 24bit:𠀀"));
			
			TCVector<CTestClass> Vector;
			DMibListLinkDS_List(CTestClass, m_Link) IntrusiveList;
			TCLinkedList<int32> LinkedList;
			
			IntrusiveList.f_Insert(Vector.f_Insert(5));
			IntrusiveList.f_Insert(Vector.f_Insert(8));
			IntrusiveList.f_Insert(Vector.f_Insert(1));
			IntrusiveList.f_Insert(Vector.f_Insert(3));
			
			
			LinkedList.f_Insert(5);
			LinkedList.f_Insert(8);
			LinkedList.f_Insert(1);
			LinkedList.f_Insert(3);
			
			TCLinkedList<CTest2> LinkedListForTree;
			TCAVLTree<&CTest2::m_AVLLink, CTest2::CCompare> AVLTree;

			DMibListLinkS_List(CTest2, m_LinkSingle) IntrusiveSingleList;
			
			AVLTree.f_Insert(LinkedListForTree.f_Insert(fg_Construct(5)));
			IntrusiveSingleList.f_Insert(LinkedListForTree.f_GetLast());
			AVLTree.f_Insert(LinkedListForTree.f_Insert(fg_Construct(8)));
			IntrusiveSingleList.f_Insert(LinkedListForTree.f_GetLast());
			AVLTree.f_Insert(LinkedListForTree.f_Insert(fg_Construct(1)));
			IntrusiveSingleList.f_Insert(LinkedListForTree.f_GetLast());
			AVLTree.f_Insert(LinkedListForTree.f_Insert(fg_Construct(3)));
			IntrusiveSingleList.f_Insert(LinkedListForTree.f_GetLast());

			TCMap<int32, int32> Map;
			Map[5] = 5;
			Map[8] = 8;
			Map[1] = 1;
			Map[3] = 3;

			TCMap<int32> MapNoData;
			MapNoData[5];
			MapNoData[8];
			MapNoData[1];
			MapNoData[3];
			
			TCSet<int32> Set;
			Set[5];
			Set[8];
			Set[1];
			Set[3];

			TCMap<int32, TCMapTreeMember<int32, int32>> MapComplex;
			
			MapComplex(1, 5, 6);
			
			TCMap<CStr, CStr> MapStr;
			
			MapStr["One"] = "Value";
			
			auto iLinkedListForTree = LinkedListForTree.f_GetIterator();
			
			auto iVector = Vector.f_GetIterator();
			auto iIntrusiveList = IntrusiveList.f_GetIterator();
			auto iLinkedList = LinkedList.f_GetIterator();
			auto iAVLTree = AVLTree.f_GetIterator();
			auto iIntrusiveSingleList = IntrusiveSingleList.f_GetIterator();
 			auto iMap = Map.f_GetIterator();
			auto iMapComplex = MapComplex.f_GetIterator();
			auto iMapNoData = MapNoData.f_GetIterator();
			auto iSet = Set.f_GetIterator();
			
			auto iConstVector = fg_Const(Vector).f_GetIterator();
			auto iConstIntrusiveList = fg_Const(IntrusiveList).f_GetIterator();
			auto iConstLinkedList = fg_Const(LinkedList).f_GetIterator();
			auto iConstAVLTree = fg_Const(AVLTree).f_GetIterator();
			auto iConstIntrusiveSingleList = fg_Const(IntrusiveSingleList).f_GetIterator();
			auto iConstMap = fg_Const(Map).f_GetIterator();
			auto iConstMapComplex = fg_Const(MapComplex).f_GetIterator();
			auto iConstMapNoData = fg_Const(MapNoData).f_GetIterator();
			auto iConstSet = fg_Const(Set).f_GetIterator();
			
			using namespace NTime;
			
			CTime Time = CTime::fs_NowUTC();
			CTimeSpan TimeSpan = CTimeSpanConvert::fs_CreateSpan(0,5,3,2);
			
			fp16 Float16 = fp32(0.5f);
			fp32 Float32 = 5.5f;
			fp64 Float64 = 6.8;
			
			NStorage::TCAggregate<int32> Aggregate = { DAggregateInit };
			
			auto CleanupAggregate
			= fg_OnScopeExit
				(
					[&]()
					{
						Aggregate.f_Clear();
					}
				)
			;
			
			*Aggregate = 55;

			NStorage::TCAggregateSimple<int32> AggregateSimple = { DAggregateInit };
			
			AggregateSimple.f_Construct(55);
			
			NThread::TCThreadLocal<int32> ThreadLocal;
			
			*ThreadLocal = 55;
			
			auto Exception = DMibErrorInstance("Test exception");
			auto ExceptionStr = DMibErrorInstance(CStr("Test exception str"));
			auto ExceptionNonTrackedStr = DMibErrorInstance(CStrNonTracked("Test exception nontracked str"));
			
			NMib::NFile::CExceptionFile &FileException = (NMib::NFile::CExceptionFile &)Exception;
			
			TCVariant<int32, fp32, fp16> Variant0;
			TCVariant<int32, fp32, fp16> Variant1;
			TCVariant<int32, fp32, NMib::NNumeric::TCFloat<1, 5, 10, NMib::NNumeric::CNoImplicit, 1, short>> Variant2;
			
			NMib::NNumeric::TCFloat<1, 5, 10, NMib::NNumeric::CNoImplicit, 1, short> FloatWhat(fp32(3.4f));
			Variant0 = 3;
			Variant1.f_Set<1>(3.3f);
			Variant2.f_Set<2>(fp32(3.4f));

			TCStreamableVariant<int, int32, 0, fp32, 1, fp16, 2> StreamableVariant0;
			TCStreamableVariant<int, int32, 0, fp32, 1, fp16, 2> StreamableVariant1;
			TCStreamableVariant<int, int32, 0, fp32, 1, NMib::NNumeric::TCFloat<1, 5, 10, NMib::NNumeric::CNoImplicit, 1, short>, 2> StreamableVariant2;
			
			StreamableVariant0 = 3;
			StreamableVariant1.f_Set<1>(3.3f);
			StreamableVariant2.f_Set<2>(fp32(3.4f));
			
			/*DMibTrace("MV0: {}\n", Variant0.ms_MemberValue0);
			DMibTrace("MV1: {}\n", Variant1.ms_MemberValue1);
			DMibTrace("MV2: {}\n", Variant2.ms_MemberValue2);*/
			
			struct CTesting
			{
				TCLinkedList<int32> m_LinkedList;
				CTesting()
				{
					m_LinkedList.f_Insert(5);
					m_LinkedList.f_Insert(6);
				}
				void f_Test()
				{
					auto fl_Test
						= [this]()
						{
							m_LinkedList.f_Insert(66);
							m_LinkedList.f_Insert(67);
						}
					;
					
					fl_Test();
				}
			};
			auto fl_Test
				= [&]()
				{
					IntrusiveList.f_GetIterator();
					AVLTree.f_GetIterator();
					LinkedList.f_Insert(66);
					LinkedList.f_Insert(67);
				}
			;
			
			fl_Test();
			
			CTesting TestLinkedLamba;
			
			TestLinkedLamba.f_Test();
			
			CMibCodeAddress StackTrace[16];
			NSys::fg_System_GetStackTrace(StackTrace, 16);
			
			fg_TestIntrusive(IntrusiveList);
			
			TCAtomic<int32> AtomicInt(5);
			TCAtomic<CTestClass *> AtomicPtr(&Vector[0]);
			TCAtomic<CTestClass *> AtomicPtrNull(nullptr);
			
			int32 TestInt = 355;
			TCAtomic<int32 *> AtomicIntPtr(&TestInt);

			TCSet<int32> BigSet;
			TCVector<int32> BigVector;
			TCLinkedList<int32> BigLinkedList;
			
			for (int32 i = 0; i < 2048; ++i)
			{
				BigSet[i];
				BigVector.f_Insert(i);
				BigLinkedList.f_Insert(i);
			}
			
			TCVector<CTestClass> VectorLooped;
			DMibListLinkDS_List(CTestClass, m_Link) IntrusiveListLooped;
			IntrusiveListLooped.f_Insert(VectorLooped.f_Insert(5));
			IntrusiveListLooped.f_Insert(VectorLooped.f_Insert(8));
			IntrusiveListLooped.f_Insert(VectorLooped.f_Insert(1));
			IntrusiveListLooped.f_Insert(VectorLooped.f_Insert(3));
			
			*((void**)(&(VectorLooped[2].m_Link))) = (void*)(&(VectorLooped[0].m_Link));
			
			IntrusiveListLooped.f_Construct();
			for (mint i = 0; i < 4; ++i)
				*((void**)(&(VectorLooped[i].m_Link))) = nullptr;
			
			CTest2 Test2(665);
			
			NStorage::TCAutoClearPtr<CTest2> pAutoClear(&Test2);
			NStorage::TCAutoClearPtrDebug<CTest2> pAutoClearDebug(&Test2);
			NStorage::TCDebugPointer<CTest2> pDebugPointer(&Test2);
			NStorage::TCPointer<CTest2> pPointer(&Test2);
			NStorage::TCSharedPointer<CTest2> pSharedPointer(fg_Construct(667));
			NStorage::TCUniquePointer<CTest2> pUniquePointer(fg_Construct(668));

			NStorage::TCAutoClearPtr<CTest2> pAutoClearNull;
			NStorage::TCAutoClearPtrDebug<CTest2> pAutoClearDebugNull;
			NStorage::TCDebugPointer<CTest2> pDebugPointerNull;
			NStorage::TCPointer<CTest2> pPointerNull;
			NStorage::TCSharedPointer<CTest2> pSharedPointerNull;
 			NStorage::TCUniquePointer<CTest2> pUniquePointerNull;
			
			int32 Data = 664;

			NStorage::TCDebugPointer<int32> pDebugPointerInt(&Data);
			NStorage::TCPointer<int32> pPointerInt(&Data);
			NStorage::TCSharedPointer<int32> pSharedPointerInt(fg_Construct(3));
			NStorage::TCUniquePointer<int32> pUniquePointerInt(fg_Construct(4));
			
			CStr *pStrNullPtr = nullptr;
						
			NMib::NStorage::TCReference<int32> Reference(Data);

			NMib::NStorage::TCIndirection<int32> Indirection(5);
			
			NMib::NContainer::TCRegistry<CStr, CStr> Registry;
			Registry.f_SetThisValue("ValueRoot");
			Registry.f_SetValue("Path0", "ValuePath0");
			Registry.f_SetValue("Path0/Key1", "Value1");
			Registry.f_SetValue("Path0/Key2", "Value2");
			Registry.f_SetValue("Path1/Key3", "Value3");
			Registry.f_SetValue("Path1/Key4", "Value4");
			
			NMib::TCAutoClear<int32> AutoClearGeneral;
			NMib::TCAutoClear<CTest2 *> AutoClearGeneralPointer;
			AutoClearGeneralPointer = &Test2;
			NMib::TCAutoClearInt<int32, 556> AutoClearInt;
			
			zmint AutoClear_zmint = 6;
			zfp32 AutoClear_zfp32 = fp32(5.6f);
			
			using namespace NMib::NEncoding;
			CJSON JSON(EJSONType_Object);
			{
				CJSON &ToReturn = JSON;

				ToReturn["Key"] = "Value";
				ToReturn["KeyTrue"] = true;
				ToReturn["KeyFalse"] = false;
				ToReturn["KeyNull"] = nullptr;
				ToReturn["KeyInt"] = 25;
				ToReturn["KeyFloat"] = 167.6;

				auto &Object = ToReturn["KeyObject"];
				Object["Key"] = "Value";
				Object["KeyTrue"] = true;
				Object["KeyFalse"] = false;
				Object["KeyNull"] = nullptr;
				Object["KeyInt"] = 25;
				Object["KeyFloat"] = 167.6;
				Object["KeyArray"] = EJSONType_Array;
				Object["KeyObject"] = EJSONType_Object;

				auto &Array = ToReturn["KeyArray"];
				Array.f_Insert(25);
				Array.f_Insert(167.6);
				Array.f_Insert(true);
				Array.f_Insert(false);
				Array.f_Insert(EJSONType_Array);

				auto &ArrayObject = Array.f_Insert();
				ArrayObject["KeyInt"] = 25;
				ArrayObject["KeyFloat"] = 167.6;
			}
			
			auto& RawStr0Ref = RawStr0;
			auto& RawStr1Ref = RawStr1;
			auto& RawStr2Ref = RawStr2;
			auto& pRawStr0Ref = pRawStr0;
			auto& pRawStr1Ref = pRawStr1;
			auto& pRawStr2Ref = pRawStr2;
			auto& MixedStr8Ref = MixedStr8;
			auto& MixedStr16Ref = MixedStr16;
			auto& MixedStr32Ref = MixedStr32;
			auto& AnsiStrRef = AnsiStr;
			auto& UnicodeStrRef = UnicodeStr;
			auto& TestUTF8Ref = TestUTF8;
			auto& TestUnicode8Ref = TestUnicode8;
			auto& TestAnsi8Ref = TestAnsi8;
			auto& TestUTF16Ref = TestUTF16;
			auto& TestUnicode16Ref = TestUnicode16;
			auto& TestUnicode32Ref = TestUnicode32;
			auto& VectorRef = Vector;
			auto& IntrusiveListRef = IntrusiveList;
			auto& LinkedListRef = LinkedList;
			auto& LinkedListForTreeRef = LinkedListForTree;
			auto& AVLTreeRef = AVLTree;
			auto& IntrusiveSingleListRef = IntrusiveSingleList;
			auto& MapRef = Map;
			auto& MapNoDataRef = MapNoData;
			auto& SetRef = Set;
			auto& MapComplexRef = MapComplex;
			auto& MapStrRef = MapStr;
			auto& iLinkedListForTreeRef = iLinkedListForTree;
			auto& iVectorRef = iVector;
			auto& iIntrusiveListRef = iIntrusiveList;
			auto& iLinkedListRef = iLinkedList;
			auto& iAVLTreeRef = iAVLTree;
			auto& iIntrusiveSingleListRef = iIntrusiveSingleList;
			auto& iMapRef = iMap;
			auto& iMapComplexRef = iMapComplex;
			auto& iMapNoDataRef = iMapNoData;
			auto& iSetRef = iSet;
			auto& iConstVectorRef = iConstVector;
			auto& iConstIntrusiveListRef = iConstIntrusiveList;
			auto& iConstLinkedListRef = iConstLinkedList;
			auto& iConstAVLTreeRef = iConstAVLTree;
			auto& iConstIntrusiveSingleListRef = iConstIntrusiveSingleList;
			auto& iConstMapRef = iConstMap;
			auto& iConstMapComplexRef = iConstMapComplex;
			auto& iConstMapNoDataRef = iConstMapNoData;
			auto& iConstSetRef = iConstSet;
			auto& TimeRef = Time;
			auto& TimeSpanRef = TimeSpan;
			auto& Float16Ref = Float16;
			auto& Float32Ref = Float32;
			auto& Float64Ref = Float64;
			auto& AggregateRef = Aggregate;
			auto& AggregateSimpleRef = AggregateSimple;
			auto& ThreadLocalRef = ThreadLocal;
			auto& ExceptionRef = Exception;
			auto& ExceptionStrRef = ExceptionStr;
			auto& ExceptionNonTrackedStrRef = ExceptionNonTrackedStr;
			auto& Variant0Ref = Variant0;
			auto& Variant1Ref = Variant1;
			auto& Variant2Ref = Variant2;
			auto& FloatWhatRef = FloatWhat;
			auto& StackTraceRef = StackTrace;
			auto& AtomicIntRef = AtomicInt;
			auto& AtomicPtrRef = AtomicPtr;
			auto& AtomicPtrNullRef = AtomicPtrNull;
			auto& AtomicIntPtrRef = AtomicIntPtr;
			auto& BigSetRef = BigSet;
			auto& BigVectorRef = BigVector;
			auto& BigLinkedListRef = BigLinkedList;
			auto& pAutoClearRef = pAutoClear;
			auto& pAutoClearDebugRef = pAutoClearDebug;
			auto& pDebugPointerRef = pDebugPointer;
			auto& pPointerRef = pPointer;
			auto& pSharedPointerRef = pSharedPointer;
			auto& pUniquePointerRef = pUniquePointer;
			auto& pAutoClearNullRef = pAutoClearNull;
			auto& pAutoClearDebugNullRef = pAutoClearDebugNull;
			auto& pDebugPointerNullRef = pDebugPointerNull;
			auto& pPointerNullRef = pPointerNull;
			auto& pSharedPointerNullRef = pSharedPointerNull;
			auto& pUniquePointerNullRef = pUniquePointerNull;
			auto& pDebugPointerIntRef = pDebugPointerInt;
			auto& pPointerIntRef = pPointerInt;
			auto& pSharedPointerIntRef = pSharedPointerInt;
			auto& pUniquePointerIntRef = pUniquePointerInt;
			auto& ReferenceRef = Reference;
			auto& IndirectionRef = Indirection;
			auto& AutoClearGeneralRef = AutoClearGeneral;
			auto& AutoClearGeneralPointerRef = AutoClearGeneralPointer;
			auto& AutoClearIntRef = AutoClearInt;
			auto& AutoClear_zmintRef = AutoClear_zmint;
			auto& AutoClear_zfp32Ref = AutoClear_zfp32;

			auto const& RawStr0ConstRef = RawStr0;
			auto const& RawStr1ConstRef = RawStr1;
			auto const& RawStr2ConstRef = RawStr2;
			auto const& pRawStr0ConstRef = pRawStr0;
			auto const& pRawStr1ConstRef = pRawStr1;
			auto const& pRawStr2ConstRef = pRawStr2;
			auto const& MixedStr8ConstRef = MixedStr8;
			auto const& MixedStr16ConstRef = MixedStr16;
			auto const& MixedStr32ConstRef = MixedStr32;
			auto const& AnsiStrConstRef = AnsiStr;
			auto const& UnicodeStrConstRef = UnicodeStr;
			auto const& TestUTF8ConstRef = TestUTF8;
			auto const& TestUnicode8ConstRef = TestUnicode8;
			auto const& TestAnsi8ConstRef = TestAnsi8;
			auto const& TestUTF16ConstRef = TestUTF16;
			auto const& TestUnicode16ConstRef = TestUnicode16;
			auto const& TestUnicode32ConstRef = TestUnicode32;
			auto const& VectorConstRef = Vector;
			auto const& IntrusiveListConstRef = IntrusiveList;
			auto const& LinkedListConstRef = LinkedList;
			auto const& LinkedListForTreeConstRef = LinkedListForTree;
			auto const& AVLTreeConstRef = AVLTree;
			auto const& IntrusiveSingleListConstRef = IntrusiveSingleList;
			auto const& MapConstRef = Map;
			auto const& MapNoDataConstRef = MapNoData;
			auto const& SetConstRef = Set;
			auto const& MapComplexConstRef = MapComplex;
			auto const& MapStrConstRef = MapStr;
			auto const& iLinkedListForTreeConstRef = iLinkedListForTree;
			auto const& iVectorConstRef = iVector;
			auto const& iIntrusiveListConstRef = iIntrusiveList;
			auto const& iLinkedListConstRef = iLinkedList;
			auto const& iAVLTreeConstRef = iAVLTree;
			auto const& iIntrusiveSingleListConstRef = iIntrusiveSingleList;
			auto const& iMapConstRef = iMap;
			auto const& iMapComplexConstRef = iMapComplex;
			auto const& iMapNoDataConstRef = iMapNoData;
			auto const& iSetConstRef = iSet;
			auto const& iConstVectorConstRef = iConstVector;
			auto const& iConstIntrusiveListConstRef = iConstIntrusiveList;
			auto const& iConstLinkedListConstRef = iConstLinkedList;
			auto const& iConstAVLTreeConstRef = iConstAVLTree;
			auto const& iConstIntrusiveSingleListConstRef = iConstIntrusiveSingleList;
			auto const& iConstMapConstRef = iConstMap;
			auto const& iConstMapComplexConstRef = iConstMapComplex;
			auto const& iConstMapNoDataConstRef = iConstMapNoData;
			auto const& iConstSetConstRef = iConstSet;
			auto const& TimeConstRef = Time;
			auto const& TimeSpanConstRef = TimeSpan;
			auto const& Float16ConstRef = Float16;
			auto const& Float32ConstRef = Float32;
			auto const& Float64ConstRef = Float64;
			auto const& AggregateConstRef = Aggregate;
			auto const& AggregateSimpleConstRef = AggregateSimple;
			auto const& ThreadLocalConstRef = ThreadLocal;
			auto const& ExceptionConstRef = Exception;
			auto const& ExceptionStrConstRef = ExceptionStr;
			auto const& ExceptionNonTrackedStrConstRef = ExceptionNonTrackedStr;
			auto const& Variant0ConstRef = Variant0;
			auto const& Variant1ConstRef = Variant1;
			auto const& Variant2ConstRef = Variant2;
			auto const& FloatWhatConstRef = FloatWhat;
			auto const& StackTraceConstRef = StackTrace;
			auto const& AtomicIntConstRef = AtomicInt;
			auto const& AtomicPtrConstRef = AtomicPtr;
			auto const& AtomicPtrNullConstRef = AtomicPtrNull;
			auto const& AtomicIntPtrConstRef = AtomicIntPtr;
			auto const& BigSetConstRef = BigSet;
			auto const& BigVectorConstRef = BigVector;
			auto const& BigLinkedListConstRef = BigLinkedList;
			auto const& pAutoClearConstRef = pAutoClear;
			auto const& pAutoClearDebugConstRef = pAutoClearDebug;
			auto const& pDebugPointerConstRef = pDebugPointer;
			auto const& pPointerConstRef = pPointer;
			auto const& pSharedPointerConstRef = pSharedPointer;
			auto const& pUniquePointerConstRef = pUniquePointer;
			auto const& pAutoClearNullConstRef = pAutoClearNull;
			auto const& pAutoClearDebugNullConstRef = pAutoClearDebugNull;
			auto const& pDebugPointerNullConstRef = pDebugPointerNull;
			auto const& pPointerNullConstRef = pPointerNull;
			auto const& pSharedPointerNullConstRef = pSharedPointerNull;
			auto const& pUniquePointerNullConstRef = pUniquePointerNull;
			auto const& pDebugPointerIntConstRef = pDebugPointerInt;
			auto const& pPointerIntConstRef = pPointerInt;
			auto const& pSharedPointerIntConstRef = pSharedPointerInt;
			auto const& pUniquePointerIntConstRef = pUniquePointerInt;
			auto const& ReferenceConstRef = Reference;
			auto const& IndirectionConstRef = Indirection;
			auto const& AutoClearGeneralConstRef = AutoClearGeneral;
			auto const& AutoClearGeneralPointerConstRef = AutoClearGeneralPointer;
			auto const& AutoClearIntConstRef = AutoClearInt;
			auto const& AutoClear_zmintConstRef = AutoClear_zmint;
			auto const& AutoClear_zfp32ConstRef = AutoClear_zfp32;

			auto volatile& RawStr0VolatileRef = RawStr0;
			auto volatile& RawStr1VolatileRef = RawStr1;
			auto volatile& RawStr2VolatileRef = RawStr2;
			auto volatile& pRawStr0VolatileRef = pRawStr0;
			auto volatile& pRawStr1VolatileRef = pRawStr1;
			auto volatile& pRawStr2VolatileRef = pRawStr2;
			auto volatile& MixedStr8VolatileRef = MixedStr8;
			auto volatile& MixedStr16VolatileRef = MixedStr16;
			auto volatile& MixedStr32VolatileRef = MixedStr32;
			auto volatile& AnsiStrVolatileRef = AnsiStr;
			auto volatile& UnicodeStrVolatileRef = UnicodeStr;
			auto volatile& TestUTF8VolatileRef = TestUTF8;
			auto volatile& TestUnicode8VolatileRef = TestUnicode8;
			auto volatile& TestAnsi8VolatileRef = TestAnsi8;
			auto volatile& TestUTF16VolatileRef = TestUTF16;
			auto volatile& TestUnicode16VolatileRef = TestUnicode16;
			auto volatile& TestUnicode32VolatileRef = TestUnicode32;
			auto volatile& VectorVolatileRef = Vector;
			auto volatile& IntrusiveListVolatileRef = IntrusiveList;
			auto volatile& LinkedListVolatileRef = LinkedList;
			auto volatile& LinkedListForTreeVolatileRef = LinkedListForTree;
			auto volatile& AVLTreeVolatileRef = AVLTree;
			auto volatile& IntrusiveSingleListVolatileRef = IntrusiveSingleList;
			auto volatile& MapVolatileRef = Map;
			auto volatile& MapNoDataVolatileRef = MapNoData;
			auto volatile& SetVolatileRef = Set;
			auto volatile& MapComplexVolatileRef = MapComplex;
			auto volatile& MapStrVolatileRef = MapStr;
			auto volatile& iLinkedListForTreeVolatileRef = iLinkedListForTree;
			auto volatile& iVectorVolatileRef = iVector;
			auto volatile& iIntrusiveListVolatileRef = iIntrusiveList;
			auto volatile& iLinkedListVolatileRef = iLinkedList;
			auto volatile& iAVLTreeVolatileRef = iAVLTree;
			auto volatile& iIntrusiveSingleListVolatileRef = iIntrusiveSingleList;
			auto volatile& iMapVolatileRef = iMap;
			auto volatile& iMapComplexVolatileRef = iMapComplex;
			auto volatile& iMapNoDataVolatileRef = iMapNoData;
			auto volatile& iSetVolatileRef = iSet;
			auto volatile& iConstVectorVolatileRef = iConstVector;
			auto volatile& iConstIntrusiveListVolatileRef = iConstIntrusiveList;
			auto volatile& iConstLinkedListVolatileRef = iConstLinkedList;
			auto volatile& iConstAVLTreeVolatileRef = iConstAVLTree;
			auto volatile& iConstIntrusiveSingleListVolatileRef = iConstIntrusiveSingleList;
			auto volatile& iConstMapVolatileRef = iConstMap;
			auto volatile& iConstMapComplexVolatileRef = iConstMapComplex;
			auto volatile& iConstMapNoDataVolatileRef = iConstMapNoData;
			auto volatile& iConstSetVolatileRef = iConstSet;
			auto volatile& TimeVolatileRef = Time;
			auto volatile& TimeSpanVolatileRef = TimeSpan;
			auto volatile& Float16VolatileRef = Float16;
			auto volatile& Float32VolatileRef = Float32;
			auto volatile& Float64VolatileRef = Float64;
			auto volatile& AggregateVolatileRef = Aggregate;
			auto volatile& AggregateSimpleVolatileRef = AggregateSimple;
			auto volatile& ThreadLocalVolatileRef = ThreadLocal;
			auto volatile& ExceptionVolatileRef = Exception;
			auto volatile& ExceptionStrVolatileRef = ExceptionStr;
			auto volatile& ExceptionNonTrackedStrVolatileRef = ExceptionNonTrackedStr;
			auto volatile& Variant0VolatileRef = Variant0;
			auto volatile& Variant1VolatileRef = Variant1;
			auto volatile& Variant2VolatileRef = Variant2;
			auto volatile& FloatWhatVolatileRef = FloatWhat;
			auto volatile& StackTraceVolatileRef = StackTrace;
			auto volatile& AtomicIntVolatileRef = AtomicInt;
			auto volatile& AtomicPtrVolatileRef = AtomicPtr;
			auto volatile& AtomicPtrNullVolatileRef = AtomicPtrNull;
			auto volatile& AtomicIntPtrVolatileRef = AtomicIntPtr;
			auto volatile& BigSetVolatileRef = BigSet;
			auto volatile& BigVectorVolatileRef = BigVector;
			auto volatile& BigLinkedListVolatileRef = BigLinkedList;
			auto volatile& pAutoClearVolatileRef = pAutoClear;
			auto volatile& pAutoClearDebugVolatileRef = pAutoClearDebug;
			auto volatile& pDebugPointerVolatileRef = pDebugPointer;
			auto volatile& pPointerVolatileRef = pPointer;
			auto volatile& pSharedPointerVolatileRef = pSharedPointer;
			auto volatile& pUniquePointerVolatileRef = pUniquePointer;
			auto volatile& pAutoClearNullVolatileRef = pAutoClearNull;
			auto volatile& pAutoClearDebugNullVolatileRef = pAutoClearDebugNull;
			auto volatile& pDebugPointerNullVolatileRef = pDebugPointerNull;
			auto volatile& pPointerNullVolatileRef = pPointerNull;
			auto volatile& pSharedPointerNullVolatileRef = pSharedPointerNull;
			auto volatile& pUniquePointerNullVolatileRef = pUniquePointerNull;
			auto volatile& pDebugPointerIntVolatileRef = pDebugPointerInt;
			auto volatile& pPointerIntVolatileRef = pPointerInt;
			auto volatile& pSharedPointerIntVolatileRef = pSharedPointerInt;
			auto volatile& pUniquePointerIntVolatileRef = pUniquePointerInt;
			auto volatile& ReferenceVolatileRef = Reference;
			auto volatile& IndirectionVolatileRef = Indirection;
			auto volatile& AutoClearGeneralVolatileRef = AutoClearGeneral;
			auto volatile& AutoClearGeneralPointerVolatileRef = AutoClearGeneralPointer;
			auto volatile& AutoClearIntVolatileRef = AutoClearInt;
			auto volatile& AutoClear_zmintVolatileRef = AutoClear_zmint;
			auto volatile& AutoClear_zfp32VolatileRef = AutoClear_zfp32;
			
			
			auto* RawStr0Ptr = &RawStr0;
			auto* RawStr1Ptr = &RawStr1;
			auto* RawStr2Ptr = &RawStr2;
			auto* pRawStr0Ptr = &pRawStr0;
			auto* pRawStr1Ptr = &pRawStr1;
			auto* pRawStr2Ptr = &pRawStr2;
			auto* pStr3 = &Str0;
			auto* pStr4 = &Str1;
			auto* pStr5 = &Str2;
			auto* pStr3_0 = &Str0_0;
			auto* pStr4_0 = &Str1_0;
			auto* pStr5_0 = &Str2_0;
			auto* pStr6_0 = &Str6;
			auto* pStr7_0 = &Str7;
			auto* pStr8_0 = &Str8;
			auto* pStr9_0 = &Str9;
			auto* pStr10_0 = &Str10;
			auto* pStr11_0 = &Str11;
			auto* pStr15 = &Str12;
			auto* pStr16 = &Str13;
			auto* pStr17 = &Str14;
			auto* pStr15_0 = &Str12_0;
			auto* pStr16_0 = &Str13_0;
			auto* pStr17_0 = &Str14_0;
			auto* pStr21 = &Str18;
			auto* pStr22 = &Str19;
			auto* pStr23 = &Str20;
			auto* pStr21_0 = &Str18_0;
			auto* pStr22_0 = &Str19_0;
			auto* pStr23_0 = &Str20_0;
			auto* pStr27 = &Str24;
			auto* pStr28 = &Str25;
			auto* pStr29 = &Str26;
			auto* pStr27_0 = &Str24_0;
			auto* pStr28_0 = &Str25_0;
			auto* pStr29_0 = &Str26_0;
			auto* pStr33 = &Str30;
			auto* pStr34 = &Str31;
			auto* pStr35 = &Str32;
			auto* pStr33_0 = &Str30_0;
			auto* pStr34_0 = &Str31_0;
			auto* pStr35_0 = &Str32_0;
			auto* pMixedStr8 = &MixedStr8;
			auto* pMixedStr16 = &MixedStr16;
			auto* pMixedStr32 = &MixedStr32;
			auto* pAnsiStr = &AnsiStr;
			auto* pUnicodeStr = &UnicodeStr;
			auto* pTestUTF8 = &TestUTF8;
			auto* pTestUnicode8 = &TestUnicode8;
			auto* pTestAnsi8 = &TestAnsi8;
			auto* pTestUTF16 = &TestUTF16;
			auto* pTestUnicode16 = &TestUnicode16;
			auto* pTestUnicode32 = &TestUnicode32;
			auto* pVector = &Vector;
			auto* pIntrusiveList = &IntrusiveList;
			auto* pLinkedList = &LinkedList;
			auto* pLinkedListForTree = &LinkedListForTree;
			auto* pAVLTree = &AVLTree;
			auto* pIntrusiveSingleList = &IntrusiveSingleList;
			auto* pMap = &Map;
			auto* pMapNoData = &MapNoData;
			auto* pSet = &Set;
			auto* pMapComplex = &MapComplex;
			auto* pMapStr = &MapStr;
			auto* piLinkedListForTree = &iLinkedListForTree;
			auto* piVector = &iVector;
			auto* piIntrusiveList = &iIntrusiveList;
			auto* piLinkedList = &iLinkedList;
			auto* piAVLTree = &iAVLTree;
			auto* piIntrusiveSingleList = &iIntrusiveSingleList;
			auto* piMap = &iMap;
			auto* piMapComplex = &iMapComplex;
			auto* piMapNoData = &iMapNoData;
			auto* piSet = &iSet;
			auto* piConstVector = &iConstVector;
			auto* piConstIntrusiveList = &iConstIntrusiveList;
			auto* piConstLinkedList = &iConstLinkedList;
			auto* piConstAVLTree = &iConstAVLTree;
			auto* piConstIntrusiveSingleList = &iConstIntrusiveSingleList;
			auto* piConstMap = &iConstMap;
			auto* piConstMapComplex = &iConstMapComplex;
			auto* piConstMapNoData = &iConstMapNoData;
			auto* piConstSet = &iConstSet;
			auto* pTime = &Time;
			auto* pTimeSpan = &TimeSpan;
			auto* pFloat16 = &Float16;
			auto* pFloat32 = &Float32;
			auto* pFloat64 = &Float64;
			auto* pAggregate = &Aggregate;
			auto* pAggregateSimple = &AggregateSimple;
			auto* pException = &Exception;
			auto* pExceptionStr = &ExceptionStr;
			auto* pExceptionNonTrackedStr = &ExceptionNonTrackedStr;
			auto* pVariant0 = &Variant0;
			auto* pVariant1 = &Variant1;
			auto* pVariant2 = &Variant2;
			auto* pFloatWhat = &FloatWhat;
			auto* pStackTrace = &StackTrace;
			auto* pAtomicInt = &AtomicInt;
			auto* pAtomicPtr = &AtomicPtr;
			auto* pAtomicPtrNull = &AtomicPtrNull;
			auto* pAtomicIntPtr = &AtomicIntPtr;
			auto* pBigSet = &BigSet;
			auto* pBigVector = &BigVector;
			auto* pBigLinkedList = &BigLinkedList;
			auto* ppAutoClear = &pAutoClear;
			auto* ppAutoClearDebug = &pAutoClearDebug;
			auto* ppDebugPointer = &pDebugPointer;
			auto* ppPointer = &pPointer;
			auto* ppSharedPointer = &pSharedPointer;
			auto* ppUniquePointer = &pUniquePointer;
			auto* ppAutoClearNull = &pAutoClearNull;
			auto* ppAutoClearDebugNull = &pAutoClearDebugNull;
			auto* ppDebugPointerNull = &pDebugPointerNull;
			auto* ppPointerNull = &pPointerNull;
			auto* ppSharedPointerNull = &pSharedPointerNull;
			auto* ppUniquePointerNull = &pUniquePointerNull;
			auto* ppDebugPointerInt = &pDebugPointerInt;
			auto* ppPointerInt = &pPointerInt;
			auto* ppSharedPointerInt = &pSharedPointerInt;
			auto* ppUniquePointerInt = &pUniquePointerInt;
			auto* pReference = &Reference;
			auto* pIndirection = &Indirection;
			auto* pAutoClearGeneral = &AutoClearGeneral;
			auto* pAutoClearGeneralPointer = &AutoClearGeneralPointer;
			auto* pAutoClearInt = &AutoClearInt;
			auto* pAutoClear_zmint = &AutoClear_zmint;
			auto* pAutoClear_zfp32 = &AutoClear_zfp32;
			
			
			auto** RawStr0PtrPtr = &RawStr0Ptr;
			auto** RawStr1PtrPtr = &RawStr1Ptr;
			auto** RawStr2PtrPtr = &RawStr2Ptr;
			auto** ppRawStr0Ptr = &pRawStr0Ptr;
			auto** ppRawStr1Ptr = &pRawStr1Ptr;
			auto** ppRawStr2Ptr = &pRawStr2Ptr;
			auto** ppStr3 = &pStr3;
			auto** ppStr4 = &pStr4;
			auto** ppStr5 = &pStr5;
			auto** ppStr3_0 = &pStr3_0;
			auto** ppStr4_0 = &pStr4_0;
			auto** ppStr5_0 = &pStr5_0;
			auto** ppStr6_0 = &pStr6_0;
			auto** ppStr7_0 = &pStr7_0;
			auto** ppStr8_0 = &pStr8_0;
			auto** ppStr9_0 = &pStr9_0;
			auto** ppStr10_0 = &pStr10_0;
			auto** ppStr11_0 = &pStr11_0;
			auto** ppStr15 = &pStr15;
			auto** ppStr16 = &pStr16;
			auto** ppStr17 = &pStr17;
			auto** ppStr15_0 = &pStr15_0;
			auto** ppStr16_0 = &pStr16_0;
			auto** ppStr17_0 = &pStr17_0;
			auto** ppStr21 = &pStr21;
			auto** ppStr22 = &pStr22;
			auto** ppStr23 = &pStr23;
			auto** ppStr21_0 = &pStr21_0;
			auto** ppStr22_0 = &pStr22_0;
			auto** ppStr23_0 = &pStr23_0;
			auto** ppStr27 = &pStr27;
			auto** ppStr28 = &pStr28;
			auto** ppStr29 = &pStr29;
			auto** ppStr27_0 = &pStr27_0;
			auto** ppStr28_0 = &pStr28_0;
			auto** ppStr29_0 = &pStr29_0;
			auto** ppStr33 = &pStr33;
			auto** ppStr34 = &pStr34;
			auto** ppStr35 = &pStr35;
			auto** ppStr33_0 = &pStr33_0;
			auto** ppStr34_0 = &pStr34_0;
			auto** ppStr35_0 = &pStr35_0;
			auto** ppMixedStr8 = &pMixedStr8;
			auto** ppMixedStr16 = &pMixedStr16;
			auto** ppMixedStr32 = &pMixedStr32;
			auto** ppAnsiStr = &pAnsiStr;
			auto** ppUnicodeStr = &pUnicodeStr;
			auto** ppTestUTF8 = &pTestUTF8;
			auto** ppTestUnicode8 = &pTestUnicode8;
			auto** ppTestAnsi8 = &pTestAnsi8;
			auto** ppTestUTF16 = &pTestUTF16;
			auto** ppTestUnicode16 = &pTestUnicode16;
			auto** ppTestUnicode32 = &pTestUnicode32;
			auto** ppVector = &pVector;
			auto** ppIntrusiveList = &pIntrusiveList;
			auto** ppLinkedList = &pLinkedList;
			auto** ppLinkedListForTree = &pLinkedListForTree;
			auto** ppAVLTree = &pAVLTree;
			auto** ppIntrusiveSingleList = &pIntrusiveSingleList;
			auto** ppMap = &pMap;
			auto** ppMapNoData = &pMapNoData;
			auto** ppSet = &pSet;
			auto** ppMapComplex = &pMapComplex;
			auto** ppMapStr = &pMapStr;
			auto** ppiLinkedListForTree = &piLinkedListForTree;
			auto** ppiVector = &piVector;
			auto** ppiIntrusiveList = &piIntrusiveList;
			auto** ppiLinkedList = &piLinkedList;
			auto** ppiAVLTree = &piAVLTree;
			auto** ppiIntrusiveSingleList = &piIntrusiveSingleList;
			auto** ppiMap = &piMap;
			auto** ppiMapComplex = &piMapComplex;
			auto** ppiMapNoData = &piMapNoData;
			auto** ppiSet = &piSet;
			auto** ppiConstVector = &piConstVector;
			auto** ppiConstIntrusiveList = &piConstIntrusiveList;
			auto** ppiConstLinkedList = &piConstLinkedList;
			auto** ppiConstAVLTree = &piConstAVLTree;
			auto** ppiConstIntrusiveSingleList = &piConstIntrusiveSingleList;
			auto** ppiConstMap = &piConstMap;
			auto** ppiConstMapComplex = &piConstMapComplex;
			auto** ppiConstMapNoData = &piConstMapNoData;
			auto** ppiConstSet = &piConstSet;
			auto** ppTime = &pTime;
			auto** ppTimeSpan = &pTimeSpan;
			auto** ppFloat16 = &pFloat16;
			auto** ppFloat32 = &pFloat32;
			auto** ppFloat64 = &pFloat64;
			auto** ppAggregate = &pAggregate;
			auto** ppAggregateSimple = &pAggregateSimple;
			auto** ppException = &pException;
			auto** ppExceptionStr = &pExceptionStr;
			auto** ppExceptionNonTrackedStr = &pExceptionNonTrackedStr;
			auto** ppVariant0 = &pVariant0;
			auto** ppVariant1 = &pVariant1;
			auto** ppVariant2 = &pVariant2;
			auto** ppFloatWhat = &pFloatWhat;
			auto** ppStackTrace = &pStackTrace;
			auto** ppAtomicInt = &pAtomicInt;
			auto** ppAtomicPtr = &pAtomicPtr;
			auto** ppAtomicPtrNull = &pAtomicPtrNull;
			auto** ppAtomicIntPtr = &pAtomicIntPtr;
			auto** ppBigSet = &pBigSet;
			auto** ppBigVector = &pBigVector;
			auto** ppBigLinkedList = &pBigLinkedList;
			auto** pppAutoClear = &ppAutoClear;
			auto** pppAutoClearDebug = &ppAutoClearDebug;
			auto** pppDebugPointer = &ppDebugPointer;
			auto** pppPointer = &ppPointer;
			auto** pppSharedPointer = &ppSharedPointer;
			auto** pppUniquePointer = &ppUniquePointer;
			auto** pppAutoClearNull = &ppAutoClearNull;
			auto** pppAutoClearDebugNull = &ppAutoClearDebugNull;
			auto** pppDebugPointerNull = &ppDebugPointerNull;
			auto** pppPointerNull = &ppPointerNull;
			auto** pppSharedPointerNull = &ppSharedPointerNull;
			auto** pppUniquePointerNull = &ppUniquePointerNull;
			auto** pppDebugPointerInt = &ppDebugPointerInt;
			auto** pppPointerInt = &ppPointerInt;
			auto** pppSharedPointerInt = &ppSharedPointerInt;
			auto** pppUniquePointerInt = &ppUniquePointerInt;
			auto** ppReference = &pReference;
			auto** ppIndirection = &pIndirection;
			auto** ppAutoClearGeneral = &pAutoClearGeneral;
			auto** ppAutoClearGeneralPointer = &pAutoClearGeneralPointer;
			auto** ppAutoClearInt = &pAutoClearInt;
			auto** ppAutoClear_zmint = &pAutoClear_zmint;
			auto** ppAutoClear_zfp32 = &pAutoClear_zfp32;
			
			int x1 = 0;
			int x2 = 0;
			int x3 = 0;
			int x4 = 0;
			int x5 = 0;
			int x6 = 0;
			int x7 = 0;
			(void)&JSON;
			int x = 0;
			(void)x; 
			(void)x1;
			(void)x2;
			(void)x3;
			(void)x4;
			(void)x5;
			(void)x6;
			(void)x7;
			
			// pTime
			// pTimeSpan
		};
	}
};

DMibTestRegister(CDebug_Tests, Malterlib::Debug);

