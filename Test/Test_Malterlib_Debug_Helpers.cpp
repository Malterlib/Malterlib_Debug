// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include "Test_Malterlib_Debug.h"

void fg_TestIntrusive(DMibListLinkDS_List(CTestClass, m_Link) &_List)
{
	for (auto iTest = _List.f_GetIterator(); iTest; ++iTest)
	{
	}
}
