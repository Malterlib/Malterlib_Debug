// Copyright © 2022 Favro Holding AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

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
