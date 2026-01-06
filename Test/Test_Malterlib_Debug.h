// Copyright © 2015 Hansoft AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

class CTestClass
{
public:
	CTestClass(mint _Value)
		: m_Value(_Value)
	{
	}

	mint m_Value;

	DMibListLinkDS_Link(CTestClass, m_Link);
};

class CTestClassManyValue
{
public:
	CTestClassManyValue(mint _Value)
		: m_Value(_Value)
	{
	}

	mint m_Value;
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

class CTest2
{
public:

	CTest2(int _Value)
		: m_Value(_Value)
	{
	}

	class CCompare
	{
	public:
		inline_small const mint &operator () (CTest2 const &_Node) const
		{
			return _Node.m_Value;
		}
	};

	NMib::NStorage::CIntrusiveRefCount m_RefCount;
	mint m_Value;
	NMib::NIntrusive::TCAVLLink<> m_AVLLink;
	DMibListLinkS_Link(CTest2, m_Link);
	DMibAutoClearPtrDeclare;
	DMibAutoClearPtrDeclareDebug(CTestClass);
};

void fg_TestIntrusive(DMibListLinkDS_List(CTestClass, m_Link) &_List);
