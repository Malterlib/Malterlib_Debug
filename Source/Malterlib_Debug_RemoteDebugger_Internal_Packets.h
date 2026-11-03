// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

namespace NMib::NDebug::NRemoteDebugger
{
	enum EChannel
	{
		EChannel_System
		, EChannel_Memory
	};

	enum EPacket
	{
		// System Channel
		EPacket_Sys_Initialize
		, EPacket_Sys_Disconnected

		, EPacket_Sys_ClientConnect // The client notifies the server of it's PID

		// Memory Channel
		, EPacket_Mem_AllocatorName
		, EPacket_Mem_AllocatorDelete
		, EPacket_Mem_ScopeEnter
		, EPacket_Mem_ScopeExit
		, EPacket_Mem_Alloc
		, EPacket_Mem_Resize
		, EPacket_Mem_Realloc
		, EPacket_Mem_Free
		, EPacket_Mem_GetSize
		, EPacket_Mem_Protect
		, EPacket_Mem_Commit
		, EPacket_Mem_Decommit
	};

	// TODO: Using Var-Ints for alot of these would probably save a load of bandwidth.

	// Special requirement for CPacketHeader: Size of in-mem struct == Size of serialised struct.
	struct CPacketHeader
	{
		uint8 m_Channel;
		uint8 m_Padding;
		uint16 m_PacketID;
		uint32 m_nBytes;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	// Sys Packets

	struct CSysPacket_Initialize
	{
		uint32 m_Features;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CSysPacket_ClientConnect
	{
		uint64 m_PID;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	// Mem Packets

	struct CMemPacket_AllocatorName
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		NStr::CStrNonTracked m_Name;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_AllocatorDelete
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_ScopeEnter
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_ScopeExit
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_Alloc
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_Address;
		uint64 m_RequestedAlignment;
		uint64 m_RequestedSize;
		uint64 m_ReturnedSize;
		fp32 m_nBytesOverhead;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_Resize
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_OldAddress;
		uint64 m_Address;
		uint64 m_RequestedAlignment;
		uint64 m_RequestedSize;
		uint64 m_ReturnedSize;
		fp32 m_nBytesOverhead;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_Realloc
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_OldAddress;
		uint64 m_Address;
		uint64 m_RequestedAlignment;
		uint64 m_RequestedSize;
		uint64 m_ReturnedSize;
		fp32 m_nBytesOverhead;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_Free
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_Address;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_GetSize
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_Address;
		uint64 m_Size;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_Protect
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_Address;
		uint64 m_Size;
		uint64 m_Protect;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_Commit
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_Address;
		uint64 m_Size;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};

	struct CMemPacket_Decommit
	{
		uint64 m_ThreadID;
		uint64 m_MemoryAllocator;
		uint64 m_Address;
		uint64 m_Size;

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);

		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;
	};
}

#include "Malterlib_Debug_RemoteDebugger_Internal_Packets.hpp"
