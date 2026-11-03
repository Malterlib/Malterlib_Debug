// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

struct CTestClass
{
	CTestClass(umint _Value);

	umint m_Value;

	DMibListLinkDS_Link(CTestClass, m_Link);
};

struct CTestClassManyValue
{
	CTestClassManyValue(umint _Value);

	umint m_Value;
	fp32 m_Value0 = 55.55f;
	fp32 m_Value1 = 6;
	fp32 m_Value2 = 8;
	NMib::NStr::CStr m_Value3 = "Testing a long long long long long long long long long long long long value";

	DMibListLinkDS_Link(CTestClassManyValue, m_Link);
};

struct CTestRecursiveLinked
{
	DMibListLinkDS_Link(CTestRecursiveLinked, m_Link);
	DMibListLinkDS_List(CTestRecursiveLinked, m_Link) m_Children;
};

struct CTest2
{
	CTest2(int _Value);

	struct CCompare
	{
		inline_small umint const &operator () (CTest2 const &_Node) const;
	};

	NMib::NStorage::CIntrusiveRefCount m_RefCount;
	umint m_Value;
	NMib::NIntrusive::TCAVLLink<> m_AVLLink;
	DMibListLinkS_Link(CTest2, m_Link);
	DMibAutoClearPtrDeclare;
	DMibAutoClearPtrDeclareDebug(CTestClass);
};

void fg_TestIntrusive(DMibListLinkDS_List(CTestClass, m_Link) &_List);

#include "Test_Malterlib_Debug.hpp"
