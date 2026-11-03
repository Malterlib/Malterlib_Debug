// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

namespace NMib::NDebug::NPlatform
{
	inline umint const &CStackTraceContext::CAVLCompare_CLocalStackTraceInfo::operator () (CLocalStackTraceInfo const &_Node) const
	{
		return _Node.m_Address;
	}
}
