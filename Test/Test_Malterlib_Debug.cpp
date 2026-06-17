// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

using namespace NMib;

#ifdef DPlatformFamily_macOS
	#include <Mib/Debug/PlatformSpecific/MacOSSymbols>
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

inline_never umint fg_AcquireStackTraceFromHere(CMibCodeAddress* _pStack, umint _MaxDepth)
{
	volatile static int Test = DMibPLine;
	NSys::fg_Compiler_MakeActive(0, &Test);
	volatile umint Value = NMib::NSys::fg_System_GetStackTrace(_pStack, _MaxDepth);
	return Value;
}

#include "Test_Malterlib_Debug.h"
#include <Mib/Storage/Reference>
#include <Mib/Storage/Indirection>
#include <Mib/Container/MapWithPool>
#include <Mib/Container/SetWithPool>
#include <Mib/String/Mixed>
#include <Mib/Encoding/Json>
#include <Mib/Encoding/EJson>
#include <Mib/Encoding/Yaml>
#include <Mib/Numeric/TaggedInteger>
#include <Mib/Numeric/fp80>
#include <Mib/Numeric/fp256>
#include <Mib/Numeric/ufp64>
#include <Mib/Numeric/FloatImp>

class CDebug_Tests : public NMib::NTest::CTest
{
public:

	template <typename t_CValue>
	struct TCFunctionConstTemplateParam
	{
	};

	inline_never static void* fs_LookupThisStaticMemberFunc()
	{
		volatile static int Test = DMibPLine;
		NSys::fg_Compiler_MakeActive(0, &Test);
		void * volatile pRet = fg_GetInstructionPointer();
		return pRet;
	}

	inline_never auto static fs_BigLambda(NEncoding::CEJsonSorted const &_Json)
	{
		return [_Json, Test0 = uint64(), Test1 = uint64(), Test2 = uint64(), Test3 = uint64(), Test4 = uint64()]
			{
				(void)Test0;
				(void)Test1;
				(void)Test2;
				(void)Test3;
				(void)Test4;
				DMibConOut("Test {}:{}\n", DMibPFile, DMibPLine);
			}
		;
	}

	void f_DoTests()
	{
#ifdef DMibDebug_NoSymbols
		return;
#endif

#ifdef DPlatformFamily_Linux
		ETest ExpectLinuxFail = ETest_ExpectFail;
#else
		ETest ExpectLinuxFail = ETest_Fail;
#endif
		DMibTestSuite("StackTrace")
		{
			//DMibTrace("&fg_AcquireStackTraceFromHere: {}\n", (void*)&fg_AcquireStackTraceFromHere );

			CMibCodeAddress Stack[64];
			umint nStack = fg_AcquireStackTraceFromHere(Stack, 64);

			bool bFound = false;

			for (umint i = 0; i < nStack; ++i)
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

#ifndef DPlatformFamily_macOS
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
#if defined(DPlatformFamily_Linux) && !defined(DMibSanitizerEnabled)
		DMibTestSuite("StackTraceInfoExternal")
		{
			{
				CMibCodeAddress pFunction;
				(void * &)pFunction = NMib::NSys::fg_GetLibrarySymbol(nullptr, "dlopen");

				CStackTraceInfo *pInfo = NSys::fg_Debug_AquireStackTraceInfo(pFunction);

				DMibTest(DMibExpr(pInfo) != DMibExpr(nullptr))(ETest_FailAndStop);

				if (pInfo)
				{
					DMibTest(DMibExpr((void*)pInfo->m_pFunctionName) != DMibExpr(nullptr));
					if (pInfo->m_pFunctionName)
						DMibExpect(NStr::CStr(pInfo->m_pFunctionName), ==, "dlopen");

					DMibTest(DMibExpr((void*)pInfo->m_pModuleName) != DMibExpr(nullptr));
					if (pInfo->m_pModuleName)
					{
						auto ModuleName = NFile::CFile::fs_GetFileNoExt(NFile::CFile::fs_GetFileNoExt(NStr::CStr(pInfo->m_pModuleName)));
						DMibTest(DMibExpr(ModuleName) == DMibExpr("libdl") || DMibExpr(ModuleName) == DMibExpr("libc"));
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

#ifndef DPlatformFamily_macOS
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
	#if defined(DPlatformFamily_macOS) && 0
		DMibTestSuite("MacOSSymbols")
		{
			auto &Symbols = NMib::NDebug::NPlatform::fg_GetSymbols();

//			Symbols.f_SetSymbolsFile("/CompiledFiles/Build/Products/Debug Inlined 10.7/Exe_Certifier.symbols");

			NMib::NDebug::NPlatform::CAddressInfo Info;
			bool bLookup = Symbols.f_Lookup((umint)&fg_LookupThisFunc, Info);

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

		DMibTestSuite("VisualizersMini")
		{
			CMibCodeAddress StackTrace[16];
			NSys::fg_System_GetStackTrace(StackTrace, 16);

			DMibTest(DMibExpr(StackTrace[0]) != DMibExpr(nullptr))(ETest_FailAndStop);
		};

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

			ch8 RawStr0[256] = {0};
			ch16 RawStr1[256] = {0};
			ch32 RawStr2[256] = {0};

			ch8 const *pRawStr0 = Str0;
			ch16 const *pRawStr1 = Str1;
			ch32 const *pRawStr2 = Str2;

			NStr::fg_StrCopy(RawStr0, pRawStr0);
			NStr::fg_StrCopy(RawStr1, pRawStr1);
			NStr::fg_StrCopy(RawStr2, pRawStr2);

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> Str0_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> Str1_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsDeflauts>::CType> Str2_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			CFStr128 Str6(str_utf8("CFStr128 実際にあっ 24bit:𠀀"));
			CFStr256 Str7(str_utf8("CFStr256 実際にあっ 24bit:𠀀"));
			CFWStr128 Str8(str_utf16("CFWStr128 実際にあっ 24bit:𠀀"));
			CFWStr256 Str9(str_utf16("CFWStr256 実際にあっ 24bit:𠀀"));
			CFUStr128 Str10(str_utf16("CFUStr128 実際にあっ 24bit:𠀀"));
			CFUStr256 Str11(str_utf16("CFUStr256 実際にあっ 24bit:𠀀"));

			CStrVMem Str12(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CWStrVMem Str13(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			CUStrVMem Str14(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> Str12_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> Str13_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsVirtual>::CType> Str14_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			CStrSecure Str18(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CWStrSecure Str19(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			CUStrSecure Str20(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> Str18_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> Str19_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsSecure>::CType> Str20_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			CStrNonTracked Str24(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			CWStrNonTracked Str25(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			CUStrNonTracked Str26(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			TCStr<TCStrTraits_Eval<ch8, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> Str24_0(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch16, EStrType_UTF, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> Str25_0(str_utf16("CWStr 実際にあっ 24bit:𠀀"));
			TCStr<TCStrTraits_Eval<ch32, EStrType_Unicode, TCStrImp_Dynamic, CStrImp_Dynamic_ParamsNonTracked>::CType> Str26_0(str_utf32("CUStr 実際にあっ 24bit:𠀀"));

			CStrPtr Str30; Str30.f_SetConstPtr(str_utf8("CStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf8("CStrPtr 実際にあっ 24bit:𠀀")));
			CWStrPtr Str31; Str31.f_SetConstPtr(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀")));
			CUStrPtr Str32; Str32.f_SetConstPtr(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀")));

			TCStr<TCStrTraitsPtr<ch8, EStrType_UTF>::CType> Str30_0; Str30_0.f_SetConstPtr(str_utf8("CStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf8("CStrPtr 実際にあっ 24bit:𠀀")));
			TCStr<TCStrTraitsPtr<ch16, EStrType_UTF>::CType> Str31_0; Str31_0.f_SetConstPtr(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf16("CWStrPtr 実際にあっ 24bit:𠀀")));
			TCStr<TCStrTraitsPtr<ch32, EStrType_Unicode>::CType> Str32_0; Str32_0.f_SetConstPtr(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀"), fg_StrLen(str_utf32("CUStrPtr 実際にあっ 24bit:𠀀")));

			CMStrDeprecated MixedStr8(CStr(str_utf8("CStr")));
			CMStrDeprecated MixedStr16(CStr(str_utf8("CWStr 実際にあっ")));
			CMStrDeprecated MixedStr32(CStr(str_utf8("CUStr 実際にあっ 24bit:𠀀")));

			CAnsiStr AnsiStr;
			NMib::NStr::NPlatform::fg_SystemEncodeAnsiStr(CStr(str_utf8("CStr ÄäÅåÖ")), AnsiStr, '?');

			CStr UnicodeStr = CMStrDeprecated(CStr(str_utf8("CStr ÄäÅåÖ")));

			CFStr256 TestUTF8(str_utf8("CStr 実際にあっ 24bit:𠀀"));
			TCFStr<ch8, 256, EStrType_Unicode>::CType TestUnicode8 = AnsiStr.f_GetStr();
			TCFStr<ch8, 256, EStrType_Ansi>::CType TestAnsi8 = AnsiStr;

			CFWStr256 TestUTF16 = CWStr(str_utf16("CStr 実際にあっ 24bit:𠀀"));
			TCFStr<ch16, 256, EStrType_Unicode>::CType TestUnicode16 = str_utf16("CStr 実際にあっ");

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

			TCVector<CTestClassManyValue> Vector2;
			struct CTestLinked
			{
				DMibListLinkDS_List(CTestClassManyValue, m_Link) m_IntrusiveList;
				TCLinkedList<int32> m_LinkedList;
			};

			TCUniquePointer<CTestLinked> pTestLinked = fg_Construct();

			pTestLinked->m_IntrusiveList.f_Insert(Vector2.f_Insert(5));
			pTestLinked->m_IntrusiveList.f_Insert(Vector2.f_Insert(8));
			pTestLinked->m_IntrusiveList.f_Insert(Vector2.f_Insert(1));
			pTestLinked->m_IntrusiveList.f_Insert(Vector2.f_Insert(3));

			pTestLinked->m_LinkedList.f_Insert(5);
			pTestLinked->m_LinkedList.f_Insert(8);
			pTestLinked->m_LinkedList.f_Insert(1);
			pTestLinked->m_LinkedList.f_Insert(3);

			TCVector<CTestRecursiveLinked> Vector3;

			Vector3.f_SetLen(5);

			Vector3[0].m_Children.f_Insert(Vector3[1]);
			Vector3[0].m_Children.f_Insert(Vector3[2]);
			Vector3[2].m_Children.f_Insert(Vector3[3]);
			Vector3[2].m_Children.f_Insert(Vector3[4]);

			TCLinkedList<CTest2> LinkedListForTree;
			TCAVLTree<&CTest2::m_AVLLink, CTest2::CCompare> AVLTree;

			DMibListLinkS_List(CTest2, m_Link) IntrusiveSingleList;

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

			TCMapWithPool<int32, int32> MapWithPool;
			MapWithPool[5] = 5;
			MapWithPool[8] = 8;
			MapWithPool[1] = 1;
			MapWithPool[3] = 3;

			TCSet<int32> Set;
			Set[5];
			Set[8];
			Set[1];
			Set[3];

			TCSetWithPool<int32> SetWithPool;
			SetWithPool[5];
			SetWithPool[8];
			SetWithPool[1];
			SetWithPool[3];

			TCMap<CStr, CStr> MapStr;

			MapStr["One"] = "Value";

			auto iLinkedListForTree = LinkedListForTree.f_GetIterator();

			auto iVector = Vector.f_GetIterator();
			auto iIntrusiveList = IntrusiveList.f_GetIterator();
			auto iLinkedList = LinkedList.f_GetIterator();
			auto iAVLTree = AVLTree.f_GetIterator();
			auto iIntrusiveSingleList = IntrusiveSingleList.f_GetIterator();
			auto iMap = Map.f_GetIterator();
			auto iSet = Set.f_GetIterator();
			auto iManyValues = pTestLinked->m_IntrusiveList.f_GetIterator();

			auto iConstVector = fg_Const(Vector).f_GetIterator();
			auto iConstIntrusiveList = fg_Const(IntrusiveList).f_GetIterator();
			auto iConstLinkedList = fg_Const(LinkedList).f_GetIterator();
			auto iConstAVLTree = fg_Const(AVLTree).f_GetIterator();
			auto iConstIntrusiveSingleList = fg_Const(IntrusiveSingleList).f_GetIterator();
			auto iConstMap = fg_Const(Map).f_GetIterator();
			auto iConstSet = fg_Const(Set).f_GetIterator();
			auto iConstManyValues = fg_Const(pTestLinked->m_IntrusiveList).f_GetIterator();

			auto fMakeEmpty = [](auto &_iIterator)
				{
					while (_iIterator)
						++_iIterator;
				}
			;

			auto iVectorEmpty = Vector.f_GetIterator(); fMakeEmpty(iVectorEmpty);
			auto iIntrusiveListEmpty = IntrusiveList.f_GetIterator(); fMakeEmpty(iIntrusiveListEmpty);
			auto iLinkedListEmpty = LinkedList.f_GetIterator(); fMakeEmpty(iLinkedListEmpty);
			auto iAVLTreeEmpty = AVLTree.f_GetIterator(); fMakeEmpty(iAVLTreeEmpty);
			auto iIntrusiveSingleListEmpty = IntrusiveSingleList.f_GetIterator(); fMakeEmpty(iIntrusiveSingleListEmpty);
			auto iMapEmpty = Map.f_GetIterator(); fMakeEmpty(iMapEmpty);
			auto iSetEmtpy = Set.f_GetIterator(); fMakeEmpty(iSetEmtpy);

			using namespace NTime;

			CTime Time = CTime::fs_NowUTC();
			CTimeSpan TimeSpan = CTimeSpanConvert::fs_CreateSpan(0,5,3,2);

			CTime StartOfTime = CTime::fs_StartOfTime();
			CTime EndOfTime = CTime::fs_EndOfTime();

			CTime AlmostStartOfTime = CTime::fs_StartOfTime() + CTimeSpan::fs_SmallestTime();
			CTime AlmostEndOfTime = CTime::fs_EndOfTime() - CTimeSpan::fs_SmallestTime();

			fp16 Float16 = fp32(0.5f);
			NMib::NNumeric::TCFloat<1, 5, 10, 0, NMib::NNumeric::CNoImplicit, true, short> Float16_2 = fp32(0.66f);
			fp32 Float32 = 5.5f;
			fp32 Float32_Inf = fp32::fs_Inf();
			fp32 Float32_NegInf = fp32::fs_NegInf();
			fp32 Float32_SNan = fp32::fs_SNan();
			fp32 Float32_QNan = fp32::fs_QNan();
			fp32 Float32_NegSNan = fp32::fs_NegSNan();
			fp32 Float32_NegQNan = fp32::fs_NegQNan();
			fp32 Float32_Smallest = fp32::fs_Smallest();
			fp32 Float32_NegSmallest = fp32::fs_NegSmallest();
			fp32 Float32_SmallestDenormal = fp32::fs_SmallestDenormal();
			fp32 Float32_NegSmallestDenormal = fp32::fs_NegSmallestDenormal();

			CIEEEFloat32Emu Float32Emu = Float32;
			CIEEEFloat32Emu Float32Emu_Inf = CIEEEFloat32Emu::fs_Inf();
			CIEEEFloat32Emu Float32Emu_NegInf = CIEEEFloat32Emu::fs_NegInf();
			CIEEEFloat32Emu Float32Emu_SNan = CIEEEFloat32Emu::fs_SNan();
			CIEEEFloat32Emu Float32Emu_QNan = CIEEEFloat32Emu::fs_QNan();
			CIEEEFloat32Emu Float32Emu_NegSNan = CIEEEFloat32Emu::fs_NegSNan();
			CIEEEFloat32Emu Float32Emu_NegQNan = CIEEEFloat32Emu::fs_NegQNan();
			CIEEEFloat32Emu Float32Emu_Smallest = CIEEEFloat32Emu::fs_Smallest();
			CIEEEFloat32Emu Float32Emu_NegSmallest = CIEEEFloat32Emu::fs_NegSmallest();
			CIEEEFloat32Emu Float32Emu_SmallestDenormal = CIEEEFloat32Emu::fs_SmallestDenormal();
			CIEEEFloat32Emu Float32Emu_NegSmallestDenormal = CIEEEFloat32Emu::fs_NegSmallestDenormal();

			fp64 Float64 = 6.8;
			fp64 Float64_Inf = fp64::fs_Inf();
			fp64 Float64_NegInf = fp64::fs_NegInf();
			fp64 Float64_SNan = fp64::fs_SNan();
			fp64 Float64_QNan = fp64::fs_QNan();
			fp64 Float64_NegSNan = fp64::fs_NegSNan();
			fp64 Float64_NegQNan = fp64::fs_NegQNan();
			fp64 Float64_Smallest = fp64::fs_Smallest();
			fp64 Float64_NegSmallest = fp64::fs_NegSmallest();
			fp64 Float64_SmallestDenormal = fp64::fs_SmallestDenormal();
			fp64 Float64_NegSmallestDenormal = fp64::fs_NegSmallestDenormal();

			CIEEEFloat64Emu Float64Emu = Float64;
			CIEEEFloat64Emu Float64Emu_Inf = CIEEEFloat64Emu::fs_Inf();
			CIEEEFloat64Emu Float64Emu_NegInf = CIEEEFloat64Emu::fs_NegInf();
			CIEEEFloat64Emu Float64Emu_SNan = CIEEEFloat64Emu::fs_SNan();
			CIEEEFloat64Emu Float64Emu_QNan = CIEEEFloat64Emu::fs_QNan();
			CIEEEFloat64Emu Float64Emu_NegSNan = CIEEEFloat64Emu::fs_NegSNan();
			CIEEEFloat64Emu Float64Emu_NegQNan = CIEEEFloat64Emu::fs_NegQNan();
			CIEEEFloat64Emu Float64Emu_Smallest = CIEEEFloat64Emu::fs_Smallest();
			CIEEEFloat64Emu Float64Emu_NegSmallest = CIEEEFloat64Emu::fs_NegSmallest();
			CIEEEFloat64Emu Float64Emu_SmallestDenormal = CIEEEFloat64Emu::fs_SmallestDenormal();
			CIEEEFloat64Emu Float64Emu_NegSmallestDenormal = CIEEEFloat64Emu::fs_NegSmallestDenormal();

			fp80 Float80 = fp64(0.6666666666666666666);
			CIEEEFloat80Emu Float80Emu = Float80;

			fp256 Float256 = Float80;
			fp256 Float256_Inf = fp256::fs_Inf();
			fp256 Float256_NegINf = fp256::fs_NegInf();
			fp256 Float256_SNan = fp256::fs_SNan();
			fp256 Float256_QNan = fp256::fs_QNan();
			fp256 Float256_NegSNan = fp256::fs_NegSNan();
			fp256 Float256_NegQNan = fp256::fs_NegQNan();
			fp256 Float256_Smallest = fp256::fs_Smallest();
			fp256 Float256_NegSmallest = fp256::fs_NegSmallest();
			fp256 Float256_SmallestDenormal = fp256::fs_SmallestDenormal();
			fp256 Float256_NegSmallestDenormal = fp256::fs_NegSmallestDenormal();

			ufp16 UFloat16 = fp32(0.5f);
			ufp32 UFloat32 = fp32(5.5f);
			ufp64 UFloat64_Inf = ufp64::fs_Inf();
			ufp64 UFloat64_QNan = ufp64::fs_QNan();
			ufp64 UFloat64_Smallest = ufp64::fs_Smallest();
			ufp64 UFloat64_SmallestDenormal = ufp64::fs_SmallestDenormal();

			static NStorage::TCAggregate<int32> s_Aggregate = { DAggregateInit };
			static NStorage::TCAggregate<int32> s_AggregateEmpty = { DAggregateInit };

			auto CleanupAggregate
				= fg_OnScopeExit
				(
					[&]()
					{
						s_Aggregate.f_Clear();
					}
				)
			;

			*s_Aggregate = 55;

			NStorage::TCAggregateSimple<int32> AggregateSimple = { DAggregateInit };

			AggregateSimple.f_Construct(55);

			NThread::TCThreadLocal<int32> ThreadLocal;

			*ThreadLocal = 55;

			struct CThreadLocalTest
			{
				umint m_Value0 = 0;
				umint m_Value1 = 55;
				umint m_Value2 = 111;
			};

			NThread::TCThreadLocal<CThreadLocalTest> ThreadLocalClass;
			*ThreadLocalClass = CThreadLocalTest();

			NThread::TCThreadLocalDynamic<int32> ThreadLocalDynamic
				(
					[]() -> NThread::CThreadLocalInterface::CSafeAllocMemory
					{
						return
						{
							NMemory::CAllocator_Heap::f_AllocAligned(sizeof(int32), fg_Max(umint(DMibPMemoryCacheLineSize), alignof(int32)))
							, sizeof(int32)
						};
					}
					, [](NThread::CThreadLocalInterface::CSafeAllocMemory const &_Alloc) -> void
					{
						NMemory::CAllocator_Heap::f_Free(_Alloc.m_pMemory, _Alloc.m_Size);
					}
					, [](int32 *_pParent, void *_pMemory, bool _bMove) -> int32 *
					{
						(void)_bMove;
						if (_pParent)
							return new (_pMemory) int32(*_pParent);
						return new (_pMemory) int32();
					}
					, [](int32 *_pData) -> void
					{
						(void)_pData;
					}
				)
			;
			*ThreadLocalDynamic = 9;

			auto Exception = DMibErrorInstance("Test exception");
			auto ExceptionStr = DMibErrorInstance(CStr("Test exception str"));
			auto ExceptionNonTrackedStr = DMibErrorInstance(CStrNonTracked("Test exception nontracked str"));

			NMib::NFile::CExceptionFile &FileException = (NMib::NFile::CExceptionFile &)Exception;

			TCVariant<int32, fp32, fp16> Variant0;
			TCVariant<int32, fp32, fp16> Variant1;
			TCVariant<int32, fp32, NMib::NNumeric::TCFloat<1, 5, 10, 0, NMib::NNumeric::CNoImplicit, 1, short>> Variant2;
			TCVariant<int32, fp32, TCVariant<int32, fp32, fp16>> Variant3;

			TCVariant<void, int32, fp32, fp16> VoidVariant;

			NMib::NNumeric::TCFloat<1, 5, 10, 0, NMib::NNumeric::CNoImplicit, 1, short> FloatWhat(fp32(3.4f));
			struct CTaggedIntegerTestTag {};
			NNumeric::TCTaggedInteger<int32, CTaggedIntegerTestTag> TaggedInteger = NNumeric::TCTaggedInteger<int32, CTaggedIntegerTestTag>::fs_Create(42);

			Variant0 = 3;
			Variant1.f_Set<1>(3.3f);
			Variant2.f_Set<2>(fp32(3.4f));
			Variant3.f_Set<2>(6);

			TCStreamableVariant
				<
					int
					, NStorage::TCMember<int32, 0>
					, NStorage::TCMember<fp32, 1>
					, NStorage::TCMember<fp16, 2>
				>
				StreamableVariant0
			;
			TCStreamableVariant
				<
					int
					, NStorage::TCMember<int32, 0>
					, NStorage::TCMember<fp32, 1>
					, NStorage::TCMember<fp16, 2>
				>
				StreamableVariant1
			;
			TCStreamableVariant
				<
					int
					, NStorage::TCMember<int32, 0>
					, NStorage::TCMember<fp32, 1>
					, NStorage::TCMember<NMib::NNumeric::TCFloat<1, 5, 10, 0, NMib::NNumeric::CNoImplicit, 1, short>, 2>
				>
				StreamableVariant2
			;

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
					auto fTest
						= [this]()
						{
							m_LinkedList.f_Insert(66);
							m_LinkedList.f_Insert(67);
						}
					;

					fTest();
				}
			};
			auto fTest
				= [&]()
				{
					IntrusiveList.f_GetIterator();
					AVLTree.f_GetIterator();
					LinkedList.f_Insert(66);
					LinkedList.f_Insert(67);
				}
			;

			fTest();

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

			*((void**)(&(VectorLooped[3].m_Link))) = (void*)(&(VectorLooped[1].m_Link));

			IntrusiveListLooped.f_Construct();
			for (umint i = 0; i < 4; ++i)
				*((void**)(&(VectorLooped[i].m_Link))) = nullptr;

			CTest2 Test2(665);

			NStorage::TCAutoClearPtr<CTest2> pAutoClear(&Test2);
			NStorage::TCAutoClearPtrDebug<CTest2> pAutoClearDebug(&Test2);
			NStorage::TCDebugPointer<CTest2> pDebugPointer(&Test2);
			NStorage::TCPointer<CTest2> pPointer(&Test2);
			NStorage::TCSharedPointer<CTest2> pSharedPointer(fg_Construct(667));
			NStorage::TCSharedPointerSupportWeak<CTestClass> pSharedPointerSupportWeak(fg_Construct(669));
			NStorage::TCWeakPointer<CTestClass> pWeakPointer = pSharedPointerSupportWeak;
			NStorage::TCUniquePointer<CTest2> pUniquePointer(fg_Construct(668));

			NStorage::TCAutoClearPtr<CTest2> pAutoClearNull;
			NStorage::TCAutoClearPtrDebug<CTest2> pAutoClearDebugNull;
			NStorage::TCDebugPointer<CTest2> pDebugPointerNull;
			NStorage::TCPointer<CTest2> pPointerNull;
			NStorage::TCSharedPointer<CTest2> pSharedPointerNull;
			NStorage::TCSharedPointerSupportWeak<CTestClass> pSharedPointerSupportWeakNull;
			NStorage::TCWeakPointer<CTestClass> pWeakPointerNull;
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

			CRegistryPreserveWhitespace RegistryPreserve;
			RegistryPreserve.f_SetThisValue("ValueRoot");
			RegistryPreserve.f_SetValue("Path0", "ValuePath0");
			RegistryPreserve.f_SetValue("Path0/Key1", "Value1");
			RegistryPreserve.f_SetValue("Path0/Key2", "Value2");
			RegistryPreserve.f_SetValue("Path1/Key3", "Value3");
			RegistryPreserve.f_SetValue("Path1/Key4", "Value4");

			CRegistryPreserveAll RegistryPreserveOrder;
			RegistryPreserveOrder.f_SetThisValue("ValueRoot");
			RegistryPreserveOrder.f_SetValue("Path0", "ValuePath0");
			RegistryPreserveOrder.f_SetValue("Path0/Key1", "Value1");
			RegistryPreserveOrder.f_SetValue("Path0/Key2", "Value2");
			RegistryPreserveOrder.f_SetValue("Path1/Key3", "Value3");
			RegistryPreserveOrder.f_SetValue("Path1/Key4", "Value4");

			NMib::TCAutoClear<int32> AutoClearGeneral;
			NMib::TCAutoClear<CTest2 *> AutoClearGeneralPointer;
			AutoClearGeneralPointer = &Test2;
			NMib::TCAutoClearInt<int32, 556> AutoClearInt;

			zmint AutoClear_zmint = 6;
			zfp32 AutoClear_zfp32 = fp32(5.6f);
			CSecureByteVector SecureByteVector{3,4,5};

			using namespace NMib::NEncoding;
			CJsonSorted Json(EJsonType_Object);
			{
				CJsonSorted &ToReturn = Json;

				ToReturn["Key"] = "Value";
				ToReturn["KeyTrue"] = true;
				ToReturn["KeyFalse"] = false;
				ToReturn["KeyNull"] = nullptr;
				ToReturn["KeyInt"] = 25;
				ToReturn["KeyFloat"] = 167.6;
				ToReturn["KeyInvalid"] = CJsonSorted{};

				auto &Object = ToReturn["KeyObject"];
				Object["Key"] = "Value";
				Object["KeyTrue"] = true;
				Object["KeyFalse"] = false;
				Object["KeyNull"] = nullptr;
				Object["KeyInt"] = 25;
				Object["KeyFloat"] = 167.6;
				Object["KeyArray"] = EJsonType_Array;
				Object["KeyObject"] = EJsonType_Object;

				auto &Array = ToReturn["KeyArray"];
				Array.f_Insert(25);
				Array.f_Insert(167.6);
				Array.f_Insert(true);
				Array.f_Insert(false);
				Array.f_Insert(EJsonType_Array);

				auto &ArrayObject = Array.f_Insert();
				ArrayObject["KeyInt"] = 25;
				ArrayObject["KeyFloat"] = 167.6;
			}

			CEJsonSorted EnhancedJson(EJsonType_Object);
			{
				CEJsonSorted &ToReturn = EnhancedJson;

				ToReturn["Key"] = "Value";
				ToReturn["KeyTrue"] = true;
				ToReturn["KeyFalse"] = false;
				ToReturn["KeyNull"] = nullptr;
				ToReturn["KeyInt"] = 25;
				ToReturn["KeyFloat"] = 167.6;
				ToReturn["KeyInvalid"] = CEJsonSorted{};

				auto &Object = ToReturn["KeyObject"];
				Object["Key"] = "Value";
				Object["KeyTrue"] = true;
				Object["KeyFalse"] = false;
				Object["KeyNull"] = nullptr;
				Object["KeyInt"] = 25;
				Object["KeyFloat"] = 167.6;
				Object["KeyArray"] = EJsonType_Array;
				Object["KeyObject"] = EJsonType_Object;
				Object["KeyBinary"] = CByteVector{0,1,2};
				Object["KeyDate"] = CTime::fs_NowUTC();
				Object["KeyUser"] = CEJsonUserTypeSorted{"TestType", Json};


				auto &Array = ToReturn["KeyArray"];
				Array.f_Insert(25);
				Array.f_Insert(167.6);
				Array.f_Insert(true);
				Array.f_Insert(false);
				Array.f_Insert(EJsonType_Array);

				auto &ArrayObject = Array.f_Insert();
				ArrayObject["KeyInt"] = 25;
				ArrayObject["KeyFloat"] = 167.6;
			}

			auto JsonOrderedYaml = CJsonOrderedYaml::fs_FromCompatible(Json);
			auto JsonSortedYaml = CJsonSortedYaml::fs_FromCompatible(Json);
			auto JsonOrdered = CJsonOrdered::fs_FromCompatible(Json);
			auto EnhancedJsonOrdered = CEJsonOrdered::fs_FromCompatible(EnhancedJson);
			auto EnhancedJsonOrderedYaml = CEJsonOrderedYaml::fs_FromCompatible(EnhancedJson);
			auto EnhancedJsonSortedYaml = CEJsonSortedYaml::fs_FromCompatible(EnhancedJson);

			auto fTestLambda = [&]
				{
					(void)EnhancedJson;
					DMibConOut("Test {}:{}\n", DMibPFile, DMibPLine);
				}
			;

			auto fTestLambdaBig = [&, Test0 = uint64(), Test1 = uint64(), Test2 = uint64(), Test3 = uint64(), Test4 = uint64()]
				{
					(void)EnhancedJson;
					(void)Test0;
					(void)Test1;
					(void)Test2;
					(void)Test3;
					(void)Test4;
					DMibConOut("Test {}:{}\n", DMibPFile, DMibPLine);
				}
			;

			struct CTestingFunctor
			{
				void operator() () const
				{
					DMibConOut("Test {}:{}\n", DMibPFile, DMibPLine);
				}

				void operator() ()
				{
					DMibConOut("Test {}:{}\n", DMibPFile, DMibPLine);
				}
			};

			struct CTestingFunctorConstTemplateParam
			{
				void operator() (TCFunctionConstTemplateParam<int32 const> const &) const
				{
					DMibConOut("Test {}:{}\n", DMibPFile, DMibPLine);
				}

				void operator() (TCFunctionConstTemplateParam<int32 const> const &)
				{
					DMibConOut("Test {}:{}\n", DMibPFile, DMibPLine);
				}
			};

			NFunction::TCFunction<void ()> Function0 = fTestLambda;
			NFunction::TCFunctionFastCall<void ()> Function1 = fTestLambda;
			NFunction::TCFunctionSmall<void ()> Function2 = fTestLambda;
			NFunction::TCFunctionNoAlloc<void ()> Function3 = fTestLambda;
			NFunction::TCFunctionNoAlloc<void ()> FunctionFunctor = CTestingFunctor();
			NFunction::TCFunctionMutable<void ()> FunctionFunctorMutable = CTestingFunctor();
			NFunction::TCFunctionMovable<void ()> FunctionFunctorMovable = CTestingFunctor();
			NFunction::TCFunctionMutable<void (TCFunctionConstTemplateParam<int32 const> const &)> FunctionFunctorMutableConstTemplateParam = CTestingFunctorConstTemplateParam();
			NFunction::TCFunction<void (TCFunctionConstTemplateParam<int32 const> const &)> FunctionFunctorConstThisTagConstTemplateParam = CTestingFunctorConstTemplateParam();

			NFunction::TCFunction<void ()> FunctionExternalLambda = fs_BigLambda(EnhancedJson);

			NFunction::TCFunction<void ()> FunctionBig = fTestLambdaBig;
			NFunction::TCFunction<void ()> FunctionEmpty;

			struct CTestActor : public NConcurrency::CActor
			{
				using CActorHolder = NConcurrency::CSeparateThreadActorHolder;

				umint m_Internal0 = 0;
				umint m_Internal2 = 1;
			};

			NConcurrency::TCActor<CTestActor> TestActor{fg_Construct(), "Test"};
			NConcurrency::TCWeakActor<CTestActor> TestActorWeak = TestActor;

			NConcurrency::TCActor<CTestActor> TestActorEmpty;
			NConcurrency::TCWeakActor<CTestActor> TestActorEmptyWeak;

			auto &RawStr0Ref = RawStr0;
			auto &RawStr1Ref = RawStr1;
			auto &RawStr2Ref = RawStr2;
			auto &pRawStr0Ref = pRawStr0;
			auto &pRawStr1Ref = pRawStr1;
			auto &pRawStr2Ref = pRawStr2;
			auto &MixedStr8Ref = MixedStr8;
			auto &MixedStr16Ref = MixedStr16;
			auto &MixedStr32Ref = MixedStr32;
			auto &AnsiStrRef = AnsiStr;
			auto &UnicodeStrRef = UnicodeStr;
			auto &TestUTF8Ref = TestUTF8;
			auto &TestUnicode8Ref = TestUnicode8;
			auto &TestAnsi8Ref = TestAnsi8;
			auto &TestUTF16Ref = TestUTF16;
			auto &TestUnicode16Ref = TestUnicode16;
			auto &TestUnicode32Ref = TestUnicode32;
			auto &VectorRef = Vector;
			auto &IntrusiveListRef = IntrusiveList;
			auto &LinkedListRef = LinkedList;
			auto &LinkedListForTreeRef = LinkedListForTree;
			auto &AVLTreeRef = AVLTree;
			auto &IntrusiveSingleListRef = IntrusiveSingleList;
			auto &MapRef = Map;
			auto &SetRef = Set;
			auto &MapStrRef = MapStr;
			auto &iLinkedListForTreeRef = iLinkedListForTree;
			auto &iVectorRef = iVector;
			auto &iIntrusiveListRef = iIntrusiveList;
			auto &iLinkedListRef = iLinkedList;
			auto &iAVLTreeRef = iAVLTree;
			auto &iIntrusiveSingleListRef = iIntrusiveSingleList;
			auto &iMapRef = iMap;
			auto &iSetRef = iSet;
			auto &iConstVectorRef = iConstVector;
			auto &iConstIntrusiveListRef = iConstIntrusiveList;
			auto &iConstLinkedListRef = iConstLinkedList;
			auto &iConstAVLTreeRef = iConstAVLTree;
			auto &iConstIntrusiveSingleListRef = iConstIntrusiveSingleList;
			auto &iConstMapRef = iConstMap;
			auto &iConstSetRef = iConstSet;
			auto &TimeRef = Time;
			auto &TimeSpanRef = TimeSpan;
			auto &Float16Ref = Float16;
			auto &Float32Ref = Float32;
			auto &Float64Ref = Float64;
			auto &AggregateRef = s_Aggregate;
			auto &AggregateSimpleRef = AggregateSimple;
			auto &ThreadLocalRef = ThreadLocal;
			auto &ExceptionRef = Exception;
			auto &ExceptionStrRef = ExceptionStr;
			auto &ExceptionNonTrackedStrRef = ExceptionNonTrackedStr;
			auto &Variant0Ref = Variant0;
			auto &Variant1Ref = Variant1;
			auto &Variant2Ref = Variant2;
			auto &FloatWhatRef = FloatWhat;
			auto &StackTraceRef = StackTrace;
			auto &AtomicIntRef = AtomicInt;
			auto &AtomicPtrRef = AtomicPtr;
			auto &AtomicPtrNullRef = AtomicPtrNull;
			auto &AtomicIntPtrRef = AtomicIntPtr;
			auto &BigSetRef = BigSet;
			auto &BigVectorRef = BigVector;
			auto &BigLinkedListRef = BigLinkedList;
			auto &pAutoClearRef = pAutoClear;
			auto &pAutoClearDebugRef = pAutoClearDebug;
			auto &pDebugPointerRef = pDebugPointer;
			auto &pPointerRef = pPointer;
			auto &pSharedPointerRef = pSharedPointer;
			auto &pSharedPointerSupportWeakRef = pSharedPointerSupportWeak;
			auto &pWeakPointerRef = pWeakPointer;
			auto &pUniquePointerRef = pUniquePointer;
			auto &pAutoClearNullRef = pAutoClearNull;
			auto &pAutoClearDebugNullRef = pAutoClearDebugNull;
			auto &pDebugPointerNullRef = pDebugPointerNull;
			auto &pPointerNullRef = pPointerNull;
			auto &pSharedPointerNullRef = pSharedPointerNull;
			auto &pSharedPointerSupportWeakNullRef = pSharedPointerSupportWeakNull;
			auto &pWeakPointerNullRef = pWeakPointerNull;
			auto &pUniquePointerNullRef = pUniquePointerNull;
			auto &pDebugPointerIntRef = pDebugPointerInt;
			auto &pPointerIntRef = pPointerInt;
			auto &pSharedPointerIntRef = pSharedPointerInt;
			auto &pUniquePointerIntRef = pUniquePointerInt;
			auto &ReferenceRef = Reference;
			auto &IndirectionRef = Indirection;
			auto &AutoClearGeneralRef = AutoClearGeneral;
			auto &AutoClearGeneralPointerRef = AutoClearGeneralPointer;
			auto &AutoClearIntRef = AutoClearInt;
			auto &AutoClear_zmintRef = AutoClear_zmint;
			auto &AutoClear_zfp32Ref = AutoClear_zfp32;

			auto const &RawStr0ConstRef = RawStr0;
			auto const &RawStr1ConstRef = RawStr1;
			auto const &RawStr2ConstRef = RawStr2;
			auto const &pRawStr0ConstRef = pRawStr0;
			auto const &pRawStr1ConstRef = pRawStr1;
			auto const &pRawStr2ConstRef = pRawStr2;
			auto const &MixedStr8ConstRef = MixedStr8;
			auto const &MixedStr16ConstRef = MixedStr16;
			auto const &MixedStr32ConstRef = MixedStr32;
			auto const &AnsiStrConstRef = AnsiStr;
			auto const &UnicodeStrConstRef = UnicodeStr;
			auto const &TestUTF8ConstRef = TestUTF8;
			auto const &TestUnicode8ConstRef = TestUnicode8;
			auto const &TestAnsi8ConstRef = TestAnsi8;
			auto const &TestUTF16ConstRef = TestUTF16;
			auto const &TestUnicode16ConstRef = TestUnicode16;
			auto const &TestUnicode32ConstRef = TestUnicode32;
			auto const &VectorConstRef = Vector;
			auto const &IntrusiveListConstRef = IntrusiveList;
			auto const &LinkedListConstRef = LinkedList;
			auto const &LinkedListForTreeConstRef = LinkedListForTree;
			auto const &AVLTreeConstRef = AVLTree;
			auto const &IntrusiveSingleListConstRef = IntrusiveSingleList;
			auto const &MapConstRef = Map;
			auto const &SetConstRef = Set;
			auto const &MapStrConstRef = MapStr;
			auto const &iLinkedListForTreeConstRef = iLinkedListForTree;
			auto const &iVectorConstRef = iVector;
			auto const &iIntrusiveListConstRef = iIntrusiveList;
			auto const &iLinkedListConstRef = iLinkedList;
			auto const &iAVLTreeConstRef = iAVLTree;
			auto const &iIntrusiveSingleListConstRef = iIntrusiveSingleList;
			auto const &iMapConstRef = iMap;
			auto const &iSetConstRef = iSet;
			auto const &iConstVectorConstRef = iConstVector;
			auto const &iConstIntrusiveListConstRef = iConstIntrusiveList;
			auto const &iConstLinkedListConstRef = iConstLinkedList;
			auto const &iConstAVLTreeConstRef = iConstAVLTree;
			auto const &iConstIntrusiveSingleListConstRef = iConstIntrusiveSingleList;
			auto const &iConstMapConstRef = iConstMap;
			auto const &iConstSetConstRef = iConstSet;
			auto const &TimeConstRef = Time;
			auto const &TimeSpanConstRef = TimeSpan;
			auto const &Float16ConstRef = Float16;
			auto const &Float32ConstRef = Float32;
			auto const &Float64ConstRef = Float64;
			auto const &AggregateConstRef = s_Aggregate;
			auto const &AggregateSimpleConstRef = AggregateSimple;
			auto const &ThreadLocalConstRef = ThreadLocal;
			auto const &ExceptionConstRef = Exception;
			auto const &ExceptionStrConstRef = ExceptionStr;
			auto const &ExceptionNonTrackedStrConstRef = ExceptionNonTrackedStr;
			auto const &Variant0ConstRef = Variant0;
			auto const &Variant1ConstRef = Variant1;
			auto const &Variant2ConstRef = Variant2;
			auto const &FloatWhatConstRef = FloatWhat;
			auto const &StackTraceConstRef = StackTrace;
			auto const &AtomicIntConstRef = AtomicInt;
			auto const &AtomicPtrConstRef = AtomicPtr;
			auto const &AtomicPtrNullConstRef = AtomicPtrNull;
			auto const &AtomicIntPtrConstRef = AtomicIntPtr;
			auto const &BigSetConstRef = BigSet;
			auto const &BigVectorConstRef = BigVector;
			auto const &BigLinkedListConstRef = BigLinkedList;
			auto const &pAutoClearConstRef = pAutoClear;
			auto const &pAutoClearDebugConstRef = pAutoClearDebug;
			auto const &pDebugPointerConstRef = pDebugPointer;
			auto const &pPointerConstRef = pPointer;
			auto const &pSharedPointerConstRef = pSharedPointer;
			auto const &pSharedPointerSupportWeakConstRef = pSharedPointerSupportWeak;
			auto const &pWeakPointerConstRef = pWeakPointer;
			auto const &pUniquePointerConstRef = pUniquePointer;
			auto const &pAutoClearNullConstRef = pAutoClearNull;
			auto const &pAutoClearDebugNullConstRef = pAutoClearDebugNull;
			auto const &pDebugPointerNullConstRef = pDebugPointerNull;
			auto const &pPointerNullConstRef = pPointerNull;
			auto const &pSharedPointerNullConstRef = pSharedPointerNull;
			auto const &pSharedPointerSupportWeakNullConstRef = pSharedPointerSupportWeakNull;
			auto const &pWeakPointerNullConstRef = pWeakPointerNull;
			auto const &pUniquePointerNullConstRef = pUniquePointerNull;
			auto const &pDebugPointerIntConstRef = pDebugPointerInt;
			auto const &pPointerIntConstRef = pPointerInt;
			auto const &pSharedPointerIntConstRef = pSharedPointerInt;
			auto const &pUniquePointerIntConstRef = pUniquePointerInt;
			auto const &ReferenceConstRef = Reference;
			auto const &IndirectionConstRef = Indirection;
			auto const &AutoClearGeneralConstRef = AutoClearGeneral;
			auto const &AutoClearGeneralPointerConstRef = AutoClearGeneralPointer;
			auto const &AutoClearIntConstRef = AutoClearInt;
			auto const &AutoClear_zmintConstRef = AutoClear_zmint;
			auto const &AutoClear_zfp32ConstRef = AutoClear_zfp32;

			auto volatile &RawStr0VolatileRef = RawStr0;
			auto volatile &RawStr1VolatileRef = RawStr1;
			auto volatile &RawStr2VolatileRef = RawStr2;
			auto volatile &pRawStr0VolatileRef = pRawStr0;
			auto volatile &pRawStr1VolatileRef = pRawStr1;
			auto volatile &pRawStr2VolatileRef = pRawStr2;
			auto volatile &MixedStr8VolatileRef = MixedStr8;
			auto volatile &MixedStr16VolatileRef = MixedStr16;
			auto volatile &MixedStr32VolatileRef = MixedStr32;
			auto volatile &AnsiStrVolatileRef = AnsiStr;
			auto volatile &UnicodeStrVolatileRef = UnicodeStr;
			auto volatile &TestUTF8VolatileRef = TestUTF8;
			auto volatile &TestUnicode8VolatileRef = TestUnicode8;
			auto volatile &TestAnsi8VolatileRef = TestAnsi8;
			auto volatile &TestUTF16VolatileRef = TestUTF16;
			auto volatile &TestUnicode16VolatileRef = TestUnicode16;
			auto volatile &TestUnicode32VolatileRef = TestUnicode32;
			auto volatile &VectorVolatileRef = Vector;
			auto volatile &IntrusiveListVolatileRef = IntrusiveList;
			auto volatile &LinkedListVolatileRef = LinkedList;
			auto volatile &LinkedListForTreeVolatileRef = LinkedListForTree;
			auto volatile &AVLTreeVolatileRef = AVLTree;
			auto volatile &IntrusiveSingleListVolatileRef = IntrusiveSingleList;
			auto volatile &MapVolatileRef = Map;
			auto volatile &SetVolatileRef = Set;
			auto volatile &MapStrVolatileRef = MapStr;
			auto volatile &iLinkedListForTreeVolatileRef = iLinkedListForTree;
			auto volatile &iVectorVolatileRef = iVector;
			auto volatile &iIntrusiveListVolatileRef = iIntrusiveList;
			auto volatile &iLinkedListVolatileRef = iLinkedList;
			auto volatile &iAVLTreeVolatileRef = iAVLTree;
			auto volatile &iIntrusiveSingleListVolatileRef = iIntrusiveSingleList;
			auto volatile &iMapVolatileRef = iMap;
			auto volatile &iSetVolatileRef = iSet;
			auto volatile &iConstVectorVolatileRef = iConstVector;
			auto volatile &iConstIntrusiveListVolatileRef = iConstIntrusiveList;
			auto volatile &iConstLinkedListVolatileRef = iConstLinkedList;
			auto volatile &iConstAVLTreeVolatileRef = iConstAVLTree;
			auto volatile &iConstIntrusiveSingleListVolatileRef = iConstIntrusiveSingleList;
			auto volatile &iConstMapVolatileRef = iConstMap;
			auto volatile &iConstSetVolatileRef = iConstSet;
			auto volatile &TimeVolatileRef = Time;
			auto volatile &TimeSpanVolatileRef = TimeSpan;
			auto volatile &Float16VolatileRef = Float16;
			auto volatile &Float32VolatileRef = Float32;
			auto volatile &Float64VolatileRef = Float64;
			auto volatile &AggregateVolatileRef = s_Aggregate;
			auto volatile &AggregateSimpleVolatileRef = AggregateSimple;
			auto volatile &ThreadLocalVolatileRef = ThreadLocal;
			auto volatile &ExceptionVolatileRef = Exception;
			auto volatile &ExceptionStrVolatileRef = ExceptionStr;
			auto volatile &ExceptionNonTrackedStrVolatileRef = ExceptionNonTrackedStr;
			auto volatile &Variant0VolatileRef = Variant0;
			auto volatile &Variant1VolatileRef = Variant1;
			auto volatile &Variant2VolatileRef = Variant2;
			auto volatile &FloatWhatVolatileRef = FloatWhat;
			auto volatile &StackTraceVolatileRef = StackTrace;
			auto volatile &AtomicIntVolatileRef = AtomicInt;
			auto volatile &AtomicPtrVolatileRef = AtomicPtr;
			auto volatile &AtomicPtrNullVolatileRef = AtomicPtrNull;
			auto volatile &AtomicIntPtrVolatileRef = AtomicIntPtr;
			auto volatile &BigSetVolatileRef = BigSet;
			auto volatile &BigVectorVolatileRef = BigVector;
			auto volatile &BigLinkedListVolatileRef = BigLinkedList;
			auto volatile &pAutoClearVolatileRef = pAutoClear;
			auto volatile &pAutoClearDebugVolatileRef = pAutoClearDebug;
			auto volatile &pDebugPointerVolatileRef = pDebugPointer;
			auto volatile &pPointerVolatileRef = pPointer;
			auto volatile &pSharedPointerVolatileRef = pSharedPointer;
			auto volatile &pSharedPointerSupportWeakVolatileRef = pSharedPointerSupportWeak;
			auto volatile &pWeakPointerVolatileRef = pWeakPointer;
			auto volatile &pUniquePointerVolatileRef = pUniquePointer;
			auto volatile &pAutoClearNullVolatileRef = pAutoClearNull;
			auto volatile &pAutoClearDebugNullVolatileRef = pAutoClearDebugNull;
			auto volatile &pDebugPointerNullVolatileRef = pDebugPointerNull;
			auto volatile &pPointerNullVolatileRef = pPointerNull;
			auto volatile &pSharedPointerNullVolatileRef = pSharedPointerNull;
			auto volatile &pSharedPointerSupportWeakNullVolatileRef = pSharedPointerSupportWeakNull;
			auto volatile &pWeakPointerNullVolatileRef = pWeakPointerNull;
			auto volatile &pUniquePointerNullVolatileRef = pUniquePointerNull;
			auto volatile &pDebugPointerIntVolatileRef = pDebugPointerInt;
			auto volatile &pPointerIntVolatileRef = pPointerInt;
			auto volatile &pSharedPointerIntVolatileRef = pSharedPointerInt;
			auto volatile &pUniquePointerIntVolatileRef = pUniquePointerInt;
			auto volatile &ReferenceVolatileRef = Reference;
			auto volatile &IndirectionVolatileRef = Indirection;
			auto volatile &AutoClearGeneralVolatileRef = AutoClearGeneral;
			auto volatile &AutoClearGeneralPointerVolatileRef = AutoClearGeneralPointer;
			auto volatile &AutoClearIntVolatileRef = AutoClearInt;
			auto volatile &AutoClear_zmintVolatileRef = AutoClear_zmint;
			auto volatile &AutoClear_zfp32VolatileRef = AutoClear_zfp32;


			auto *RawStr0Ptr = &RawStr0;
			auto *RawStr1Ptr = &RawStr1;
			auto *RawStr2Ptr = &RawStr2;
			auto *pRawStr0Ptr = &pRawStr0;
			auto *pRawStr1Ptr = &pRawStr1;
			auto *pRawStr2Ptr = &pRawStr2;
			auto *pStr3 = &Str0;
			auto *pStr4 = &Str1;
			auto *pStr5 = &Str2;
			auto *pStr3_0 = &Str0_0;
			auto *pStr4_0 = &Str1_0;
			auto *pStr5_0 = &Str2_0;
			auto *pStr6_0 = &Str6;
			auto *pStr7_0 = &Str7;
			auto *pStr8_0 = &Str8;
			auto *pStr9_0 = &Str9;
			auto *pStr10_0 = &Str10;
			auto *pStr11_0 = &Str11;
			auto *pStr15 = &Str12;
			auto *pStr16 = &Str13;
			auto *pStr17 = &Str14;
			auto *pStr15_0 = &Str12_0;
			auto *pStr16_0 = &Str13_0;
			auto *pStr17_0 = &Str14_0;
			auto *pStr21 = &Str18;
			auto *pStr22 = &Str19;
			auto *pStr23 = &Str20;
			auto *pStr21_0 = &Str18_0;
			auto *pStr22_0 = &Str19_0;
			auto *pStr23_0 = &Str20_0;
			auto *pStr27 = &Str24;
			auto *pStr28 = &Str25;
			auto *pStr29 = &Str26;
			auto *pStr27_0 = &Str24_0;
			auto *pStr28_0 = &Str25_0;
			auto *pStr29_0 = &Str26_0;
			auto *pStr33 = &Str30;
			auto *pStr34 = &Str31;
			auto *pStr35 = &Str32;
			auto *pStr33_0 = &Str30_0;
			auto *pStr34_0 = &Str31_0;
			auto *pStr35_0 = &Str32_0;
			auto *pMixedStr8 = &MixedStr8;
			auto *pMixedStr16 = &MixedStr16;
			auto *pMixedStr32 = &MixedStr32;
			auto *pAnsiStr = &AnsiStr;
			auto *pUnicodeStr = &UnicodeStr;
			auto *pTestUTF8 = &TestUTF8;
			auto *pTestUnicode8 = &TestUnicode8;
			auto *pTestAnsi8 = &TestAnsi8;
			auto *pTestUTF16 = &TestUTF16;
			auto *pTestUnicode16 = &TestUnicode16;
			auto *pTestUnicode32 = &TestUnicode32;
			auto *pVector = &Vector;
			auto *pIntrusiveList = &IntrusiveList;
			auto *pLinkedList = &LinkedList;
			auto *pLinkedListForTree = &LinkedListForTree;
			auto *pAVLTree = &AVLTree;
			auto *pIntrusiveSingleList = &IntrusiveSingleList;
			auto *pMap = &Map;
			auto *pSet = &Set;
			auto *pMapStr = &MapStr;
			auto *piLinkedListForTree = &iLinkedListForTree;
			auto *piVector = &iVector;
			auto *piIntrusiveList = &iIntrusiveList;
			auto *piLinkedList = &iLinkedList;
			auto *piAVLTree = &iAVLTree;
			auto *piIntrusiveSingleList = &iIntrusiveSingleList;
			auto *piMap = &iMap;
			auto *piSet = &iSet;
			auto *piConstVector = &iConstVector;
			auto *piConstIntrusiveList = &iConstIntrusiveList;
			auto *piConstLinkedList = &iConstLinkedList;
			auto *piConstAVLTree = &iConstAVLTree;
			auto *piConstIntrusiveSingleList = &iConstIntrusiveSingleList;
			auto *piConstMap = &iConstMap;
			auto *piConstSet = &iConstSet;
			auto *pTime = &Time;
			auto *pTimeSpan = &TimeSpan;
			auto *pFloat16 = &Float16;
			auto *pFloat32 = &Float32;
			auto *pFloat64 = &Float64;
			auto *pAggregate = &s_Aggregate;
			auto *pAggregateSimple = &AggregateSimple;
			auto *pException = &Exception;
			auto *pExceptionStr = &ExceptionStr;
			auto *pExceptionNonTrackedStr = &ExceptionNonTrackedStr;
			auto *pVariant0 = &Variant0;
			auto *pVariant1 = &Variant1;
			auto *pVariant2 = &Variant2;
			auto *pFloatWhat = &FloatWhat;
			auto *pStackTrace = &StackTrace;
			auto *pAtomicInt = &AtomicInt;
			auto *pAtomicPtr = &AtomicPtr;
			auto *pAtomicPtrNull = &AtomicPtrNull;
			auto *pAtomicIntPtr = &AtomicIntPtr;
			auto *pBigSet = &BigSet;
			auto *pBigVector = &BigVector;
			auto *pBigLinkedList = &BigLinkedList;
			auto *ppAutoClear = &pAutoClear;
			auto *ppAutoClearDebug = &pAutoClearDebug;
			auto *ppDebugPointer = &pDebugPointer;
			auto *ppPointer = &pPointer;
			auto *ppSharedPointer = &pSharedPointer;
			auto *ppSharedPointerSupportWeak = &pSharedPointerSupportWeak;
			auto *ppWeakPointer = &pWeakPointer;
			auto *ppUniquePointer = &pUniquePointer;
			auto *ppAutoClearNull = &pAutoClearNull;
			auto *ppAutoClearDebugNull = &pAutoClearDebugNull;
			auto *ppDebugPointerNull = &pDebugPointerNull;
			auto *ppPointerNull = &pPointerNull;
			auto *ppSharedPointerNull = &pSharedPointerNull;
			auto *ppSharedPointerSupportWeakNull = &pSharedPointerSupportWeakNull;
			auto *ppWeakPointerNull = &pWeakPointerNull;
			auto *ppUniquePointerNull = &pUniquePointerNull;
			auto *ppDebugPointerInt = &pDebugPointerInt;
			auto *ppPointerInt = &pPointerInt;
			auto *ppSharedPointerInt = &pSharedPointerInt;
			auto *ppUniquePointerInt = &pUniquePointerInt;
			auto *pReference = &Reference;
			auto *pIndirection = &Indirection;
			auto *pAutoClearGeneral = &AutoClearGeneral;
			auto *pAutoClearGeneralPointer = &AutoClearGeneralPointer;
			auto *pAutoClearInt = &AutoClearInt;
			auto *pAutoClear_zmint = &AutoClear_zmint;
			auto *pAutoClear_zfp32 = &AutoClear_zfp32;


			auto **RawStr0PtrPtr = &RawStr0Ptr;
			auto **RawStr1PtrPtr = &RawStr1Ptr;
			auto **RawStr2PtrPtr = &RawStr2Ptr;
			auto **ppRawStr0Ptr = &pRawStr0Ptr;
			auto **ppRawStr1Ptr = &pRawStr1Ptr;
			auto **ppRawStr2Ptr = &pRawStr2Ptr;
			auto **ppStr3 = &pStr3;
			auto **ppStr4 = &pStr4;
			auto **ppStr5 = &pStr5;
			auto **ppStr3_0 = &pStr3_0;
			auto **ppStr4_0 = &pStr4_0;
			auto **ppStr5_0 = &pStr5_0;
			auto **ppStr6_0 = &pStr6_0;
			auto **ppStr7_0 = &pStr7_0;
			auto **ppStr8_0 = &pStr8_0;
			auto **ppStr9_0 = &pStr9_0;
			auto **ppStr10_0 = &pStr10_0;
			auto **ppStr11_0 = &pStr11_0;
			auto **ppStr15 = &pStr15;
			auto **ppStr16 = &pStr16;
			auto **ppStr17 = &pStr17;
			auto **ppStr15_0 = &pStr15_0;
			auto **ppStr16_0 = &pStr16_0;
			auto **ppStr17_0 = &pStr17_0;
			auto **ppStr21 = &pStr21;
			auto **ppStr22 = &pStr22;
			auto **ppStr23 = &pStr23;
			auto **ppStr21_0 = &pStr21_0;
			auto **ppStr22_0 = &pStr22_0;
			auto **ppStr23_0 = &pStr23_0;
			auto **ppStr27 = &pStr27;
			auto **ppStr28 = &pStr28;
			auto **ppStr29 = &pStr29;
			auto **ppStr27_0 = &pStr27_0;
			auto **ppStr28_0 = &pStr28_0;
			auto **ppStr29_0 = &pStr29_0;
			auto **ppStr33 = &pStr33;
			auto **ppStr34 = &pStr34;
			auto **ppStr35 = &pStr35;
			auto **ppStr33_0 = &pStr33_0;
			auto **ppStr34_0 = &pStr34_0;
			auto **ppStr35_0 = &pStr35_0;
			auto **ppMixedStr8 = &pMixedStr8;
			auto **ppMixedStr16 = &pMixedStr16;
			auto **ppMixedStr32 = &pMixedStr32;
			auto **ppAnsiStr = &pAnsiStr;
			auto **ppUnicodeStr = &pUnicodeStr;
			auto **ppTestUTF8 = &pTestUTF8;
			auto **ppTestUnicode8 = &pTestUnicode8;
			auto **ppTestAnsi8 = &pTestAnsi8;
			auto **ppTestUTF16 = &pTestUTF16;
			auto **ppTestUnicode16 = &pTestUnicode16;
			auto **ppTestUnicode32 = &pTestUnicode32;
			auto **ppVector = &pVector;
			auto **ppIntrusiveList = &pIntrusiveList;
			auto **ppLinkedList = &pLinkedList;
			auto **ppLinkedListForTree = &pLinkedListForTree;
			auto **ppAVLTree = &pAVLTree;
			auto **ppIntrusiveSingleList = &pIntrusiveSingleList;
			auto **ppMap = &pMap;
			auto **ppSet = &pSet;
			auto **ppMapStr = &pMapStr;
			auto **ppiLinkedListForTree = &piLinkedListForTree;
			auto **ppiVector = &piVector;
			auto **ppiIntrusiveList = &piIntrusiveList;
			auto **ppiLinkedList = &piLinkedList;
			auto **ppiAVLTree = &piAVLTree;
			auto **ppiIntrusiveSingleList = &piIntrusiveSingleList;
			auto **ppiMap = &piMap;
			auto **ppiSet = &piSet;
			auto **ppiConstVector = &piConstVector;
			auto **ppiConstIntrusiveList = &piConstIntrusiveList;
			auto **ppiConstLinkedList = &piConstLinkedList;
			auto **ppiConstAVLTree = &piConstAVLTree;
			auto **ppiConstIntrusiveSingleList = &piConstIntrusiveSingleList;
			auto **ppiConstMap = &piConstMap;
			auto **ppiConstSet = &piConstSet;
			auto **ppTime = &pTime;
			auto **ppTimeSpan = &pTimeSpan;
			auto **ppFloat16 = &pFloat16;
			auto **ppFloat32 = &pFloat32;
			auto **ppFloat64 = &pFloat64;
			auto **ppAggregate = &pAggregate;
			auto **ppAggregateSimple = &pAggregateSimple;
			auto **ppException = &pException;
			auto **ppExceptionStr = &pExceptionStr;
			auto **ppExceptionNonTrackedStr = &pExceptionNonTrackedStr;
			auto **ppVariant0 = &pVariant0;
			auto **ppVariant1 = &pVariant1;
			auto **ppVariant2 = &pVariant2;
			auto **ppFloatWhat = &pFloatWhat;
			auto **ppStackTrace = &pStackTrace;
			auto **ppAtomicInt = &pAtomicInt;
			auto **ppAtomicPtr = &pAtomicPtr;
			auto **ppAtomicPtrNull = &pAtomicPtrNull;
			auto **ppAtomicIntPtr = &pAtomicIntPtr;
			auto **ppBigSet = &pBigSet;
			auto **ppBigVector = &pBigVector;
			auto **ppBigLinkedList = &pBigLinkedList;
			auto **pppAutoClear = &ppAutoClear;
			auto **pppAutoClearDebug = &ppAutoClearDebug;
			auto **pppDebugPointer = &ppDebugPointer;
			auto **pppPointer = &ppPointer;
			auto **pppSharedPointer = &ppSharedPointer;
			auto **pppSharedPointerSupportWeak = &ppSharedPointerSupportWeak;
			auto **pppWeakPointer = &ppWeakPointer;
			auto **pppUniquePointer = &ppUniquePointer;
			auto **pppAutoClearNull = &ppAutoClearNull;
			auto **pppAutoClearDebugNull = &ppAutoClearDebugNull;
			auto **pppDebugPointerNull = &ppDebugPointerNull;
			auto **pppPointerNull = &ppPointerNull;
			auto **pppSharedPointerNull = &ppSharedPointerNull;
			auto **pppSharedPointerSupportWeakNull = &ppSharedPointerSupportWeakNull;
			auto **pppWeakPointerNull = &ppWeakPointerNull;
			auto **pppUniquePointerNull = &ppUniquePointerNull;
			auto **pppDebugPointerInt = &ppDebugPointerInt;
			auto **pppPointerInt = &ppPointerInt;
			auto **pppSharedPointerInt = &ppSharedPointerInt;
			auto **pppUniquePointerInt = &ppUniquePointerInt;
			auto **ppReference = &pReference;
			auto **ppIndirection = &pIndirection;
			auto **ppAutoClearGeneral = &pAutoClearGeneral;
			auto **ppAutoClearGeneralPointer = &pAutoClearGeneralPointer;
			auto **ppAutoClearInt = &pAutoClearInt;
			auto **ppAutoClear_zmint = &pAutoClear_zmint;
			auto **ppAutoClear_zfp32 = &pAutoClear_zfp32;

			int x1 = 0;
			int x2 = 0;

#define DKeepDebugVisualizerVariableActive(d_Variable) NSys::fg_Compiler_MakeActive((void const *)__builtin_addressof(d_Variable))
			DKeepDebugVisualizerVariableActive(ExpectLinuxFail);
			DKeepDebugVisualizerVariableActive(Str0);
			DKeepDebugVisualizerVariableActive(Str1);
			DKeepDebugVisualizerVariableActive(Str2);
			DKeepDebugVisualizerVariableActive(RawStr0);
			DKeepDebugVisualizerVariableActive(RawStr1);
			DKeepDebugVisualizerVariableActive(RawStr2);
			DKeepDebugVisualizerVariableActive(pRawStr0);
			DKeepDebugVisualizerVariableActive(pRawStr1);
			DKeepDebugVisualizerVariableActive(pRawStr2);
			DKeepDebugVisualizerVariableActive(Str0_0);
			DKeepDebugVisualizerVariableActive(Str1_0);
			DKeepDebugVisualizerVariableActive(Str2_0);
			DKeepDebugVisualizerVariableActive(Str6);
			DKeepDebugVisualizerVariableActive(Str7);
			DKeepDebugVisualizerVariableActive(Str8);
			DKeepDebugVisualizerVariableActive(Str9);
			DKeepDebugVisualizerVariableActive(Str10);
			DKeepDebugVisualizerVariableActive(Str11);
			DKeepDebugVisualizerVariableActive(Str12);
			DKeepDebugVisualizerVariableActive(Str13);
			DKeepDebugVisualizerVariableActive(Str14);
			DKeepDebugVisualizerVariableActive(Str12_0);
			DKeepDebugVisualizerVariableActive(Str13_0);
			DKeepDebugVisualizerVariableActive(Str14_0);
			DKeepDebugVisualizerVariableActive(Str18);
			DKeepDebugVisualizerVariableActive(Str19);
			DKeepDebugVisualizerVariableActive(Str20);
			DKeepDebugVisualizerVariableActive(Str18_0);
			DKeepDebugVisualizerVariableActive(Str19_0);
			DKeepDebugVisualizerVariableActive(Str20_0);
			DKeepDebugVisualizerVariableActive(Str24);
			DKeepDebugVisualizerVariableActive(Str25);
			DKeepDebugVisualizerVariableActive(Str26);
			DKeepDebugVisualizerVariableActive(Str24_0);
			DKeepDebugVisualizerVariableActive(Str25_0);
			DKeepDebugVisualizerVariableActive(Str26_0);
			DKeepDebugVisualizerVariableActive(Str30);
			DKeepDebugVisualizerVariableActive(Str31);
			DKeepDebugVisualizerVariableActive(Str32);
			DKeepDebugVisualizerVariableActive(Str30_0);
			DKeepDebugVisualizerVariableActive(Str31_0);
			DKeepDebugVisualizerVariableActive(Str32_0);
			DKeepDebugVisualizerVariableActive(MixedStr8);
			DKeepDebugVisualizerVariableActive(MixedStr16);
			DKeepDebugVisualizerVariableActive(MixedStr32);
			DKeepDebugVisualizerVariableActive(AnsiStr);
			DKeepDebugVisualizerVariableActive(UnicodeStr);
			DKeepDebugVisualizerVariableActive(TestUTF8);
			DKeepDebugVisualizerVariableActive(TestUnicode8);
			DKeepDebugVisualizerVariableActive(TestAnsi8);
			DKeepDebugVisualizerVariableActive(TestUTF16);
			DKeepDebugVisualizerVariableActive(TestUnicode16);
			DKeepDebugVisualizerVariableActive(TestUnicode32);
			DKeepDebugVisualizerVariableActive(Vector);
			DKeepDebugVisualizerVariableActive(IntrusiveList);
			DKeepDebugVisualizerVariableActive(LinkedList);
			DKeepDebugVisualizerVariableActive(Vector2);
			DKeepDebugVisualizerVariableActive(pTestLinked);
			DKeepDebugVisualizerVariableActive(Vector3);
			DKeepDebugVisualizerVariableActive(LinkedListForTree);
			DKeepDebugVisualizerVariableActive(AVLTree);
			DKeepDebugVisualizerVariableActive(IntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(Map);
			DKeepDebugVisualizerVariableActive(MapWithPool);
			DKeepDebugVisualizerVariableActive(Set);
			DKeepDebugVisualizerVariableActive(SetWithPool);
			DKeepDebugVisualizerVariableActive(MapStr);
			DKeepDebugVisualizerVariableActive(iLinkedListForTree);
			DKeepDebugVisualizerVariableActive(iVector);
			DKeepDebugVisualizerVariableActive(iIntrusiveList);
			DKeepDebugVisualizerVariableActive(iLinkedList);
			DKeepDebugVisualizerVariableActive(iAVLTree);
			DKeepDebugVisualizerVariableActive(iIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(iMap);
			DKeepDebugVisualizerVariableActive(iSet);
			DKeepDebugVisualizerVariableActive(iManyValues);
			DKeepDebugVisualizerVariableActive(iConstVector);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveList);
			DKeepDebugVisualizerVariableActive(iConstLinkedList);
			DKeepDebugVisualizerVariableActive(iConstAVLTree);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(iConstMap);
			DKeepDebugVisualizerVariableActive(iConstSet);
			DKeepDebugVisualizerVariableActive(iConstManyValues);
			DKeepDebugVisualizerVariableActive(fMakeEmpty);
			DKeepDebugVisualizerVariableActive(iVectorEmpty);
			DKeepDebugVisualizerVariableActive(iIntrusiveListEmpty);
			DKeepDebugVisualizerVariableActive(iLinkedListEmpty);
			DKeepDebugVisualizerVariableActive(iAVLTreeEmpty);
			DKeepDebugVisualizerVariableActive(iIntrusiveSingleListEmpty);
			DKeepDebugVisualizerVariableActive(iMapEmpty);
			DKeepDebugVisualizerVariableActive(iSetEmtpy);
			DKeepDebugVisualizerVariableActive(Time);
			DKeepDebugVisualizerVariableActive(TimeSpan);
			DKeepDebugVisualizerVariableActive(StartOfTime);
			DKeepDebugVisualizerVariableActive(EndOfTime);
			DKeepDebugVisualizerVariableActive(AlmostStartOfTime);
			DKeepDebugVisualizerVariableActive(AlmostEndOfTime);
			DKeepDebugVisualizerVariableActive(Float16);
			DKeepDebugVisualizerVariableActive(Float16_2);
			DKeepDebugVisualizerVariableActive(Float32);
			DKeepDebugVisualizerVariableActive(Float32_Inf);
			DKeepDebugVisualizerVariableActive(Float32_NegInf);
			DKeepDebugVisualizerVariableActive(Float32_SNan);
			DKeepDebugVisualizerVariableActive(Float32_QNan);
			DKeepDebugVisualizerVariableActive(Float32_NegSNan);
			DKeepDebugVisualizerVariableActive(Float32_NegQNan);
			DKeepDebugVisualizerVariableActive(Float32_Smallest);
			DKeepDebugVisualizerVariableActive(Float32_NegSmallest);
			DKeepDebugVisualizerVariableActive(Float32_SmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float32_NegSmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float32Emu);
			DKeepDebugVisualizerVariableActive(Float32Emu_Inf);
			DKeepDebugVisualizerVariableActive(Float32Emu_NegInf);
			DKeepDebugVisualizerVariableActive(Float32Emu_SNan);
			DKeepDebugVisualizerVariableActive(Float32Emu_QNan);
			DKeepDebugVisualizerVariableActive(Float32Emu_NegSNan);
			DKeepDebugVisualizerVariableActive(Float32Emu_NegQNan);
			DKeepDebugVisualizerVariableActive(Float32Emu_Smallest);
			DKeepDebugVisualizerVariableActive(Float32Emu_NegSmallest);
			DKeepDebugVisualizerVariableActive(Float32Emu_SmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float32Emu_NegSmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float64);
			DKeepDebugVisualizerVariableActive(Float64_Inf);
			DKeepDebugVisualizerVariableActive(Float64_NegInf);
			DKeepDebugVisualizerVariableActive(Float64_SNan);
			DKeepDebugVisualizerVariableActive(Float64_QNan);
			DKeepDebugVisualizerVariableActive(Float64_NegSNan);
			DKeepDebugVisualizerVariableActive(Float64_NegQNan);
			DKeepDebugVisualizerVariableActive(Float64_Smallest);
			DKeepDebugVisualizerVariableActive(Float64_NegSmallest);
			DKeepDebugVisualizerVariableActive(Float64_SmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float64_NegSmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float64Emu);
			DKeepDebugVisualizerVariableActive(Float64Emu_Inf);
			DKeepDebugVisualizerVariableActive(Float64Emu_NegInf);
			DKeepDebugVisualizerVariableActive(Float64Emu_SNan);
			DKeepDebugVisualizerVariableActive(Float64Emu_QNan);
			DKeepDebugVisualizerVariableActive(Float64Emu_NegSNan);
			DKeepDebugVisualizerVariableActive(Float64Emu_NegQNan);
			DKeepDebugVisualizerVariableActive(Float64Emu_Smallest);
			DKeepDebugVisualizerVariableActive(Float64Emu_NegSmallest);
			DKeepDebugVisualizerVariableActive(Float64Emu_SmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float64Emu_NegSmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float80);
			DKeepDebugVisualizerVariableActive(Float80Emu);
			DKeepDebugVisualizerVariableActive(Float256);
			DKeepDebugVisualizerVariableActive(Float256_Inf);
			DKeepDebugVisualizerVariableActive(Float256_NegINf);
			DKeepDebugVisualizerVariableActive(Float256_SNan);
			DKeepDebugVisualizerVariableActive(Float256_QNan);
			DKeepDebugVisualizerVariableActive(Float256_NegSNan);
			DKeepDebugVisualizerVariableActive(Float256_NegQNan);
			DKeepDebugVisualizerVariableActive(Float256_Smallest);
			DKeepDebugVisualizerVariableActive(Float256_NegSmallest);
			DKeepDebugVisualizerVariableActive(Float256_SmallestDenormal);
			DKeepDebugVisualizerVariableActive(Float256_NegSmallestDenormal);
			DKeepDebugVisualizerVariableActive(UFloat16);
			DKeepDebugVisualizerVariableActive(UFloat32);
			DKeepDebugVisualizerVariableActive(UFloat64_Inf);
			DKeepDebugVisualizerVariableActive(UFloat64_QNan);
			DKeepDebugVisualizerVariableActive(UFloat64_Smallest);
			DKeepDebugVisualizerVariableActive(UFloat64_SmallestDenormal);
			DKeepDebugVisualizerVariableActive(s_Aggregate);
			DKeepDebugVisualizerVariableActive(s_AggregateEmpty);
			DKeepDebugVisualizerVariableActive(CleanupAggregate);
			DKeepDebugVisualizerVariableActive(AggregateSimple);
			DKeepDebugVisualizerVariableActive(ThreadLocal);
			DKeepDebugVisualizerVariableActive(ThreadLocalClass);
			DKeepDebugVisualizerVariableActive(ThreadLocalDynamic);
			DKeepDebugVisualizerVariableActive(Exception);
			DKeepDebugVisualizerVariableActive(ExceptionStr);
			DKeepDebugVisualizerVariableActive(ExceptionNonTrackedStr);
			DKeepDebugVisualizerVariableActive(FileException);
			DKeepDebugVisualizerVariableActive(Variant0);
			DKeepDebugVisualizerVariableActive(Variant1);
			DKeepDebugVisualizerVariableActive(Variant2);
			DKeepDebugVisualizerVariableActive(Variant3);
			DKeepDebugVisualizerVariableActive(VoidVariant);
			DKeepDebugVisualizerVariableActive(FloatWhat);
			DKeepDebugVisualizerVariableActive(TaggedInteger);
			DKeepDebugVisualizerVariableActive(StreamableVariant0);
			DKeepDebugVisualizerVariableActive(StreamableVariant1);
			DKeepDebugVisualizerVariableActive(StreamableVariant2);
			DKeepDebugVisualizerVariableActive(fTest);
			DKeepDebugVisualizerVariableActive(TestLinkedLamba);
			DKeepDebugVisualizerVariableActive(StackTrace);
			DKeepDebugVisualizerVariableActive(AtomicInt);
			DKeepDebugVisualizerVariableActive(AtomicPtr);
			DKeepDebugVisualizerVariableActive(AtomicPtrNull);
			DKeepDebugVisualizerVariableActive(TestInt);
			DKeepDebugVisualizerVariableActive(AtomicIntPtr);
			DKeepDebugVisualizerVariableActive(BigSet);
			DKeepDebugVisualizerVariableActive(BigVector);
			DKeepDebugVisualizerVariableActive(BigLinkedList);
			DKeepDebugVisualizerVariableActive(VectorLooped);
			DKeepDebugVisualizerVariableActive(IntrusiveListLooped);
			DKeepDebugVisualizerVariableActive(Test2);
			DKeepDebugVisualizerVariableActive(pAutoClear);
			DKeepDebugVisualizerVariableActive(pAutoClearDebug);
			DKeepDebugVisualizerVariableActive(pDebugPointer);
			DKeepDebugVisualizerVariableActive(pPointer);
			DKeepDebugVisualizerVariableActive(pSharedPointer);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeak);
			DKeepDebugVisualizerVariableActive(pWeakPointer);
			DKeepDebugVisualizerVariableActive(pUniquePointer);
			DKeepDebugVisualizerVariableActive(pAutoClearNull);
			DKeepDebugVisualizerVariableActive(pAutoClearDebugNull);
			DKeepDebugVisualizerVariableActive(pDebugPointerNull);
			DKeepDebugVisualizerVariableActive(pPointerNull);
			DKeepDebugVisualizerVariableActive(pSharedPointerNull);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeakNull);
			DKeepDebugVisualizerVariableActive(pWeakPointerNull);
			DKeepDebugVisualizerVariableActive(pUniquePointerNull);
			DKeepDebugVisualizerVariableActive(Data);
			DKeepDebugVisualizerVariableActive(pDebugPointerInt);
			DKeepDebugVisualizerVariableActive(pPointerInt);
			DKeepDebugVisualizerVariableActive(pSharedPointerInt);
			DKeepDebugVisualizerVariableActive(pUniquePointerInt);
			DKeepDebugVisualizerVariableActive(pStrNullPtr);
			DKeepDebugVisualizerVariableActive(Reference);
			DKeepDebugVisualizerVariableActive(Indirection);
			DKeepDebugVisualizerVariableActive(Registry);
			DKeepDebugVisualizerVariableActive(RegistryPreserve);
			DKeepDebugVisualizerVariableActive(RegistryPreserveOrder);
			DKeepDebugVisualizerVariableActive(AutoClearGeneral);
			DKeepDebugVisualizerVariableActive(AutoClearGeneralPointer);
			DKeepDebugVisualizerVariableActive(AutoClearInt);
			DKeepDebugVisualizerVariableActive(AutoClear_zmint);
			DKeepDebugVisualizerVariableActive(AutoClear_zfp32);
			DKeepDebugVisualizerVariableActive(SecureByteVector);
			DKeepDebugVisualizerVariableActive(Json);
			DKeepDebugVisualizerVariableActive(EnhancedJson);
			DKeepDebugVisualizerVariableActive(JsonOrderedYaml);
			DKeepDebugVisualizerVariableActive(JsonSortedYaml);
			DKeepDebugVisualizerVariableActive(JsonOrdered);
			DKeepDebugVisualizerVariableActive(EnhancedJsonOrdered);
			DKeepDebugVisualizerVariableActive(EnhancedJsonOrderedYaml);
			DKeepDebugVisualizerVariableActive(EnhancedJsonSortedYaml);
			DKeepDebugVisualizerVariableActive(fTestLambda);
			DKeepDebugVisualizerVariableActive(fTestLambdaBig);
			DKeepDebugVisualizerVariableActive(Function0);
			DKeepDebugVisualizerVariableActive(Function1);
			DKeepDebugVisualizerVariableActive(Function2);
			DKeepDebugVisualizerVariableActive(Function3);
			DKeepDebugVisualizerVariableActive(FunctionFunctor);
			DKeepDebugVisualizerVariableActive(FunctionFunctorMutable);
			DKeepDebugVisualizerVariableActive(FunctionFunctorMovable);
			DKeepDebugVisualizerVariableActive(FunctionFunctorMutableConstTemplateParam);
			DKeepDebugVisualizerVariableActive(FunctionFunctorConstThisTagConstTemplateParam);
			DKeepDebugVisualizerVariableActive(FunctionExternalLambda);
			DKeepDebugVisualizerVariableActive(FunctionBig);
			DKeepDebugVisualizerVariableActive(FunctionEmpty);
			DKeepDebugVisualizerVariableActive(TestActor);
			DKeepDebugVisualizerVariableActive(TestActorWeak);
			DKeepDebugVisualizerVariableActive(TestActorEmpty);
			DKeepDebugVisualizerVariableActive(TestActorEmptyWeak);
			DKeepDebugVisualizerVariableActive(RawStr0Ref);
			DKeepDebugVisualizerVariableActive(RawStr1Ref);
			DKeepDebugVisualizerVariableActive(RawStr2Ref);
			DKeepDebugVisualizerVariableActive(pRawStr0Ref);
			DKeepDebugVisualizerVariableActive(pRawStr1Ref);
			DKeepDebugVisualizerVariableActive(pRawStr2Ref);
			DKeepDebugVisualizerVariableActive(MixedStr8Ref);
			DKeepDebugVisualizerVariableActive(MixedStr16Ref);
			DKeepDebugVisualizerVariableActive(MixedStr32Ref);
			DKeepDebugVisualizerVariableActive(AnsiStrRef);
			DKeepDebugVisualizerVariableActive(UnicodeStrRef);
			DKeepDebugVisualizerVariableActive(TestUTF8Ref);
			DKeepDebugVisualizerVariableActive(TestUnicode8Ref);
			DKeepDebugVisualizerVariableActive(TestAnsi8Ref);
			DKeepDebugVisualizerVariableActive(TestUTF16Ref);
			DKeepDebugVisualizerVariableActive(TestUnicode16Ref);
			DKeepDebugVisualizerVariableActive(TestUnicode32Ref);
			DKeepDebugVisualizerVariableActive(VectorRef);
			DKeepDebugVisualizerVariableActive(IntrusiveListRef);
			DKeepDebugVisualizerVariableActive(LinkedListRef);
			DKeepDebugVisualizerVariableActive(LinkedListForTreeRef);
			DKeepDebugVisualizerVariableActive(AVLTreeRef);
			DKeepDebugVisualizerVariableActive(IntrusiveSingleListRef);
			DKeepDebugVisualizerVariableActive(MapRef);
			DKeepDebugVisualizerVariableActive(SetRef);
			DKeepDebugVisualizerVariableActive(MapStrRef);
			DKeepDebugVisualizerVariableActive(iLinkedListForTreeRef);
			DKeepDebugVisualizerVariableActive(iVectorRef);
			DKeepDebugVisualizerVariableActive(iIntrusiveListRef);
			DKeepDebugVisualizerVariableActive(iLinkedListRef);
			DKeepDebugVisualizerVariableActive(iAVLTreeRef);
			DKeepDebugVisualizerVariableActive(iIntrusiveSingleListRef);
			DKeepDebugVisualizerVariableActive(iMapRef);
			DKeepDebugVisualizerVariableActive(iSetRef);
			DKeepDebugVisualizerVariableActive(iConstVectorRef);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveListRef);
			DKeepDebugVisualizerVariableActive(iConstLinkedListRef);
			DKeepDebugVisualizerVariableActive(iConstAVLTreeRef);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveSingleListRef);
			DKeepDebugVisualizerVariableActive(iConstMapRef);
			DKeepDebugVisualizerVariableActive(iConstSetRef);
			DKeepDebugVisualizerVariableActive(TimeRef);
			DKeepDebugVisualizerVariableActive(TimeSpanRef);
			DKeepDebugVisualizerVariableActive(Float16Ref);
			DKeepDebugVisualizerVariableActive(Float32Ref);
			DKeepDebugVisualizerVariableActive(Float64Ref);
			DKeepDebugVisualizerVariableActive(AggregateRef);
			DKeepDebugVisualizerVariableActive(AggregateSimpleRef);
			DKeepDebugVisualizerVariableActive(ThreadLocalRef);
			DKeepDebugVisualizerVariableActive(ExceptionRef);
			DKeepDebugVisualizerVariableActive(ExceptionStrRef);
			DKeepDebugVisualizerVariableActive(ExceptionNonTrackedStrRef);
			DKeepDebugVisualizerVariableActive(Variant0Ref);
			DKeepDebugVisualizerVariableActive(Variant1Ref);
			DKeepDebugVisualizerVariableActive(Variant2Ref);
			DKeepDebugVisualizerVariableActive(FloatWhatRef);
			DKeepDebugVisualizerVariableActive(StackTraceRef);
			DKeepDebugVisualizerVariableActive(AtomicIntRef);
			DKeepDebugVisualizerVariableActive(AtomicPtrRef);
			DKeepDebugVisualizerVariableActive(AtomicPtrNullRef);
			DKeepDebugVisualizerVariableActive(AtomicIntPtrRef);
			DKeepDebugVisualizerVariableActive(BigSetRef);
			DKeepDebugVisualizerVariableActive(BigVectorRef);
			DKeepDebugVisualizerVariableActive(BigLinkedListRef);
			DKeepDebugVisualizerVariableActive(pAutoClearRef);
			DKeepDebugVisualizerVariableActive(pAutoClearDebugRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerRef);
			DKeepDebugVisualizerVariableActive(pPointerRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeakRef);
			DKeepDebugVisualizerVariableActive(pWeakPointerRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerRef);
			DKeepDebugVisualizerVariableActive(pAutoClearNullRef);
			DKeepDebugVisualizerVariableActive(pAutoClearDebugNullRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerNullRef);
			DKeepDebugVisualizerVariableActive(pPointerNullRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerNullRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeakNullRef);
			DKeepDebugVisualizerVariableActive(pWeakPointerNullRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerNullRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerIntRef);
			DKeepDebugVisualizerVariableActive(pPointerIntRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerIntRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerIntRef);
			DKeepDebugVisualizerVariableActive(ReferenceRef);
			DKeepDebugVisualizerVariableActive(IndirectionRef);
			DKeepDebugVisualizerVariableActive(AutoClearGeneralRef);
			DKeepDebugVisualizerVariableActive(AutoClearGeneralPointerRef);
			DKeepDebugVisualizerVariableActive(AutoClearIntRef);
			DKeepDebugVisualizerVariableActive(AutoClear_zmintRef);
			DKeepDebugVisualizerVariableActive(AutoClear_zfp32Ref);
			DKeepDebugVisualizerVariableActive(RawStr0ConstRef);
			DKeepDebugVisualizerVariableActive(RawStr1ConstRef);
			DKeepDebugVisualizerVariableActive(RawStr2ConstRef);
			DKeepDebugVisualizerVariableActive(pRawStr0ConstRef);
			DKeepDebugVisualizerVariableActive(pRawStr1ConstRef);
			DKeepDebugVisualizerVariableActive(pRawStr2ConstRef);
			DKeepDebugVisualizerVariableActive(MixedStr8ConstRef);
			DKeepDebugVisualizerVariableActive(MixedStr16ConstRef);
			DKeepDebugVisualizerVariableActive(MixedStr32ConstRef);
			DKeepDebugVisualizerVariableActive(AnsiStrConstRef);
			DKeepDebugVisualizerVariableActive(UnicodeStrConstRef);
			DKeepDebugVisualizerVariableActive(TestUTF8ConstRef);
			DKeepDebugVisualizerVariableActive(TestUnicode8ConstRef);
			DKeepDebugVisualizerVariableActive(TestAnsi8ConstRef);
			DKeepDebugVisualizerVariableActive(TestUTF16ConstRef);
			DKeepDebugVisualizerVariableActive(TestUnicode16ConstRef);
			DKeepDebugVisualizerVariableActive(TestUnicode32ConstRef);
			DKeepDebugVisualizerVariableActive(VectorConstRef);
			DKeepDebugVisualizerVariableActive(IntrusiveListConstRef);
			DKeepDebugVisualizerVariableActive(LinkedListConstRef);
			DKeepDebugVisualizerVariableActive(LinkedListForTreeConstRef);
			DKeepDebugVisualizerVariableActive(AVLTreeConstRef);
			DKeepDebugVisualizerVariableActive(IntrusiveSingleListConstRef);
			DKeepDebugVisualizerVariableActive(MapConstRef);
			DKeepDebugVisualizerVariableActive(SetConstRef);
			DKeepDebugVisualizerVariableActive(MapStrConstRef);
			DKeepDebugVisualizerVariableActive(iLinkedListForTreeConstRef);
			DKeepDebugVisualizerVariableActive(iVectorConstRef);
			DKeepDebugVisualizerVariableActive(iIntrusiveListConstRef);
			DKeepDebugVisualizerVariableActive(iLinkedListConstRef);
			DKeepDebugVisualizerVariableActive(iAVLTreeConstRef);
			DKeepDebugVisualizerVariableActive(iIntrusiveSingleListConstRef);
			DKeepDebugVisualizerVariableActive(iMapConstRef);
			DKeepDebugVisualizerVariableActive(iSetConstRef);
			DKeepDebugVisualizerVariableActive(iConstVectorConstRef);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveListConstRef);
			DKeepDebugVisualizerVariableActive(iConstLinkedListConstRef);
			DKeepDebugVisualizerVariableActive(iConstAVLTreeConstRef);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveSingleListConstRef);
			DKeepDebugVisualizerVariableActive(iConstMapConstRef);
			DKeepDebugVisualizerVariableActive(iConstSetConstRef);
			DKeepDebugVisualizerVariableActive(TimeConstRef);
			DKeepDebugVisualizerVariableActive(TimeSpanConstRef);
			DKeepDebugVisualizerVariableActive(Float16ConstRef);
			DKeepDebugVisualizerVariableActive(Float32ConstRef);
			DKeepDebugVisualizerVariableActive(Float64ConstRef);
			DKeepDebugVisualizerVariableActive(AggregateConstRef);
			DKeepDebugVisualizerVariableActive(AggregateSimpleConstRef);
			DKeepDebugVisualizerVariableActive(ThreadLocalConstRef);
			DKeepDebugVisualizerVariableActive(ExceptionConstRef);
			DKeepDebugVisualizerVariableActive(ExceptionStrConstRef);
			DKeepDebugVisualizerVariableActive(ExceptionNonTrackedStrConstRef);
			DKeepDebugVisualizerVariableActive(Variant0ConstRef);
			DKeepDebugVisualizerVariableActive(Variant1ConstRef);
			DKeepDebugVisualizerVariableActive(Variant2ConstRef);
			DKeepDebugVisualizerVariableActive(FloatWhatConstRef);
			DKeepDebugVisualizerVariableActive(StackTraceConstRef);
			DKeepDebugVisualizerVariableActive(AtomicIntConstRef);
			DKeepDebugVisualizerVariableActive(AtomicPtrConstRef);
			DKeepDebugVisualizerVariableActive(AtomicPtrNullConstRef);
			DKeepDebugVisualizerVariableActive(AtomicIntPtrConstRef);
			DKeepDebugVisualizerVariableActive(BigSetConstRef);
			DKeepDebugVisualizerVariableActive(BigVectorConstRef);
			DKeepDebugVisualizerVariableActive(BigLinkedListConstRef);
			DKeepDebugVisualizerVariableActive(pAutoClearConstRef);
			DKeepDebugVisualizerVariableActive(pAutoClearDebugConstRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerConstRef);
			DKeepDebugVisualizerVariableActive(pPointerConstRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerConstRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeakConstRef);
			DKeepDebugVisualizerVariableActive(pWeakPointerConstRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerConstRef);
			DKeepDebugVisualizerVariableActive(pAutoClearNullConstRef);
			DKeepDebugVisualizerVariableActive(pAutoClearDebugNullConstRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerNullConstRef);
			DKeepDebugVisualizerVariableActive(pPointerNullConstRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerNullConstRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeakNullConstRef);
			DKeepDebugVisualizerVariableActive(pWeakPointerNullConstRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerNullConstRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerIntConstRef);
			DKeepDebugVisualizerVariableActive(pPointerIntConstRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerIntConstRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerIntConstRef);
			DKeepDebugVisualizerVariableActive(ReferenceConstRef);
			DKeepDebugVisualizerVariableActive(IndirectionConstRef);
			DKeepDebugVisualizerVariableActive(AutoClearGeneralConstRef);
			DKeepDebugVisualizerVariableActive(AutoClearGeneralPointerConstRef);
			DKeepDebugVisualizerVariableActive(AutoClearIntConstRef);
			DKeepDebugVisualizerVariableActive(AutoClear_zmintConstRef);
			DKeepDebugVisualizerVariableActive(AutoClear_zfp32ConstRef);
			DKeepDebugVisualizerVariableActive(RawStr0VolatileRef);
			DKeepDebugVisualizerVariableActive(RawStr1VolatileRef);
			DKeepDebugVisualizerVariableActive(RawStr2VolatileRef);
			DKeepDebugVisualizerVariableActive(pRawStr0VolatileRef);
			DKeepDebugVisualizerVariableActive(pRawStr1VolatileRef);
			DKeepDebugVisualizerVariableActive(pRawStr2VolatileRef);
			DKeepDebugVisualizerVariableActive(MixedStr8VolatileRef);
			DKeepDebugVisualizerVariableActive(MixedStr16VolatileRef);
			DKeepDebugVisualizerVariableActive(MixedStr32VolatileRef);
			DKeepDebugVisualizerVariableActive(AnsiStrVolatileRef);
			DKeepDebugVisualizerVariableActive(UnicodeStrVolatileRef);
			DKeepDebugVisualizerVariableActive(TestUTF8VolatileRef);
			DKeepDebugVisualizerVariableActive(TestUnicode8VolatileRef);
			DKeepDebugVisualizerVariableActive(TestAnsi8VolatileRef);
			DKeepDebugVisualizerVariableActive(TestUTF16VolatileRef);
			DKeepDebugVisualizerVariableActive(TestUnicode16VolatileRef);
			DKeepDebugVisualizerVariableActive(TestUnicode32VolatileRef);
			DKeepDebugVisualizerVariableActive(VectorVolatileRef);
			DKeepDebugVisualizerVariableActive(IntrusiveListVolatileRef);
			DKeepDebugVisualizerVariableActive(LinkedListVolatileRef);
			DKeepDebugVisualizerVariableActive(LinkedListForTreeVolatileRef);
			DKeepDebugVisualizerVariableActive(AVLTreeVolatileRef);
			DKeepDebugVisualizerVariableActive(IntrusiveSingleListVolatileRef);
			DKeepDebugVisualizerVariableActive(MapVolatileRef);
			DKeepDebugVisualizerVariableActive(SetVolatileRef);
			DKeepDebugVisualizerVariableActive(MapStrVolatileRef);
			DKeepDebugVisualizerVariableActive(iLinkedListForTreeVolatileRef);
			DKeepDebugVisualizerVariableActive(iVectorVolatileRef);
			DKeepDebugVisualizerVariableActive(iIntrusiveListVolatileRef);
			DKeepDebugVisualizerVariableActive(iLinkedListVolatileRef);
			DKeepDebugVisualizerVariableActive(iAVLTreeVolatileRef);
			DKeepDebugVisualizerVariableActive(iIntrusiveSingleListVolatileRef);
			DKeepDebugVisualizerVariableActive(iMapVolatileRef);
			DKeepDebugVisualizerVariableActive(iSetVolatileRef);
			DKeepDebugVisualizerVariableActive(iConstVectorVolatileRef);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveListVolatileRef);
			DKeepDebugVisualizerVariableActive(iConstLinkedListVolatileRef);
			DKeepDebugVisualizerVariableActive(iConstAVLTreeVolatileRef);
			DKeepDebugVisualizerVariableActive(iConstIntrusiveSingleListVolatileRef);
			DKeepDebugVisualizerVariableActive(iConstMapVolatileRef);
			DKeepDebugVisualizerVariableActive(iConstSetVolatileRef);
			DKeepDebugVisualizerVariableActive(TimeVolatileRef);
			DKeepDebugVisualizerVariableActive(TimeSpanVolatileRef);
			DKeepDebugVisualizerVariableActive(Float16VolatileRef);
			DKeepDebugVisualizerVariableActive(Float32VolatileRef);
			DKeepDebugVisualizerVariableActive(Float64VolatileRef);
			DKeepDebugVisualizerVariableActive(AggregateVolatileRef);
			DKeepDebugVisualizerVariableActive(AggregateSimpleVolatileRef);
			DKeepDebugVisualizerVariableActive(ThreadLocalVolatileRef);
			DKeepDebugVisualizerVariableActive(ExceptionVolatileRef);
			DKeepDebugVisualizerVariableActive(ExceptionStrVolatileRef);
			DKeepDebugVisualizerVariableActive(ExceptionNonTrackedStrVolatileRef);
			DKeepDebugVisualizerVariableActive(Variant0VolatileRef);
			DKeepDebugVisualizerVariableActive(Variant1VolatileRef);
			DKeepDebugVisualizerVariableActive(Variant2VolatileRef);
			DKeepDebugVisualizerVariableActive(FloatWhatVolatileRef);
			DKeepDebugVisualizerVariableActive(StackTraceVolatileRef);
			DKeepDebugVisualizerVariableActive(AtomicIntVolatileRef);
			DKeepDebugVisualizerVariableActive(AtomicPtrVolatileRef);
			DKeepDebugVisualizerVariableActive(AtomicPtrNullVolatileRef);
			DKeepDebugVisualizerVariableActive(AtomicIntPtrVolatileRef);
			DKeepDebugVisualizerVariableActive(BigSetVolatileRef);
			DKeepDebugVisualizerVariableActive(BigVectorVolatileRef);
			DKeepDebugVisualizerVariableActive(BigLinkedListVolatileRef);
			DKeepDebugVisualizerVariableActive(pAutoClearVolatileRef);
			DKeepDebugVisualizerVariableActive(pAutoClearDebugVolatileRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerVolatileRef);
			DKeepDebugVisualizerVariableActive(pPointerVolatileRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerVolatileRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeakVolatileRef);
			DKeepDebugVisualizerVariableActive(pWeakPointerVolatileRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerVolatileRef);
			DKeepDebugVisualizerVariableActive(pAutoClearNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pAutoClearDebugNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pPointerNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerSupportWeakNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pWeakPointerNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerNullVolatileRef);
			DKeepDebugVisualizerVariableActive(pDebugPointerIntVolatileRef);
			DKeepDebugVisualizerVariableActive(pPointerIntVolatileRef);
			DKeepDebugVisualizerVariableActive(pSharedPointerIntVolatileRef);
			DKeepDebugVisualizerVariableActive(pUniquePointerIntVolatileRef);
			DKeepDebugVisualizerVariableActive(ReferenceVolatileRef);
			DKeepDebugVisualizerVariableActive(IndirectionVolatileRef);
			DKeepDebugVisualizerVariableActive(AutoClearGeneralVolatileRef);
			DKeepDebugVisualizerVariableActive(AutoClearGeneralPointerVolatileRef);
			DKeepDebugVisualizerVariableActive(AutoClearIntVolatileRef);
			DKeepDebugVisualizerVariableActive(AutoClear_zmintVolatileRef);
			DKeepDebugVisualizerVariableActive(AutoClear_zfp32VolatileRef);
			DKeepDebugVisualizerVariableActive(RawStr0Ptr);
			DKeepDebugVisualizerVariableActive(RawStr1Ptr);
			DKeepDebugVisualizerVariableActive(RawStr2Ptr);
			DKeepDebugVisualizerVariableActive(pRawStr0Ptr);
			DKeepDebugVisualizerVariableActive(pRawStr1Ptr);
			DKeepDebugVisualizerVariableActive(pRawStr2Ptr);
			DKeepDebugVisualizerVariableActive(pStr3);
			DKeepDebugVisualizerVariableActive(pStr4);
			DKeepDebugVisualizerVariableActive(pStr5);
			DKeepDebugVisualizerVariableActive(pStr3_0);
			DKeepDebugVisualizerVariableActive(pStr4_0);
			DKeepDebugVisualizerVariableActive(pStr5_0);
			DKeepDebugVisualizerVariableActive(pStr6_0);
			DKeepDebugVisualizerVariableActive(pStr7_0);
			DKeepDebugVisualizerVariableActive(pStr8_0);
			DKeepDebugVisualizerVariableActive(pStr9_0);
			DKeepDebugVisualizerVariableActive(pStr10_0);
			DKeepDebugVisualizerVariableActive(pStr11_0);
			DKeepDebugVisualizerVariableActive(pStr15);
			DKeepDebugVisualizerVariableActive(pStr16);
			DKeepDebugVisualizerVariableActive(pStr17);
			DKeepDebugVisualizerVariableActive(pStr15_0);
			DKeepDebugVisualizerVariableActive(pStr16_0);
			DKeepDebugVisualizerVariableActive(pStr17_0);
			DKeepDebugVisualizerVariableActive(pStr21);
			DKeepDebugVisualizerVariableActive(pStr22);
			DKeepDebugVisualizerVariableActive(pStr23);
			DKeepDebugVisualizerVariableActive(pStr21_0);
			DKeepDebugVisualizerVariableActive(pStr22_0);
			DKeepDebugVisualizerVariableActive(pStr23_0);
			DKeepDebugVisualizerVariableActive(pStr27);
			DKeepDebugVisualizerVariableActive(pStr28);
			DKeepDebugVisualizerVariableActive(pStr29);
			DKeepDebugVisualizerVariableActive(pStr27_0);
			DKeepDebugVisualizerVariableActive(pStr28_0);
			DKeepDebugVisualizerVariableActive(pStr29_0);
			DKeepDebugVisualizerVariableActive(pStr33);
			DKeepDebugVisualizerVariableActive(pStr34);
			DKeepDebugVisualizerVariableActive(pStr35);
			DKeepDebugVisualizerVariableActive(pStr33_0);
			DKeepDebugVisualizerVariableActive(pStr34_0);
			DKeepDebugVisualizerVariableActive(pStr35_0);
			DKeepDebugVisualizerVariableActive(pMixedStr8);
			DKeepDebugVisualizerVariableActive(pMixedStr16);
			DKeepDebugVisualizerVariableActive(pMixedStr32);
			DKeepDebugVisualizerVariableActive(pAnsiStr);
			DKeepDebugVisualizerVariableActive(pUnicodeStr);
			DKeepDebugVisualizerVariableActive(pTestUTF8);
			DKeepDebugVisualizerVariableActive(pTestUnicode8);
			DKeepDebugVisualizerVariableActive(pTestAnsi8);
			DKeepDebugVisualizerVariableActive(pTestUTF16);
			DKeepDebugVisualizerVariableActive(pTestUnicode16);
			DKeepDebugVisualizerVariableActive(pTestUnicode32);
			DKeepDebugVisualizerVariableActive(pVector);
			DKeepDebugVisualizerVariableActive(pIntrusiveList);
			DKeepDebugVisualizerVariableActive(pLinkedList);
			DKeepDebugVisualizerVariableActive(pLinkedListForTree);
			DKeepDebugVisualizerVariableActive(pAVLTree);
			DKeepDebugVisualizerVariableActive(pIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(pMap);
			DKeepDebugVisualizerVariableActive(pSet);
			DKeepDebugVisualizerVariableActive(pMapStr);
			DKeepDebugVisualizerVariableActive(piLinkedListForTree);
			DKeepDebugVisualizerVariableActive(piVector);
			DKeepDebugVisualizerVariableActive(piIntrusiveList);
			DKeepDebugVisualizerVariableActive(piLinkedList);
			DKeepDebugVisualizerVariableActive(piAVLTree);
			DKeepDebugVisualizerVariableActive(piIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(piMap);
			DKeepDebugVisualizerVariableActive(piSet);
			DKeepDebugVisualizerVariableActive(piConstVector);
			DKeepDebugVisualizerVariableActive(piConstIntrusiveList);
			DKeepDebugVisualizerVariableActive(piConstLinkedList);
			DKeepDebugVisualizerVariableActive(piConstAVLTree);
			DKeepDebugVisualizerVariableActive(piConstIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(piConstMap);
			DKeepDebugVisualizerVariableActive(piConstSet);
			DKeepDebugVisualizerVariableActive(pTime);
			DKeepDebugVisualizerVariableActive(pTimeSpan);
			DKeepDebugVisualizerVariableActive(pFloat16);
			DKeepDebugVisualizerVariableActive(pFloat32);
			DKeepDebugVisualizerVariableActive(pFloat64);
			DKeepDebugVisualizerVariableActive(pAggregate);
			DKeepDebugVisualizerVariableActive(pAggregateSimple);
			DKeepDebugVisualizerVariableActive(pException);
			DKeepDebugVisualizerVariableActive(pExceptionStr);
			DKeepDebugVisualizerVariableActive(pExceptionNonTrackedStr);
			DKeepDebugVisualizerVariableActive(pVariant0);
			DKeepDebugVisualizerVariableActive(pVariant1);
			DKeepDebugVisualizerVariableActive(pVariant2);
			DKeepDebugVisualizerVariableActive(pFloatWhat);
			DKeepDebugVisualizerVariableActive(pStackTrace);
			DKeepDebugVisualizerVariableActive(pAtomicInt);
			DKeepDebugVisualizerVariableActive(pAtomicPtr);
			DKeepDebugVisualizerVariableActive(pAtomicPtrNull);
			DKeepDebugVisualizerVariableActive(pAtomicIntPtr);
			DKeepDebugVisualizerVariableActive(pBigSet);
			DKeepDebugVisualizerVariableActive(pBigVector);
			DKeepDebugVisualizerVariableActive(pBigLinkedList);
			DKeepDebugVisualizerVariableActive(ppAutoClear);
			DKeepDebugVisualizerVariableActive(ppAutoClearDebug);
			DKeepDebugVisualizerVariableActive(ppDebugPointer);
			DKeepDebugVisualizerVariableActive(ppPointer);
			DKeepDebugVisualizerVariableActive(ppSharedPointer);
			DKeepDebugVisualizerVariableActive(ppSharedPointerSupportWeak);
			DKeepDebugVisualizerVariableActive(ppWeakPointer);
			DKeepDebugVisualizerVariableActive(ppUniquePointer);
			DKeepDebugVisualizerVariableActive(ppAutoClearNull);
			DKeepDebugVisualizerVariableActive(ppAutoClearDebugNull);
			DKeepDebugVisualizerVariableActive(ppDebugPointerNull);
			DKeepDebugVisualizerVariableActive(ppPointerNull);
			DKeepDebugVisualizerVariableActive(ppSharedPointerNull);
			DKeepDebugVisualizerVariableActive(ppSharedPointerSupportWeakNull);
			DKeepDebugVisualizerVariableActive(ppWeakPointerNull);
			DKeepDebugVisualizerVariableActive(ppUniquePointerNull);
			DKeepDebugVisualizerVariableActive(ppDebugPointerInt);
			DKeepDebugVisualizerVariableActive(ppPointerInt);
			DKeepDebugVisualizerVariableActive(ppSharedPointerInt);
			DKeepDebugVisualizerVariableActive(ppUniquePointerInt);
			DKeepDebugVisualizerVariableActive(pReference);
			DKeepDebugVisualizerVariableActive(pIndirection);
			DKeepDebugVisualizerVariableActive(pAutoClearGeneral);
			DKeepDebugVisualizerVariableActive(pAutoClearGeneralPointer);
			DKeepDebugVisualizerVariableActive(pAutoClearInt);
			DKeepDebugVisualizerVariableActive(pAutoClear_zmint);
			DKeepDebugVisualizerVariableActive(pAutoClear_zfp32);
			DKeepDebugVisualizerVariableActive(RawStr0PtrPtr);
			DKeepDebugVisualizerVariableActive(RawStr1PtrPtr);
			DKeepDebugVisualizerVariableActive(RawStr2PtrPtr);
			DKeepDebugVisualizerVariableActive(ppRawStr0Ptr);
			DKeepDebugVisualizerVariableActive(ppRawStr1Ptr);
			DKeepDebugVisualizerVariableActive(ppRawStr2Ptr);
			DKeepDebugVisualizerVariableActive(ppStr3);
			DKeepDebugVisualizerVariableActive(ppStr4);
			DKeepDebugVisualizerVariableActive(ppStr5);
			DKeepDebugVisualizerVariableActive(ppStr3_0);
			DKeepDebugVisualizerVariableActive(ppStr4_0);
			DKeepDebugVisualizerVariableActive(ppStr5_0);
			DKeepDebugVisualizerVariableActive(ppStr6_0);
			DKeepDebugVisualizerVariableActive(ppStr7_0);
			DKeepDebugVisualizerVariableActive(ppStr8_0);
			DKeepDebugVisualizerVariableActive(ppStr9_0);
			DKeepDebugVisualizerVariableActive(ppStr10_0);
			DKeepDebugVisualizerVariableActive(ppStr11_0);
			DKeepDebugVisualizerVariableActive(ppStr15);
			DKeepDebugVisualizerVariableActive(ppStr16);
			DKeepDebugVisualizerVariableActive(ppStr17);
			DKeepDebugVisualizerVariableActive(ppStr15_0);
			DKeepDebugVisualizerVariableActive(ppStr16_0);
			DKeepDebugVisualizerVariableActive(ppStr17_0);
			DKeepDebugVisualizerVariableActive(ppStr21);
			DKeepDebugVisualizerVariableActive(ppStr22);
			DKeepDebugVisualizerVariableActive(ppStr23);
			DKeepDebugVisualizerVariableActive(ppStr21_0);
			DKeepDebugVisualizerVariableActive(ppStr22_0);
			DKeepDebugVisualizerVariableActive(ppStr23_0);
			DKeepDebugVisualizerVariableActive(ppStr27);
			DKeepDebugVisualizerVariableActive(ppStr28);
			DKeepDebugVisualizerVariableActive(ppStr29);
			DKeepDebugVisualizerVariableActive(ppStr27_0);
			DKeepDebugVisualizerVariableActive(ppStr28_0);
			DKeepDebugVisualizerVariableActive(ppStr29_0);
			DKeepDebugVisualizerVariableActive(ppStr33);
			DKeepDebugVisualizerVariableActive(ppStr34);
			DKeepDebugVisualizerVariableActive(ppStr35);
			DKeepDebugVisualizerVariableActive(ppStr33_0);
			DKeepDebugVisualizerVariableActive(ppStr34_0);
			DKeepDebugVisualizerVariableActive(ppStr35_0);
			DKeepDebugVisualizerVariableActive(ppMixedStr8);
			DKeepDebugVisualizerVariableActive(ppMixedStr16);
			DKeepDebugVisualizerVariableActive(ppMixedStr32);
			DKeepDebugVisualizerVariableActive(ppAnsiStr);
			DKeepDebugVisualizerVariableActive(ppUnicodeStr);
			DKeepDebugVisualizerVariableActive(ppTestUTF8);
			DKeepDebugVisualizerVariableActive(ppTestUnicode8);
			DKeepDebugVisualizerVariableActive(ppTestAnsi8);
			DKeepDebugVisualizerVariableActive(ppTestUTF16);
			DKeepDebugVisualizerVariableActive(ppTestUnicode16);
			DKeepDebugVisualizerVariableActive(ppTestUnicode32);
			DKeepDebugVisualizerVariableActive(ppVector);
			DKeepDebugVisualizerVariableActive(ppIntrusiveList);
			DKeepDebugVisualizerVariableActive(ppLinkedList);
			DKeepDebugVisualizerVariableActive(ppLinkedListForTree);
			DKeepDebugVisualizerVariableActive(ppAVLTree);
			DKeepDebugVisualizerVariableActive(ppIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(ppMap);
			DKeepDebugVisualizerVariableActive(ppSet);
			DKeepDebugVisualizerVariableActive(ppMapStr);
			DKeepDebugVisualizerVariableActive(ppiLinkedListForTree);
			DKeepDebugVisualizerVariableActive(ppiVector);
			DKeepDebugVisualizerVariableActive(ppiIntrusiveList);
			DKeepDebugVisualizerVariableActive(ppiLinkedList);
			DKeepDebugVisualizerVariableActive(ppiAVLTree);
			DKeepDebugVisualizerVariableActive(ppiIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(ppiMap);
			DKeepDebugVisualizerVariableActive(ppiSet);
			DKeepDebugVisualizerVariableActive(ppiConstVector);
			DKeepDebugVisualizerVariableActive(ppiConstIntrusiveList);
			DKeepDebugVisualizerVariableActive(ppiConstLinkedList);
			DKeepDebugVisualizerVariableActive(ppiConstAVLTree);
			DKeepDebugVisualizerVariableActive(ppiConstIntrusiveSingleList);
			DKeepDebugVisualizerVariableActive(ppiConstMap);
			DKeepDebugVisualizerVariableActive(ppiConstSet);
			DKeepDebugVisualizerVariableActive(ppTime);
			DKeepDebugVisualizerVariableActive(ppTimeSpan);
			DKeepDebugVisualizerVariableActive(ppFloat16);
			DKeepDebugVisualizerVariableActive(ppFloat32);
			DKeepDebugVisualizerVariableActive(ppFloat64);
			DKeepDebugVisualizerVariableActive(ppAggregate);
			DKeepDebugVisualizerVariableActive(ppAggregateSimple);
			DKeepDebugVisualizerVariableActive(ppException);
			DKeepDebugVisualizerVariableActive(ppExceptionStr);
			DKeepDebugVisualizerVariableActive(ppExceptionNonTrackedStr);
			DKeepDebugVisualizerVariableActive(ppVariant0);
			DKeepDebugVisualizerVariableActive(ppVariant1);
			DKeepDebugVisualizerVariableActive(ppVariant2);
			DKeepDebugVisualizerVariableActive(ppFloatWhat);
			DKeepDebugVisualizerVariableActive(ppStackTrace);
			DKeepDebugVisualizerVariableActive(ppAtomicInt);
			DKeepDebugVisualizerVariableActive(ppAtomicPtr);
			DKeepDebugVisualizerVariableActive(ppAtomicPtrNull);
			DKeepDebugVisualizerVariableActive(ppAtomicIntPtr);
			DKeepDebugVisualizerVariableActive(ppBigSet);
			DKeepDebugVisualizerVariableActive(ppBigVector);
			DKeepDebugVisualizerVariableActive(ppBigLinkedList);
			DKeepDebugVisualizerVariableActive(pppAutoClear);
			DKeepDebugVisualizerVariableActive(pppAutoClearDebug);
			DKeepDebugVisualizerVariableActive(pppDebugPointer);
			DKeepDebugVisualizerVariableActive(pppPointer);
			DKeepDebugVisualizerVariableActive(pppSharedPointer);
			DKeepDebugVisualizerVariableActive(pppSharedPointerSupportWeak);
			DKeepDebugVisualizerVariableActive(pppWeakPointer);
			DKeepDebugVisualizerVariableActive(pppUniquePointer);
			DKeepDebugVisualizerVariableActive(pppAutoClearNull);
			DKeepDebugVisualizerVariableActive(pppAutoClearDebugNull);
			DKeepDebugVisualizerVariableActive(pppDebugPointerNull);
			DKeepDebugVisualizerVariableActive(pppPointerNull);
			DKeepDebugVisualizerVariableActive(pppSharedPointerNull);
			DKeepDebugVisualizerVariableActive(pppSharedPointerSupportWeakNull);
			DKeepDebugVisualizerVariableActive(pppWeakPointerNull);
			DKeepDebugVisualizerVariableActive(pppUniquePointerNull);
			DKeepDebugVisualizerVariableActive(pppDebugPointerInt);
			DKeepDebugVisualizerVariableActive(pppPointerInt);
			DKeepDebugVisualizerVariableActive(pppSharedPointerInt);
			DKeepDebugVisualizerVariableActive(pppUniquePointerInt);
			DKeepDebugVisualizerVariableActive(ppReference);
			DKeepDebugVisualizerVariableActive(ppIndirection);
			DKeepDebugVisualizerVariableActive(ppAutoClearGeneral);
			DKeepDebugVisualizerVariableActive(ppAutoClearGeneralPointer);
			DKeepDebugVisualizerVariableActive(ppAutoClearInt);
			DKeepDebugVisualizerVariableActive(ppAutoClear_zmint);
			DKeepDebugVisualizerVariableActive(ppAutoClear_zfp32);
			DKeepDebugVisualizerVariableActive(x1);
			DKeepDebugVisualizerVariableActive(x2);
#undef DKeepDebugVisualizerVariableActive
			};
		}
	};

DMibTestRegister(CDebug_Tests, Malterlib::Debug);
