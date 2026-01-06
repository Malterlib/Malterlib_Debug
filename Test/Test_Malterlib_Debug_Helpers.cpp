// Copyright © 2015 Hansoft AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include "Test_Malterlib_Debug.h"

void fg_TestIntrusive(DMibListLinkDS_List(CTestClass, m_Link) &_List)
{
	for (auto iTest = _List.f_GetIterator(); iTest; ++iTest)
	{
	}
}
