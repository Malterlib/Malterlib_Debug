// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

#if DMibRemoteDebugger_Enabled
namespace NMib::NDebug::NRemoteDebugger
{
	template <typename t_CType>
	TCStackTrace<t_CType>::TCStackTrace()
	{
	}

	template <typename t_CType>
	TCStackTrace<t_CType>::~TCStackTrace()
	{
	}

	template <typename t_CType>
	template <typename tf_CStream>
	void TCStackTrace<t_CType>::f_Read(tf_CStream &_Stream)
	{
		uint8 nLevels = 0;
		_Stream >> nLevels;
		if (nLevels > gc_nStackLevels)
			DMibError("Invalid stack trace");

		m_StackTraceLevels = nLevels;

		uint64 CurValue;
		for (umint iL = 0; iL < nLevels; ++iL)
		{
			_Stream >> CurValue;
			m_Stack[iL] = CurValue;
		}
	}

	template <typename t_CType>
	template <typename tf_CStream>
	void TCStackTrace<t_CType>::f_Write(tf_CStream &_Stream) const
	{
		_Stream << (uint8)m_StackTraceLevels.f_Get();

		for (umint iL = 0; iL < m_StackTraceLevels; ++iL)
			_Stream << (uint64)m_Stack[iL];
	}

	template <typename t_CType>
	void TCStackTrace<t_CType>::f_Acquire()
	{
		m_StackTraceLevels = NSys::fg_System_GetStackTrace((CMibCodeAddress *)m_Stack, gc_nStackLevels);
	}
}
#endif
