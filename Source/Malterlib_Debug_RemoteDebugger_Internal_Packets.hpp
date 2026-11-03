// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

namespace NMib::NDebug::NRemoteDebugger
{
	template <typename tf_CStream>
	void CPacketHeader::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_Channel >> m_Padding >> m_PacketID >> m_nBytes;
	}

	template <typename tf_CStream>
	void CPacketHeader::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_Channel << m_Padding << m_PacketID << m_nBytes;
	}

	template <typename tf_CStream>
	void CSysPacket_Initialize::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_Features;
	}

	template <typename tf_CStream>
	void CSysPacket_Initialize::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_Features;
	}

	template <typename tf_CStream>
	void CSysPacket_ClientConnect::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_PID;
	}

	template <typename tf_CStream>
	void CSysPacket_ClientConnect::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_PID;
	}

	template <typename tf_CStream>
	void CMemPacket_AllocatorName::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_Name;
	}

	template <typename tf_CStream>
	void CMemPacket_AllocatorName::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_Name;
	}

	template <typename tf_CStream>
	void CMemPacket_AllocatorDelete::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator;
	}

	template <typename tf_CStream>
	void CMemPacket_AllocatorDelete::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator;
	}

	template <typename tf_CStream>
	void CMemPacket_ScopeEnter::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator;
	}

	template <typename tf_CStream>
	void CMemPacket_ScopeEnter::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator;
	}

	template <typename tf_CStream>
	void CMemPacket_ScopeExit::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator;
	}

	template <typename tf_CStream>
	void CMemPacket_ScopeExit::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator;
	}

	template <typename tf_CStream>
	void CMemPacket_Alloc::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_Address >> m_RequestedSize >> m_RequestedSize >> m_ReturnedSize >> m_nBytesOverhead;
	}

	template <typename tf_CStream>
	void CMemPacket_Alloc::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_Address << m_RequestedSize << m_RequestedSize << m_ReturnedSize << m_nBytesOverhead;
	}

	template <typename tf_CStream>
	void CMemPacket_Resize::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_OldAddress >> m_Address >> m_RequestedAlignment >> m_RequestedSize >> m_ReturnedSize >> m_nBytesOverhead;
	}

	template <typename tf_CStream>
	void CMemPacket_Resize::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_OldAddress << m_Address << m_RequestedAlignment << m_RequestedSize << m_ReturnedSize << m_nBytesOverhead;
	}

	template <typename tf_CStream>
	void CMemPacket_Realloc::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_OldAddress >> m_Address >> m_RequestedAlignment >> m_RequestedSize >> m_ReturnedSize >> m_nBytesOverhead;
	}

	template <typename tf_CStream>
	void CMemPacket_Realloc::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_OldAddress << m_Address << m_RequestedAlignment << m_RequestedSize << m_ReturnedSize << m_nBytesOverhead;
	}

	template <typename tf_CStream>
	void CMemPacket_Free::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_Address;
	}

	template <typename tf_CStream>
	void CMemPacket_Free::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_Address;
	}

	template <typename tf_CStream>
	void CMemPacket_GetSize::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_Address >> m_Size;
	}

	template <typename tf_CStream>
	void CMemPacket_GetSize::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_Address << m_Size;
	}

	template <typename tf_CStream>
	void CMemPacket_Protect::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_Address >> m_Size >> m_Protect;
	}

	template <typename tf_CStream>
	void CMemPacket_Protect::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_Address << m_Size << m_Protect;
	}

	template <typename tf_CStream>
	void CMemPacket_Commit::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_Address >> m_Size;
	}

	template <typename tf_CStream>
	void CMemPacket_Commit::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_Address << m_Size;
	}

	template <typename tf_CStream>
	void CMemPacket_Decommit::f_Read(tf_CStream &_Stream)
	{
		_Stream >> m_ThreadID >> m_MemoryAllocator >> m_Address >> m_Size;
	}

	template <typename tf_CStream>
	void CMemPacket_Decommit::f_Write(tf_CStream &_Stream) const
	{
		_Stream << m_ThreadID << m_MemoryAllocator << m_Address << m_Size;
	}
}
