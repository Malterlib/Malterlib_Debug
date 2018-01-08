// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include <Mib/Debug/RemoteDebugger>
#include "Malterlib_Debug_RemoteDebugger_Internal_Packets.h"

namespace NMib
{
	namespace NRemoteDebugger
	{
		/*
		template <typename t_CType, mint t_GrowSize = 512>
		class TCRemoteDebuggerPool : public NMem::TCStaticPool<t_CType, t_GrowSize, NMib::NMem::CAllocator_VirtualNoTracking>
		{
			typedef NMem::TCStaticPool<t_CType, t_GrowSize, NMib::NMem::CAllocator_VirtualNoTracking> CSuper;
		public:
			static t_CType *fs_New()
			{
				return CSuper::ms_Pool->f_New();
			}	

			template <typename t_CP0>
			static t_CType *fs_New(t_CP0 &&_P0)
			{
				return CSuper::ms_Pool->f_New(fg_Forward<t_CP0>(_P0));
			}	

			template <typename t_CP0, typename t_CP1>
			static t_CType *fs_New(t_CP0 &&_P0, t_CP1 &&_P1)
			{
				return CSuper::ms_Pool->f_New(fg_Forward<t_CP0>(_P0), fg_Forward<t_CP1>(_P1));
			}	

			template <typename t_CP0, typename t_CP1, typename t_CP2>
			static t_CType *fs_New(t_CP0 &&_P0, t_CP1 &&_P1, t_CP2 &&_P2)
			{
				return CSuper::ms_Pool->f_New(fg_Forward<t_CP0>(_P0), fg_Forward<t_CP1>(_P1), fg_Forward<t_CP2>(_P2));
			}	

			static void fs_Delete(t_CType *_pObject)
			{
				return CSuper::ms_Pool->f_Delete(_pObject);
			}	
		};

		template <typename t_CType, mint t_GrowSize = 512>
		class TCRemoteDebuggerAllocator : public NMem::TCStaticPoolAllocator<t_CType, t_GrowSize, NMib::NMem::CAllocator_VirtualNoTracking>
		{
		public:
		};
		*/

		template <typename t_CType, mint t_GrowSize = 512>
		class TCRemoteDebuggerPool
		{
			typedef NMem::TCStaticPool<t_CType, t_GrowSize, NMib::NMem::CAllocator_VirtualNoTracking> CSuper;
		public:
			template <typename ...tfp_CParams>
			static t_CType *fs_New(tfp_CParams &&...p_Params)
			{
				auto Memory = NMem::CAllocator_NonTrackedHeap::f_AllocSafe(sizeof(t_CType), NTraits::TCAlignmentOf<t_CType>::mc_Value);
				auto pReturn = new(Memory.m_pMemory) t_CType(fg_Forward<tfp_CParams>(p_Params)...);
				Memory.f_Claim();
				return pReturn;
			}
			static void fs_Delete(t_CType *_pObject)
			{
				_pObject->~t_CType();
				NMem::CAllocator_NonTrackedHeap::f_Free(_pObject, sizeof(t_CType));
			}
		};

		typedef NContainer::TCVector<uint8, NMem::CAllocator_NonTrackedHeap, NContainer::CVectorBoundsCheckDefault, NContainer::CVectorData, NContainer::TCVectorStaticData_GrowDouble<64, false>> CDataBuffer;

		struct CPacket
		{
		private:
			CPacket(CPacket const& ) {}
		public:
			CPacket() {}
			CPacket(CPacket&& _ToMove)
				: m_Channel(_ToMove.m_Channel)
				, m_PacketID(_ToMove.m_PacketID)
				, m_Data(fg_Move(_ToMove.m_Data))
			{}

			EChannel m_Channel;
			EPacket m_PacketID;
			CDataBuffer m_Data;

			DMibListLinkDS_Link(CConnection::CPacket, m_Link);
		};

		class CConnection;
		class CPacketReference
		{
			CPacket *mp_pPacket;
			CConnection *mp_pConnection;
			CPacketReference(CPacketReference const &_Other);
			CPacketReference &operator = (CPacketReference const &_Other);
		public:
			CPacketReference(CPacket *_pPacket, CConnection *_pConnection)
				: mp_pPacket(_pPacket)
				, mp_pConnection(_pConnection)
			{
			}
			CPacketReference()
				: mp_pPacket(nullptr)
				, mp_pConnection(nullptr)
			{
			}
			CPacketReference(CPacketReference &&_Other)
				: mp_pPacket(_Other.mp_pPacket)
				, mp_pConnection(_Other.mp_pConnection)
			{
				_Other.mp_pPacket = nullptr;
				_Other.mp_pConnection = nullptr;
			}

			~CPacketReference();

			operator bool()
			{
				return mp_pPacket != nullptr;
			}
			EChannel f_Channel() const
			{
				return mp_pPacket->m_Channel;
			}
			EPacket f_PacketID() const
			{
				return mp_pPacket->m_PacketID;
			}
			
			CDataBuffer const &f_Data()
			{
				return mp_pPacket->m_Data;
			}
		};

		class CConnection
		{
			friend class CPacketReference;
		public:

			enum EMode
			{
				EMode_Listen,
				EMode_Connect,
				EMode_DelayedConnect,
			};

			enum EState
			{
				EState_None,
				EState_Connected,
				EState_Failed,
				EState_Disconnected,
				EState_Listening,
			};

			struct CDataBlock
			{
				EChannel m_Channel;
				CDataBuffer m_Data;

				DMibListLinkDS_Link(CConnection::CDataBlock, m_Link);

				template<typename t_CPacket>
				void f_Fill(EChannel _Channel, EPacket _PacketID, t_CPacket const& _Packet, TCStackTrace<mint> const* _pTrace)
				{
					m_Channel = _Channel;

					NStream::CBinaryStreamMemoryRef<NStream::CBinaryStreamDefault, CDataBuffer> Stream(m_Data);
					Stream.f_ResetStream();

					CPacketHeader Header =
						{ (uint8)_Channel, (uint8)0, (uint16)_PacketID, 0 };

					Header.f_Write(Stream);

					mint nHeaderBytes = Stream.f_GetPosition(); 

					_Packet.f_Write(Stream);
					if (_pTrace)
						_pTrace->f_Write(Stream);
					
					Header.m_nBytes = Stream.f_GetPosition() - nHeaderBytes;

					Stream.f_SetPosition(0);
					Header.f_Write(Stream);
					/*
					DMibLogCat(RD);
					DMibLog(Debug, "Filling block. PcktID: {}, Hdr: {}, Payload: {}"
						, (uint32)_PacketID
						, sizeof(CPacketHeader)
						, Header.m_nBytes);
						*/
				}
			};

		private:

			NStr::CStrNonTracked mp_Address;
			uint16 mp_Port;

			EMode mp_Mode;

			NAtomic::TCAtomic<EState> mp_ConnectionState;

			NNet::CSocket mp_Socket;
			NThread::CSemaphoreReportable mp_SocketSema;

			NThread::CSemaphoreReportableAggregate* mp_pReportTo;

			NAtomic::TCAtomic<uint32> mp_bDataToSend;
			NThread::CMutual mp_SendLock; 
				DMibListLinkDS_List(CConnection::CDataBlock, m_Link) mp_SendData;

			NThread::CMutual mp_FreeDataBlocksLock; 
				DMibListLinkDS_List(CConnection::CDataBlock, m_Link) mp_FreeDataBlocks;
				NThread::CEventAutoReset mp_FreeDataBlocksAvailable;

			NThread::CMutual mp_ReceiveLock; 
				DMibListLinkDS_List(CPacket, m_Link) mp_ReceivedPackets;

			NThread::CMutual mp_FreePacketsLock; 
				DMibListLinkDS_List(CPacket, m_Link) mp_FreePackets;
				NThread::CEventAutoReset mp_FreePacketsAvailable;

			NPtr::TCUniquePointer<NThread::CThreadObjectNonTracked, NMem::CAllocator_NonTrackedHeap> mp_pThread;

			void fp_Process();
			void fp_StartThread();

			void fp_ReturnPacket(CPacket *_pPacket);
			CPacket *fp_GetPacket();

		public:
			CConnection(NThread::CSemaphoreReportableAggregate* _pReportTo); // Should be private. Do not use.
			CConnection(EMode _Mode, NStr::CStrNonTracked const& _Address, uint16 _Port, NThread::CSemaphoreReportableAggregate* _pReportTo);
			~CConnection();

			EState f_GetState() const;
			bint f_IsConnected() const;

			bint f_Connect(); // Used with EMode_DelayedConnect

			// For connection connections :-)

			// Always succeed.
			CDataBlock* f_GetDataBlock();
			void f_ReturnDataBlock(CDataBlock *_pBlock);
			void f_SendDataBlock(CDataBlock* _pBlock);

			template<typename t_CPacket>
			void f_SendPacket(EChannel _Channel, EPacket _PacketID, t_CPacket const& _Packet, TCStackTrace<mint> const* _pTrace = nullptr)
			{
				CDataBlock* pBlock = f_GetDataBlock();
				pBlock->f_Fill(_Channel, _PacketID, _Packet, _pTrace);
				f_SendDataBlock(pBlock);
			}

			// Can fail. Wait on _pReportTo for when packets are available.
			CPacketReference f_ReceivePacket();

			// For listen connections

			// Can return nullptr. Wait on _pReportTo for when connections.
			NPtr::TCUniquePointer<CConnection, NMem::CAllocator_NonTrackedHeap> f_Accept(NThread::CSemaphoreReportableAggregate* _pReportTo);
		};

		class CReportMemoryToRemote;

		class CClient
		{
		private:		
			// The dispatcher will make an appearence later.
//			TCFunction<void(TCFunction<void()>&&)> mp_Dispatcher;

			NPtr::TCUniquePointer<CConnection, NMem::CAllocator_NonTrackedHeap> mp_pConnection;
			NThread::CSemaphoreReportable mp_ReadReady;

			NPtr::TCUniquePointer<NThread::CThreadObjectNonTracked, NMem::CAllocator_NonTrackedHeap> mp_pThread;

			EFeature mp_Features;

			NMem::CReportMemory* mp_pOldReporter;
			NPtr::TCUniquePointer<CReportMemoryToRemote, NMem::CAllocator_NonTrackedHeap> mp_pMemoryReporter;			

			NStr::CStrNonTracked mp_Address;
			uint16 mp_Port;

			void fp_Process();
			void fp_Initialize(EFeature _Features);

		public:
			CClient(/*TCFunction<void(TCFunction<void()>&&)>&& _Dispatcher*/);
			~CClient();

			bint f_IsEnabled();

			bint f_Connect();

			CConnection* f_GetConnection() { return mp_pConnection.f_Get(); }

		};

		class CServer
		{
		private:
			CServerSettings mp_Settings;

			NPtr::TCUniquePointer<CConnection, NMem::CAllocator_NonTrackedHeap> mp_pConnection;

			NThread::CSemaphoreReportable mp_ConnectionReady;
			NPtr::TCUniquePointer<NThread::CThreadObjectNonTracked, NMem::CAllocator_NonTrackedHeap> mp_pThread;			

			uint64 mp_ClientPID;


			void fp_Process();
			void fp_Process_Listening();
			void fp_Process_Connected();
			void fp_EmitEvent(EServerEvent _Event);
	
			void fp_DecodeMemoryPacket(EPacket _Packet, CDataBuffer const& _Data);

		public:
			CServer(CServerSettings&& _Settings);
			~CServer();

			bint f_Start();
			bint f_IsRunning();
			void f_Stop();

			uint64 f_GetClientPID() const { return mp_ClientPID;  }
		};


		class CReportMemoryToRemote : public NMem::CGlobalReportMemory
		{
		private:
			CClient* mp_pClient;
			bint mp_bStackTrace;
			NAtomic::TCAtomic<uint32> mp_SequenceNum;

		public:
			CReportMemoryToRemote(CClient* _pClient, bint _bStackTrace);
			virtual ~CReportMemoryToRemote();

			void f_AllocatorName(mint _MemoryAllocator, ch8 const* _pAllocatorName) override;
			void f_AllocatorDelete(mint _MemoryAllocator) override;

			void f_ScopeEnter(mint _MemoryAllocator) override;
			void f_ScopeExit(mint _MemoryAllocator) override;

			void f_Alloc
				(
					mint _MemoryAllocator
					, mint _Address
					, mint _RequestedAlignment
					, mint _RequestedSize
					, mint _ReturnedSize
					, fp32 _nBytesOverhead
					, void *_pAllocationInfo
				) override
			;
			void f_Resize
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
				) override
			;
			void f_Realloc
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
				) override
			;
			void f_Free(mint _MemoryAllocator, mint _Address, mint _Size, void const *_pAllocationInfo) override;
			void f_GetSize(mint _MemoryAllocator, mint _Address, mint _Size, void const *_pAllocationInfo) override;
			void f_Protect(mint _MemoryAllocator, mint _Address, mint _Size, uaint _Protect) override;
			void f_Commit(mint _MemoryAllocator, mint _Address, mint _Size) override;
			void f_Decommit(mint _MemoryAllocator, mint _Address, mint _Size) override;
		};

	} // Namespace NMem

} // Namespace NMib
