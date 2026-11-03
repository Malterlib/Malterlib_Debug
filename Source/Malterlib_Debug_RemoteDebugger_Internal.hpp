// Copyright © Unbroken AB
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

namespace NMib::NDebug::NRemoteDebugger
{
	template <typename t_CType, umint t_GrowSize>
	template <typename ...tfp_CParams>
	t_CType *TCRemoteDebuggerPool<t_CType, t_GrowSize>::fs_New(tfp_CParams && ...p_Params)
	{
		auto Memory = NMemory::CAllocator_NonTrackedHeap::f_AllocSafe(sizeof(t_CType), alignof(t_CType));
		auto pReturn = new(Memory.m_pMemory) t_CType(fg_Forward<tfp_CParams>(p_Params)...);
		Memory.f_Claim();
		return pReturn;
	}

	template <typename t_CType, umint t_GrowSize>
	void TCRemoteDebuggerPool<t_CType, t_GrowSize>::fs_Delete(t_CType *_pObject)
	{
		_pObject->~t_CType();
		NMemory::CAllocator_NonTrackedHeap::f_Free(_pObject, sizeof(t_CType));
	}

	inline CPacket::CPacket()
	{
	}

	inline CPacket::CPacket(CPacket &&_ToMove)
		: m_Channel(_ToMove.m_Channel)
		, m_PacketID(_ToMove.m_PacketID)
		, m_Data(fg_Move(_ToMove.m_Data))
	{
	}

	inline CPacket::CPacket(CPacket const &_Other)
	{
	}

	inline CPacketReference::CPacketReference(CPacket *_pPacket, CConnection *_pConnection)
		: mp_pPacket(_pPacket)
		, mp_pConnection(_pConnection)
	{
	}

	inline CPacketReference::CPacketReference()
		: mp_pPacket(nullptr)
		, mp_pConnection(nullptr)
	{
	}

	inline CPacketReference::CPacketReference(CPacketReference &&_Other)
		: mp_pPacket(_Other.mp_pPacket)
		, mp_pConnection(_Other.mp_pConnection)
	{
		_Other.mp_pPacket = nullptr;
		_Other.mp_pConnection = nullptr;
	}

	inline CPacketReference::operator bool ()
	{
		return mp_pPacket != nullptr;
	}

	inline EChannel CPacketReference::f_Channel() const
	{
		return mp_pPacket->m_Channel;
	}

	inline EPacket CPacketReference::f_PacketID() const
	{
		return mp_pPacket->m_PacketID;
	}

	inline CDataBuffer const &CPacketReference::f_Data()
	{
		return mp_pPacket->m_Data;
	}

	template <typename tf_CPacket>
	void CConnection::CDataBlock::f_Fill(EChannel _Channel, EPacket _PacketID, tf_CPacket const &_Packet, TCStackTrace<umint> const *_pTrace)
	{
		m_Channel = _Channel;

		NStream::TCBinaryStreamMemoryRef<NStream::CBinaryStreamDefault, CDataBuffer> Stream(m_Data);
		Stream.f_ResetStream();

		CPacketHeader Header = {(uint8)_Channel, (uint8)0, (uint16)_PacketID, 0};

		Header.f_Write(Stream);

		umint nHeaderBytes = Stream.f_GetPosition();

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

	template <typename tf_CPacket>
	void CConnection::f_SendPacket(EChannel _Channel, EPacket _PacketID, tf_CPacket const &_Packet, TCStackTrace<umint> const *_pTrace)
	{
		CDataBlock *pBlock = f_GetDataBlock();
		pBlock->f_Fill(_Channel, _PacketID, _Packet, _pTrace);
		f_SendDataBlock(pBlock);
	}

	inline CConnection *CClient::f_GetConnection()
	{
		return mp_pConnection.f_Get();
	}

	inline uint64 CServer::f_GetClientPID() const
	{
		return mp_ClientPID;
	}
}
