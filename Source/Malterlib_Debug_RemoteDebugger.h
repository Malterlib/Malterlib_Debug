// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once
namespace NMib::NDebug::NRemoteDebugger
{
#ifndef DMibRemoteDebugger_Enabled
#	define DMibRemoteDebugger_Enabled 0
#endif

	static constexpr uint64 gc_nStackLevels = 64;

#if DMibRemoteDebugger_Enabled
	enum EFeature
	{
		EFeature_None               = 0
		, EFeature_MemoryReporting  = DMibBit(0)
		, EFeature_MemoryStackTrace = DMibBit(1)
		, EFeature_Logging          = DMibBit(2)
	};

	template <typename t_CType>
	struct TCStackTrace
	{
		t_CType m_Stack[gc_nStackLevels];
		zuint32 m_StackTraceLevels;

		TCStackTrace();
		~TCStackTrace();

		template <typename tf_CStream>
		void f_Read(tf_CStream &_Stream);
		template <typename tf_CStream>
		void f_Write(tf_CStream &_Stream) const;

		void f_Acquire();
	};

	struct CReportMemoryFromRemote //  : public NMemory::CGlobalReportMemory
	{
		virtual ~CReportMemoryFromRemote();

		virtual void f_AllocatorName(uint64 _ThreadID, uint64 _MemoryAllocator, NStr::CStr const &_Name, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_AllocatorDelete(uint64 _ThreadID, uint64 _MemoryAllocator, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_ScopeEnter(uint64 _ThreadID, uint64 _MemoryAllocator, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_ScopeExit(uint64 _ThreadID, uint64 _MemoryAllocator, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_Alloc
			(
				uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _Address
				, uint64 _RequestedAlignment
				, uint64 _RequestedSize
				, uint64 _ReturnedSize
				, fp32 _nBytesOverhead
				, TCStackTrace<uint64> const &_Stack
			)
			= 0
		;
		virtual void f_Resize
			(
				uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _OldAddress
				, uint64 _Address
				, uint64 _RequestedAlignment
				, uint64 _RequestedSize
				, uint64 _ReturnedSize
				, fp32 _nBytesOverhead
				, TCStackTrace<uint64> const &_Stack
			)
			= 0
		;
		virtual void f_Realloc
			(
				uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _OldAddress
				, uint64 _Address
				, uint64 _RequestedAlignment
				, uint64 _RequestedSize
				, uint64 _ReturnedSize
				, fp32 _nBytesOverhead
				, TCStackTrace<uint64> const &_Stack
			)
			= 0
		;
		virtual void f_Free(uint64 _ThreadID, uint64 _MemoryAllocator, uint64 _Address, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_GetSize(uint64 _ThreadID, uint64 _MemoryAllocator, uint64 _Address, uint64 _Size, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_Protect(uint64 _ThreadID, uint64 _MemoryAllocator, uint64 _Address, uint64 _Size, uaint _Protect, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_Commit(uint64 _ThreadID, uint64 _MemoryAllocator, uint64 _Address, uint64 _Size, TCStackTrace<uint64> const &_Stack) = 0;

		virtual void f_Decommit(uint64 _ThreadID, uint64 _MemoryAllocator, uint64 _Address, uint64 _Size, TCStackTrace<uint64> const &_Stack) = 0;
	};

	static constexpr uint16 gc_RemoteDebuggerPort = 50277;

	enum EServerEvent
	{
		EServerEvent_Connected
		, EServerEvent_Disconnected
		, EServerEvent_FatalError
	};

	struct CServerSettings
	{
		NStr::CStr m_Address;
		uint16 m_Port;
		EFeature m_Features;
		NFunction::TCFunction<void (NFunction::TCFunction<void ()> &&_fFunction)> m_Dispatcher;
		NFunction::TCFunction<void (EServerEvent _Event)> m_EventCallback;
		NFunction::TCFunction<void (NFunction::TCFunction<void ()> &&_fFunction)> m_MemoryDispatcher; // Used for memory reporter calls.
		CReportMemoryFromRemote *m_pMemoryReporter;

		CServerSettings();
		CServerSettings(CServerSettings &&_ToMove);
	};

	bool fg_RD_InitializeServer(CServerSettings &&_Settings); // Note: Callbacks will be moved out of _Settings.
	uint64 fg_RD_ServerGetClientPID();
	void fg_RD_DeinitializeServer();

	bool fg_RD_InitializeClient();
	bool fg_RD_NetworkAvailableForClient();
	void fg_RD_DeinitializeClient();
#endif
}

#include "Malterlib_Debug_RemoteDebugger.hpp"
