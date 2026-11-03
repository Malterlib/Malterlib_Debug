// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

inline umint const &CTest2::CCompare::operator () (CTest2 const &_Node) const
{
	return _Node.m_Value;
}
