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

class CTest2 : public NMib::NPtr::TCSharedPointerIntrusiveBase<>
{
public:
	CTest2(int _Value)
		: m_Value(_Value)
	{
	}
	mint m_Value;
	
	class CCompare
	{
	public:
		inline_small const mint &operator () (CTest2 const &_Node) const 
		{
			return _Node.m_Value;
		}
	};

	DMibIntrusiveLink(CTest2, NMib::NIntrusive::TCAVLLink<>, m_AVLLink);
	DMibListLinkS_Link(CTestClass, m_LinkSingle);
	DMibAutoClearPtrDeclare;
	DMibAutoClearPtrDeclareDebug(CTestClass);
};

void fg_TestIntrusive(DMibListLinkDS_List(CTestClass, m_Link) &_List);
