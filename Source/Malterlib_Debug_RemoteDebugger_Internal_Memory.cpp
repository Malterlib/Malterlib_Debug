// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>

#include <Mib/Debug/RemoteDebugger>

#if DMibRemoteDebugger_Enabled

#include "Malterlib_Debug_RemoteDebugger_Internal.h"

namespace NMib::NDebug::NRemoteDebugger
{
	void CServer::fp_DecodeMemoryPacket(EPacket _Packet, CDataBuffer const &_Data)
	{
		using namespace NStream;

		CBinaryStreamMemoryPtr<> Stream;
		Stream.f_OpenRead(_Data.f_GetArray(), _Data.f_GetLen());

		bool bStackTrace = mp_Settings.m_Features & EFeature_MemoryStackTrace;
		TCStackTrace<uint64> StackTrace;

		auto fl_ReadStackTrace =
			[&]()
			{
				if (bStackTrace)
				{
					StackTrace.f_Read(Stream);
					// We could (should?) do this reversal elsewhere.
					mint nLevels = StackTrace.m_StackTraceLevels;
					mint nLevelsSubOne = nLevels - 1;
					mint Half = nLevels >> 1;
					for (mint iL = 0; iL < Half; ++iL)
					{
						fg_Swap(StackTrace.m_lStack[iL], StackTrace.m_lStack[nLevelsSubOne - iL] );
					}
				}
			};

		switch(_Packet)
		{
			case EPacket_Mem_AllocatorName:
				{
					CMemPacket_AllocatorName Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_AllocatorName(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								,	Packet.m_Name
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_AllocatorDelete:
				{
					CMemPacket_AllocatorDelete Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_AllocatorDelete(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_ScopeEnter:
				{
					CMemPacket_ScopeEnter Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_ScopeEnter(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_ScopeExit:
				{
					CMemPacket_ScopeExit Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_ScopeExit(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_Alloc:
				{
					CMemPacket_Alloc Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_Alloc(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_Address
								,	Packet.m_RequestedAlignment
								,	Packet.m_RequestedSize
								, 	Packet.m_ReturnedSize
								,	Packet.m_nBytesOverhead
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_Resize:
				{
					CMemPacket_Resize Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_Resize(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_OldAddress
								, 	Packet.m_Address
								,	Packet.m_RequestedAlignment
								,	Packet.m_RequestedSize
								, 	Packet.m_ReturnedSize
								,	Packet.m_nBytesOverhead
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_Realloc:
				{
					CMemPacket_Realloc Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_Realloc(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_OldAddress
								, 	Packet.m_Address
								,	Packet.m_RequestedAlignment
								,	Packet.m_RequestedSize
								, 	Packet.m_ReturnedSize
								,	Packet.m_nBytesOverhead
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_Free:
				{
					CMemPacket_Free Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_Free(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_Address
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_GetSize:
				{
					CMemPacket_GetSize Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_GetSize(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_Address
								, 	Packet.m_Size
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_Protect:
				{
					CMemPacket_Protect Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_Protect(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_Address
								, 	Packet.m_Size
								, 	Packet.m_Protect
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_Commit:
				{
					CMemPacket_Commit Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_Commit(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_Address
								, 	Packet.m_Size
								, StackTrace
							);
						}
					);
				}
				break;
			case EPacket_Mem_Decommit:
				{
					CMemPacket_Decommit Packet;

					Packet.f_Read(Stream);
					fl_ReadStackTrace();

					mp_Settings.m_MemoryDispatcher(
						[this, Packet, StackTrace]()
						{
							mp_Settings.m_pMemoryReporter->f_Decommit(
									Packet.m_ThreadID
								,	Packet.m_MemoryAllocator
								, 	Packet.m_Address
								, 	Packet.m_Size
								, StackTrace
							);
						}
					);
				}
				break;

		}
	}

	CReportMemoryToRemote::CReportMemoryToRemote(CClient* _pClient, bool _bStackTrace)
		: mp_pClient(_pClient)
		, mp_bStackTrace(_bStackTrace)
	{
	}

	CReportMemoryToRemote::~CReportMemoryToRemote()
	{
	}


	void CReportMemoryToRemote::f_AllocatorName(mint _MemoryAllocator, ch8 const* _pAllocatorName)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_AllocatorName Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
			, _pAllocatorName
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_AllocatorName
									, Packet
									, mp_bStackTrace ? &Trace : nullptr
								);
	}

	void CReportMemoryToRemote::f_AllocatorDelete(mint _MemoryAllocator)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_AllocatorDelete Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_AllocatorDelete
									, Packet
									, mp_bStackTrace ? &Trace : nullptr
								);

	}

	void CReportMemoryToRemote::f_ScopeEnter(mint _MemoryAllocator)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_ScopeEnter Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_ScopeEnter
									, Packet
									, mp_bStackTrace ? &Trace : nullptr
								);
	}

	void CReportMemoryToRemote::f_ScopeExit(mint _MemoryAllocator)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_ScopeExit Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_ScopeExit
									, Packet
									, mp_bStackTrace ? &Trace : nullptr
								);
	}


	void CReportMemoryToRemote::f_Alloc
		(
			mint _MemoryAllocator
			, mint _Address
			, mint _RequestedAlignment
			, mint _RequestedSize
			, mint _ReturnedSize
			, fp32 _nBytesOverhead
			, void *_pAllocationInfo
		)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_Alloc Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			,_MemoryAllocator
			, _Address
			, _RequestedAlignment
			, _RequestedSize
			, _ReturnedSize
			, _nBytesOverhead
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_Alloc
									, Packet
									, mp_bStackTrace ? &Trace : nullptr
								);
	}

	void CReportMemoryToRemote::f_Resize
		(
			  mint _MemoryAllocator
			, mint _OldAddress
			, mint _OldSize
			, void const *_pOldAllocationInfo
			, mint _Address
			, mint _RequestedAlignment
			, mint _RequestedSize
			, mint _ReturnedSize
			, fp32 _nBytesOverhead
			, void *_pAllocationInfo
		)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_Resize Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
			, _OldAddress
			, _Address
			, _RequestedAlignment
			, _RequestedSize
			, _ReturnedSize
			, _nBytesOverhead
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_Resize
									, Packet
									, mp_bStackTrace ? &Trace : nullptr);
	}

	void CReportMemoryToRemote::f_Realloc
		(
			mint _MemoryAllocator
			, mint _OldAddress
			, mint _OldSize
			, void const *_pOldAllocationInfo
			, mint _Address
			, mint _RequestedAlignment
			, mint _RequestedSize
			, mint _ReturnedSize
			, fp32 _nBytesOverhead
			, void *_pAllocationInfo
		)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_Realloc Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
			, _OldAddress
			, _Address
			, _RequestedAlignment
			, _RequestedSize
			, _ReturnedSize
			, _nBytesOverhead
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_Realloc
									, Packet
									, mp_bStackTrace ? &Trace : nullptr);

	}

	void CReportMemoryToRemote::f_Free(mint _MemoryAllocator, mint _Address, mint _Size, void const *_pAllocationInfo)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_Free Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			,_MemoryAllocator
			, _Address
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_Free
									, Packet
									, mp_bStackTrace ? &Trace : nullptr);

	}

	void CReportMemoryToRemote::f_GetSize(mint _MemoryAllocator, mint _Address, mint _Size, void const *_pAllocationInfo)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_GetSize Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
			, _Address
			, _Size
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_GetSize
									, Packet
									, mp_bStackTrace ? &Trace : nullptr);

	}

	void CReportMemoryToRemote::f_Protect(mint _MemoryAllocator, mint _Address, mint _Size, uaint _Protect)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_Protect Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
			, _Address
			, _Size
			, _Protect
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_Protect
									, Packet
									, mp_bStackTrace ? &Trace : nullptr);

	}

	void CReportMemoryToRemote::f_Commit(mint _MemoryAllocator, mint _Address, mint _Size)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_Commit Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
			, _Address
			, _Size
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_Commit
									, Packet
									, mp_bStackTrace ? &Trace : nullptr);

	}

	void CReportMemoryToRemote::f_Decommit(mint _MemoryAllocator, mint _Address, mint _Size)
	{
		auto pConnection = mp_pClient->f_GetConnection();
		if (!pConnection)
			return;

		CMemPacket_Decommit Packet =
		{
			 NSys::fg_Thread_GetCurrentUID()
			, _MemoryAllocator
			, _Address
			, _Size
		};

		TCStackTrace<mint> Trace;
		if (mp_bStackTrace)
			Trace.f_Acquire();

		pConnection->f_SendPacket(EChannel_Memory, EPacket_Mem_Decommit
									, Packet
									, mp_bStackTrace ? &Trace : nullptr);

	}
}

#endif
