// Copyright © 2015 Hansoft AB 
// Distributed under the MIT license, see license text in LICENSE.Malterlib

#include <Mib/Core/Core>
#include <Mib/Debug/RemoteDebugger>

#if DMibRemoteDebugger_Enabled

#include "Malterlib_Debug_RemoteDebugger_Internal.h"

using namespace NMib::NStr;
using namespace NMib::NContainer;
using namespace NMib::NPtr;
using namespace NMib::NThread;
using namespace NMib::NNet;

namespace NMib
{
	namespace NRemoteDebugger
	{

		CPacketReference::~CPacketReference()
		{
			if (mp_pPacket)
			{
				mp_pConnection->fp_ReturnPacket(mp_pPacket);
			}
		}



		CConnection::CConnection(NThread::CSemaphoreReportableAggregate* _pReportTo)
			: mp_pReportTo(_pReportTo)
			, mp_Mode(EMode_Listen)
			, mp_ConnectionState(EState_None)
		{
			for (int i = 0; i < 1024; ++i)
				mp_FreeDataBlocks.f_Insert(TCRemoteDebuggerPool<CDataBlock>::fs_New());
			for (int i = 0; i < 1024; ++i)
				mp_FreePackets.f_Insert(TCRemoteDebuggerPool<CPacket>::fs_New());
		}

		CConnection::CConnection(EMode _Mode, CStrNonTracked const& _Address, uint16 _Port, NThread::CSemaphoreReportableAggregate* _pReportTo)
			: mp_pReportTo(_pReportTo)
			, mp_Mode(_Mode)
			, mp_Address(_Address)
			, mp_Port(_Port)
			, mp_ConnectionState(EState_None)
		{

			switch (mp_Mode)
			{
			case EMode_DelayedConnect:
				break;
			case EMode_Connect:
				f_Connect();
				break;
			case EMode_Listen:
				{
					CStrNonTracked AddressStr = _Address;
					CNetAddress Address = CSocket::fs_ResolveAddress(AddressStr);
					Address.f_SetPort(_Port);

					if (mp_pReportTo)
						mp_SocketSema.f_ReportTo(mp_pReportTo);

					mp_Socket.f_Listen(Address, &mp_SocketSema, NNet::ENetFlag_None);

					mp_ConnectionState.f_Store(EState_Listening);
				}
				break;
			}

			for (int i = 0; i < 1024; ++i)
				mp_FreeDataBlocks.f_Insert(TCRemoteDebuggerPool<CDataBlock>::fs_New());
			for (int i = 0; i < 1024; ++i)
				mp_FreePackets.f_Insert(TCRemoteDebuggerPool<CPacket>::fs_New());
		}

		CConnection::~CConnection()
		{
			if (!!mp_pThread)
				mp_pThread->f_Stop(true);
			mp_Socket.f_Close();
			while(!mp_ReceivedPackets.f_IsEmpty())
				TCRemoteDebuggerPool<CPacket>::fs_Delete(mp_ReceivedPackets.f_Pop());
			while(!mp_FreePackets.f_IsEmpty())
				TCRemoteDebuggerPool<CPacket>::fs_Delete(mp_FreePackets.f_Pop());
			while(!mp_SendData.f_IsEmpty())
				TCRemoteDebuggerPool<CDataBlock>::fs_Delete(mp_SendData.f_Pop());
			while(!mp_FreeDataBlocks.f_IsEmpty())
				TCRemoteDebuggerPool<CDataBlock>::fs_Delete(mp_FreeDataBlocks.f_Pop());
		}

		bint CConnection::f_Connect()
		{
			DMibFastCheck(		(mp_Mode == EMode_Connect) 
							||	( (mp_Mode == EMode_DelayedConnect) && !mp_pThread)  );

			fp_StartThread();
			return true;		
		}

		CConnection::EState CConnection::f_GetState() const
		{
			return mp_ConnectionState.f_Load();
		}

		bint CConnection::f_IsConnected() const
		{
			return mp_ConnectionState.f_Load() == EState_Connected;
		}

		void CConnection::f_ReturnDataBlock(CDataBlock *_pBlock)
		{
			{
				DMibLock(mp_FreeDataBlocksLock);
				mp_FreeDataBlocks.f_Insert(_pBlock);
			}
			mp_FreeDataBlocksAvailable.f_Signal();
		}

		CConnection::CDataBlock* CConnection::f_GetDataBlock()
		{
			while (1)
			{
				{
					DMibLock(mp_FreeDataBlocksLock);
					auto pBlock = mp_FreeDataBlocks.f_Pop();

					if (pBlock)
						return pBlock;
				}
				if (mp_ConnectionState.f_Load() != EState_Connected || NSys::fg_Thread_GetCurrentUID() == mp_pThread->f_GetThreadID())
					return TCRemoteDebuggerPool<CDataBlock>::fs_New();
				mp_FreeDataBlocksAvailable.f_Wait();
			}

			return nullptr;
		}

		void CConnection::fp_ReturnPacket(CPacket *_pPacket)
		{
			{
				DMibLock(mp_FreePacketsLock);
				mp_FreePackets.f_Insert(_pPacket);
			}
			mp_FreePacketsAvailable.f_Signal();
		}

		CPacket *CConnection::fp_GetPacket()
		{
			while (1)
			{
				{
					DMibLock(mp_FreePacketsLock);
					auto pPacket = mp_FreePackets.f_Pop();

					if (pPacket)
						return pPacket;
				}
				if (mp_pReportTo)
					mp_pReportTo->f_Signal();
				mp_FreePacketsAvailable.f_Wait();
			}

			return nullptr;
		}


		void CConnection::f_SendDataBlock(CDataBlock* _pBlock)
		{
			{
				DMibLock(mp_SendLock);
				mp_SendData.f_InsertLast(_pBlock);
			}
			if (mp_bDataToSend.f_Exchange(1) == 0)
				mp_SocketSema.f_Signal();
		}

		CPacketReference CConnection::f_ReceivePacket()
		{
			CPacket *pPacket;
			{

				DMibLock(mp_ReceiveLock);
				pPacket = mp_ReceivedPackets.f_Pop();
			}

			if (pPacket)
				return CPacketReference(pPacket, this);
			return CPacketReference();
		}

		// Can return nullptr. Wait on _pReportTo for when connections.
		TCUniquePointer<CConnection, NMem::CAllocator_NonTrackedHeap> CConnection::f_Accept(NThread::CSemaphoreReportableAggregate* _pReportTo)
		{
			DMibFastCheck(mp_Mode == EMode_Listen);

			TCUniquePointer<CConnection, NMem::CAllocator_NonTrackedHeap> pNewConn = fg_Construct(_pReportTo);
			
			pNewConn->mp_Socket.f_Accept(&mp_Socket, &pNewConn->mp_SocketSema);

			if (pNewConn->mp_Socket.f_IsValid())
			{
				mp_ConnectionState.f_Store(EState_Connected);
				pNewConn->fp_StartThread();
				return fg_Move(pNewConn);
			}
			else
			{
				pNewConn = nullptr;
				return nullptr;
			}
		}

		void CConnection::fp_Process()
		{
			mp_SocketSema.f_ReportTo(&mp_pThread->m_EventWantQuit);

			if (mp_Mode != EMode_Listen)
			{
				// We perform the connection here as at the moment the network subsystem does not support
				// non-tracked strings etc...

				CStrNonTracked AddressStr = mp_Address;
				CNetAddress Address = CSocket::fs_ResolveAddress(AddressStr);
				Address.f_SetPort(mp_Port);

				NTime::CStopWatch Timer(true);
				while (Timer.f_Mark().f_GetSecondsFraction() < 60.0f)
				{
					try
					{
						mp_Socket.f_Connect(Address, &mp_SocketSema);
					}
					catch (NMib::NNet::CExceptionNet const &_Error)
					{
						(void)_Error;
						DMibTrace("Connect Error: {}\n", _Error.f_GetErrorStr());
					}

					if (mp_Socket.f_IsValid())
					{
						break;
					}
					else
					{
						NSys::fg_Thread_Sleep(4.0);
					}
				}

				if (!mp_Socket.f_IsValid())
				{
					mp_ConnectionState.f_Store(EState_Failed);
					return;
				}

				mp_ConnectionState.f_Store(EState_Connected);
			}
			
			mint iHeaderPos = 0;
			CPacketHeader Header;
			CPacket *pInPacket = fp_GetPacket();
			auto Cleanup
				= fg_OnScopeExit
				(
					[&]()
					{
						fp_ReturnPacket(pInPacket);
					}
				)
			;
			mint iDataPos;

			mint iCurSendingPos = 0;
			CDataBlock* pCurSending = nullptr;

			bint bSendStuffed = false;

			auto fl_SendDisconnect =
				[&]()
				{
					CPacket* pNewPacket = TCRemoteDebuggerPool<CPacket>::fs_New();
					pNewPacket->m_Channel = EChannel_System;
					pNewPacket->m_PacketID = EPacket_Sys_Disconnected;

					{
						DMibLock(mp_ReceiveLock);
						mp_ReceivedPackets.f_InsertLast(pNewPacket);
					}
					if (mp_pReportTo)
						mp_pReportTo->f_Signal();

					mp_ConnectionState.f_Store(EState_Disconnected);

					mp_pThread->f_Stop(false);
				};

			while(mp_pThread->f_GetState() != NThread::EThreadState_EventWantQuit)
			{
				ENetTCPState SocketState = mp_Socket.f_GetState();

				if (SocketState & ENetTCPState_Closed)
				{		
					fl_SendDisconnect();
					break;
				}

				try
				{
					if (SocketState & ENetTCPState_Read)
					{
						bint bReadStuffed = false;
						mint nUnreported = 0;
						do
						{
							if (iHeaderPos < sizeof(CPacketHeader))
							{ // Reading header
								mint nToRead = sizeof(CPacketHeader) - iHeaderPos;
								iHeaderPos += mp_Socket.f_Receive( ((uint8*)&Header) + iHeaderPos, nToRead);

								if (iHeaderPos == sizeof(CPacketHeader))
								{
									iDataPos = 0;
									pInPacket->m_Channel = (EChannel)Header.m_Channel;
									pInPacket->m_PacketID = (EPacket)Header.m_PacketID;
									pInPacket->m_Data.f_SetLen(Header.m_nBytes, false);

									/*
									DMibLogCat(RD);
									DMibLog(Debug, "Reading packet: PcktID: {}, Hdr: {}, Payload: {}"
										, (uint32)Header.m_PacketID
										, sizeof(Header)
										, Header.m_nBytes);
									 */
									/*
									DMibLog(Debug, "Reading packet: PcktID: {}, Hdr: {}, Payload: {}")
										<< (uint32)Header.m_PacketID
										<< sizeof(Header)
										<< Header.m_nBytes;
									*/
								}
								else
								{
									bReadStuffed = true;
								}

							}

							if (iHeaderPos == sizeof(CPacketHeader))
							{ // Reading data
								mint nToRead = pInPacket->m_Data.f_GetLen() - iDataPos;

								mint nRead = mp_Socket.f_Receive(&pInPacket->m_Data[iDataPos], nToRead);
								iDataPos += nRead;

								if (iDataPos == pInPacket->m_Data.f_GetLen())
								{
									CPacket *pNewPacket = fp_GetPacket();

									{
										DMibLock(mp_ReceiveLock);
										mp_ReceivedPackets.f_InsertLast(pInPacket);
									}
									pInPacket = pNewPacket;
									++nUnreported;

									if (nUnreported > 100)
									{
										nUnreported = 0;
										if (mp_pReportTo)
											mp_pReportTo->f_Signal();
									}

									iHeaderPos = 0;
								}
								else
								{
									bReadStuffed = true;
								}
							}
						}
						while (!bReadStuffed);

						if (nUnreported)
						{
							nUnreported = 0;
							if (mp_pReportTo)
								mp_pReportTo->f_Signal();
						}
					}

					if (SocketState & ENetTCPState_Write)
						bSendStuffed = false;

					{
						while(!bSendStuffed)
						{
							if (!pCurSending)
							{
								DMibLock(mp_SendLock);
								pCurSending = mp_SendData.f_GetFirst();
								if (pCurSending)
								{
									pCurSending->m_Link.f_Unlink();
									iCurSendingPos = 0;
								}
								if (!pCurSending)
									break;
							}

							mint nToSend = pCurSending->m_Data.f_GetLen() - iCurSendingPos;
							mint nSent = mp_Socket.f_Send(&pCurSending->m_Data[iCurSendingPos], nToSend);

							iCurSendingPos += nSent;

							if (nSent < nToSend)
								bSendStuffed = true;
							else
							{
								f_ReturnDataBlock(pCurSending);
								pCurSending = nullptr;
								iCurSendingPos = 0;
							}
						}
					}
				}
				catch(CExceptionNet const&)
				{
					fl_SendDisconnect();
					break;
				}

				if (mp_bDataToSend.f_Exchange(0) == 0)
				{
					if (mp_pThread->m_EventWantQuit.f_WaitTimeout(0.001))
						bSendStuffed = false;
				}
			}
		}

		void CConnection::fp_StartThread()
		{
			mp_pThread = CThreadObjectNonTracked::fs_StartThread(
						[this](CThreadObjectNonTracked *_pThread) -> aint
						{
							this->fp_Process();
							return 0;
						}
					,	"RemoteDebuggerConnection"
			);
		}



		CClient::CClient(/*TCFunction<void(TCFunction<void()>&&)>&& _Dispatcher*/)
			//: mp_Dispatcher(fg_Move(_Dispatcher))
			: mp_Features(EFeature_None)
			, mp_pOldReporter(nullptr)
		{
			
			auto CommandString = NSys::fg_Process_GetEnvironmentVariable(NStr::CStrNonTracked("Malterlib_RemoteDebugger"));
					
			if (!CommandString.f_IsEmpty())
			{
				mp_Features = (EFeature)fg_GetStrSep(CommandString, "_").f_ToInt(0);
				mp_Address = fg_GetStrSep(CommandString,"_");
				mp_Port = fg_GetStrSep(CommandString, "_").f_ToInt(0);
			}

			mp_pMemoryReporter = fg_Construct(this, true); // mp_Features & EFeature_MemoryStackTrace); // 

			if (f_IsEnabled())
			{
				fp_Initialize(mp_Features);

				mp_pConnection = fg_Construct(CConnection::EMode_DelayedConnect, mp_Address, mp_Port, &mp_ReadReady);
				
				{
					// Notify server of PID
					// Note: The connection will not be connected atm, but this message will be buffered to
					// be send when the connection is made.
					CSysPacket_ClientConnect Packet =
					{
						NProcess::NPlatform::fg_Process_GetCurrentUID()
					};

					mp_pConnection->f_SendPacket(EChannel_System, EPacket_Sys_ClientConnect
						, Packet
						, nullptr
						);
				}
			}
		}

		CClient::~CClient()
		{
			if (mp_Features & EFeature_MemoryReporting)
			{
#if DMibConfig_Memory_Shims_Enable
				NMem::fg_ReportMemoryGloballyTo(nullptr);
#endif
				mp_pMemoryReporter = nullptr;
			}
		}

		bint CClient::f_IsEnabled()
		{
			return (mp_Features != EFeature_None) && (mp_Port != 0) && (!mp_Address.f_IsEmpty());
		}

		bint CClient::f_Connect()
		{
			if (!mp_pConnection)
				return false;

			mp_pConnection->f_Connect();

			mp_pThread = CThreadObjectNonTracked::fs_StartThread(
						[this](NThread::CThreadObjectNonTracked *_pThread) -> aint
						{
							this->fp_Process();
							return 0;
						}
					,	"RemoteDebuggerClient"
			);

			return true;
		}

		template<typename t_CPacket>
		bint fg_ExtractPacket(t_CPacket& _ToHere, TCVector<uint8, NMem::CAllocator_NonTrackedHeap> const& _FromHere)
		{
			if (_FromHere.f_GetLen() < sizeof(t_CPacket))
				return false;
			fg_MemCopy(&_ToHere, _FromHere.f_GetArray(), sizeof(t_CPacket));
			return true;
		}

		void CClient::fp_Process()
		{
			mp_pThread->m_EventWantQuit.f_ReportTo(&mp_ReadReady);

			while(mp_pThread->f_GetState() != NThread::EThreadState_EventWantQuit)
			{
				auto Packet = mp_pConnection->f_ReceivePacket();
				if (Packet)
				{
					switch(Packet.f_Channel())
					{
						case EChannel_System:
							/*
							switch(PacketID)
							{
								case EPacket_Sys_Initialize:
									{
										CSysPacket_Initialize InitPacket;
										if (fg_ExtractPacket(InitPacket, Data))
										{
											EFeature Features = (EFeature)InitPacket.m_Features;
											mp_Dispatcher(
												[this, Features]()
												{
													fp_Initialize(Features);
												}
											);
										}
									}
									break;
							}
							*/
							break;
						case EChannel_Memory:
							break;
					}
				}

				mp_ReadReady.f_Wait();
			}			
		}

		void CClient::fp_Initialize(EFeature _Features)
		{
			mp_Features = _Features;

			if (mp_Features & EFeature_MemoryReporting)
			{
#if DMibConfig_Memory_Shims_Enable
				NMem::fg_ReportMemoryGloballyTo(mp_pMemoryReporter.f_Get());
#endif
			}
			else
			{
#if DMibConfig_Memory_Shims_Enable
				NMem::fg_ReportMemoryGloballyTo(nullptr);
#endif
				mp_pMemoryReporter = nullptr;
			}
		}

		// CServer

		CServer::CServer(CServerSettings&& _Settings)
			: mp_Settings(fg_Move(_Settings))
			, mp_ClientPID(0)
		{		
		}

		CServer::~CServer()
		{
			f_Stop();
		}

		bint CServer::f_Start()
		{
			if (!!mp_pThread)
				return false; // Already running.
			
			mp_pThread = CThreadObjectNonTracked::fs_StartThread(
						[this](NThread::CThreadObjectNonTracked *_pThread) -> aint
						{
							this->fp_Process();
							return 0;
						}
					,	"RemoteDebuggerServer"
			);

					return true;
		}

		bint CServer::f_IsRunning()
		{
			return !!mp_pThread;
		}

		void CServer::f_Stop()
		{
			if (!!mp_pThread)
			{
				mp_pThread->f_Stop(true);
			}

			if (mp_pConnection)
			{
				mp_pConnection = nullptr;
			}
		}

		void CServer::fp_Process()
		{
			while(mp_pThread->f_GetState() != NThread::EThreadState_EventWantQuit)
			{
				if (!mp_pConnection)
					fp_Process_Listening();
				else
					fp_Process_Connected();
			}
		}

		void CServer::fp_Process_Listening()
		{
			TCUniquePointer<CConnection, NMem::CAllocator_NonTrackedHeap> pListener;
			pListener = fg_Construct(
							CConnection::EMode_Listen
						, 	mp_Settings.m_Address
						,	mp_Settings.m_Port
						,	&mp_pThread->m_EventWantQuit
			);

			if (pListener->f_GetState() != CConnection::EState_Listening)
			{
				pListener = nullptr;
				mp_pThread->f_Stop(false);
				fp_EmitEvent(EServerEvent_FatalError);
				return;
			}

			while(mp_pThread->f_GetState() != NThread::EThreadState_EventWantQuit)
			{
				if ( !!(mp_pConnection = pListener->f_Accept(&mp_ConnectionReady)) )
				{
					return;
				}

				mp_pThread->m_EventWantQuit.f_Wait();
			}
		}

		void CServer::fp_Process_Connected()
		{

			mp_pThread->m_EventWantQuit.f_ReportTo(&mp_ConnectionReady);

			{				
				CSysPacket_Initialize InitPacket = { uint32(mp_Settings.m_Features) };
				mp_pConnection->f_SendPacket(EChannel_System, EPacket_Sys_Initialize, InitPacket, nullptr);
			}

			while(mp_pThread->f_GetState() != NThread::EThreadState_EventWantQuit)
			{
				for (;;)
				{
					auto Packet = mp_pConnection->f_ReceivePacket();
					if (!Packet)
						break;
					switch (Packet.f_Channel())
					{
						case EChannel_System:
							switch (Packet.f_PacketID())
							{
							case EPacket_Sys_Disconnected:
								{
									mp_pConnection = nullptr;
									return;
								}
								break;
							case EPacket_Sys_ClientConnect:
								{
									auto &Data = Packet.f_Data();
									NStream::CBinaryStreamMemoryPtr<> Stream;
									Stream.f_OpenRead(Data.f_GetArray(), Data.f_GetLen());

									CSysPacket_ClientConnect Packet;
									Packet.f_Read(Stream);

									mp_ClientPID = Packet.m_PID;
									fp_EmitEvent(EServerEvent_Connected);
								}
								break;
							}
							break;
						case EChannel_Memory:
							if (mp_Settings.m_pMemoryReporter)
								fp_DecodeMemoryPacket(Packet.f_PacketID(), Packet.f_Data());
							break;
					}
				}

				mp_ConnectionReady.f_Wait();
			}
		}

		void CServer::fp_EmitEvent(EServerEvent _Event)
		{
			if (!!mp_Settings.m_EventCallback)
			{
				mp_Settings.m_Dispatcher(
					[this, _Event]()
					{
						mp_Settings.m_EventCallback(_Event);
					}
				);				
			}
		}

		NAggregate::TCAggregateSimple<CClient> g_RDClient = {DAggregateInit};
		NAggregate::TCAggregateSimple<CServer> g_RDServer = {DAggregateInit};

		static CClient* g_pRDClient = nullptr;
		static CServer* g_pRDServer = nullptr;

		bint fg_RD_InitializeServer(CServerSettings&& _Settings)
		{
			if (g_pRDServer)
				return true;

			g_RDServer.f_Construct(fg_Move(_Settings));
			g_pRDServer = &*g_RDServer;
			if (!g_pRDServer->f_Start())
			{
				g_RDServer.f_Destruct();
				g_pRDServer = nullptr;
				return false;
			}

			return true;
		}


		uint64 fg_RD_ServerGetClientPID()
		{
			if (!g_pRDServer)
				return 0;

			return g_pRDServer->f_GetClientPID();
		}

		void fg_RD_DeinitializeServer()
		{
			if (g_pRDServer)
			{
				g_RDServer.f_Destruct();
				g_pRDServer = nullptr;
			}
		}

		bint fg_RD_InitializeClient()
		{
			if (g_pRDClient)
				return true;

			g_RDClient.f_Construct();
			g_pRDClient = &*g_RDClient;

			return true;
		}

		bint fg_RD_NetworkAvailableForClient()		
		{
			if (!g_pRDClient)
				return false;

			if (g_pRDClient->f_IsEnabled())
				return g_pRDClient->f_Connect();
			else
				return true;
		}

		void fg_RD_DeinitializeClient()
		{
			if (g_pRDClient)
			{
				g_RDClient.f_Destruct();
				g_pRDClient = nullptr;
			}
		}

	} // Namespace NMem

} // Namespace NMib

#endif
