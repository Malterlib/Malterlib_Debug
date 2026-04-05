// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

namespace NMib
{
	template <typename tf_CType>
	NStr::CStr fg_DebugColor(tf_CType const &_Data)
	{
		NStr::CStr DataStr = NStr::CStr::fs_ToStr(_Data);
		return fg_DebugColor(DataStr);
	}
}
