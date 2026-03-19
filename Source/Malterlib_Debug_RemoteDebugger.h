// Copyright © 2015 Hansoft AB
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#pragma once
namespace NMib::NDebug::NRemoteDebugger
{
#ifndef DMibRemoteDebugger_Enabled
#define DMibRemoteDebugger_Enabled 0
#endif

	static uint64 const gc_nStackLevels = 64;

#if DMibRemoteDebugger_Enabled
	enum EFeature
	{
		EFeature_None				= 0,
		EFeature_MemoryReporting	= DMibBit(0),
		EFeature_MemoryStackTrace	= DMibBit(1),
		EFeature_Logging			= DMibBit(2),
	};

	template <typename tf_CType>
	struct TCStackTrace
	{
		tf_CType m_lStack[gc_nStackLevels];
		zuint32 m_StackTraceLevels;

		TCStackTrace() {}
		~TCStackTrace() {}


		template<typename t_CStream>
		void f_Read(t_CStream& _Stream)
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
				m_lStack[iL] = CurValue;
			}
		}

		template<typename t_CStream>
		void f_Write(t_CStream& _Stream) const
		{
			_Stream << (uint8)m_StackTraceLevels.f_Get();

			for (umint iL = 0; iL < m_StackTraceLevels; ++iL)
			{
				_Stream << (uint64)m_lStack[iL];
			}
		}

		void f_Acquire()
		{
			m_StackTraceLevels = NSys::fg_System_GetStackTrace((CMibCodeAddress*)m_lStack, gc_nStackLevels);
		}
	};


	class CReportMemoryFromRemote //  : public NMemory::CGlobalReportMemory
	{
	public:
		virtual ~CReportMemoryFromRemote() {}

		virtual	void f_AllocatorName
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, NStr::CStr const& _Name
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_AllocatorDelete
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_ScopeEnter
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_ScopeExit
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_Alloc
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _Address
				, uint64 _RequestedAlignment
				, uint64 _RequestedSize
				, uint64 _ReturnedSize
				, fp32 _nBytesOverhead
				, TCStackTrace<uint64> const& _lStack
			) = 0
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
				, TCStackTrace<uint64> const& _lStack
			) = 0
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
				, TCStackTrace<uint64> const& _lStack
			) = 0

			;
		virtual void f_Free
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _Address
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_GetSize
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _Address
				, uint64 _Size
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_Protect
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _Address
				, uint64 _Size
				, uaint _Protect
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_Commit
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _Address
				, uint64 _Size
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;

		virtual void f_Decommit
			(
				  uint64 _ThreadID
				, uint64 _MemoryAllocator
				, uint64 _Address
				, uint64 _Size
				, TCStackTrace<uint64> const& _lStack
			) = 0
		;
	};

	static const uint16 gc_RemoteDebuggerPort = 50277;

	enum EServerEvent
	{
		EServerEvent_Connected,
		EServerEvent_Disconnected,
		EServerEvent_FatalError,
	};

	struct CServerSettings
	{
		NStr::CStr m_Address;
		uint16 m_Port;
		EFeature m_Features;
		NFunction::TCFunction<void (NFunction::TCFunction<void()>&&)> m_Dispatcher;
		NFunction::TCFunction<void (EServerEvent _Event)> m_EventCallback;
		NFunction::TCFunction<void (NFunction::TCFunction<void()>&&)> m_MemoryDispatcher; // Used for memory reporter calls.
		CReportMemoryFromRemote* m_pMemoryReporter;

		CServerSettings()
			: m_Address("127.0.0.1")
			, m_Port(gc_RemoteDebuggerPort)
			, m_Features(EFeature_None)
			, m_pMemoryReporter(nullptr)
		{}

		CServerSettings(CServerSettings&& _ToMove)
			: m_Address(fg_Move(_ToMove.m_Address))
			, m_Port(_ToMove.m_Port)
			, m_Features(_ToMove.m_Features)
			, m_Dispatcher(fg_Move(_ToMove.m_Dispatcher))
			, m_EventCallback(fg_Move(_ToMove.m_EventCallback))
			, m_MemoryDispatcher(fg_Move(_ToMove.m_MemoryDispatcher))
			, m_pMemoryReporter(_ToMove.m_pMemoryReporter)
		{
			_ToMove.m_Port = 0;
			_ToMove.m_Features = EFeature_None;
			_ToMove.m_pMemoryReporter = nullptr;
		}
	};

	bool fg_RD_InitializeServer(CServerSettings&& _Settings); // Note: Callbacks will be moved out of _Settings.
	uint64 fg_RD_ServerGetClientPID();
	void fg_RD_DeinitializeServer();

	bool fg_RD_InitializeClient();
	bool fg_RD_NetworkAvailableForClient();
	void fg_RD_DeinitializeClient();
#endif

}
