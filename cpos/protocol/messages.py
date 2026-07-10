from __future__ import annotations
import json
from base64 import b64encode, b64decode
import pickle
from typing import Self

from cpos.core.block import Block
from cpos.core.transactions import TransactionList
from cpos.p2p.peer import State

class MessageCode:
    UNIMPLEMENTED = 0xFF,
    NOTIFY_BEACON = 0x00,
    HELLO = 0x1,
    BLOCK_BROADCAST = 0x2,
    PEER_LIST_REQUEST = 0x3,
    PEER_LIST = 0x4,
    PEER_FORGET_REQUEST = 0x5,
    SMR = 0x6,
    PING = 0x7,
    PONG = 0x8,

class MessageParseError(Exception):
    pass

class Message:
    """Class that represents the protocol message frames."""

    def __init__(self):
        self.code = MessageCode.UNIMPLEMENTED
        pass

    def serialize(self) -> bytes:
        return pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def deserialize(cls, raw) -> Self:
        return pickle.loads(raw)


class Hello(Message):
    def __init__(self, peer_id: bytes, peer_port: int | str):
        self.code = MessageCode.HELLO
        self.peer_id = peer_id
        self.peer_port = peer_port

    def __str__(self):
        return f"Hello(id={self.peer_id.hex()[0:8]}, port={self.peer_port})"

class Ping(Message):
    def __init__(self,  peer_ip: str, peer_id: bytes, peer_port: int | str):
        self.code = MessageCode.PING
        self.peer_ip = peer_ip
        self.peer_id = peer_id
        self.peer_port = peer_port

    def __str__(self):
        return f"Ping(id={self.peer_id.hex()[0:8]}, port={self.peer_port}, ip={self.peer_ip})"

class Pong(Message):
    def __init__(self,  peer_ip: str, peer_id: bytes, peer_port: int | str):
        self.code = MessageCode.PONG
        self.peer_ip = peer_ip
        self.peer_id = peer_id
        self.peer_port = peer_port

    def __str__(self):
        return f"Pong(id={self.peer_id.hex()[0:8]}, port={self.peer_port}, ip={self.peer_ip})"

class SMR(Message):
    def __init__(self, peer_ip: str, peer_port: int, peer_id: bytes, round: int, state: State):
        self.code = MessageCode.SMR
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.peer_id = peer_id
        self.round = round
        self.state = state
    def __str__(self):
        return f"SMR(id={self.peer_id.hex()[0:8]}, port={self.peer_port}, ip={self.peer_ip}, round={self.round}, state={self.state.name})"

class BlockBroadcast(Message):
    def __init__(self, block: Block, peer_id: bytes):
        self.code = MessageCode.BLOCK_BROADCAST
        self.block = block
        self.peer_id = peer_id

    def __str__(self):
        return self.block.__str__()
    
    def __repr__(self):
        return self.__str__()

class PeerListRequest(Message):
    def __init__(self, node_id: bytes):
        self.code = MessageCode.PEER_LIST_REQUEST
        self.node_id = node_id

class PeerForgetRequest(Message):
    def __init__(self, peer_id: bytes):
        self.peer_id = peer_id
        self.code = MessageCode.PEER_FORGET_REQUEST

class PeerList(Message):
    def __init__(self, peerlist: list[tuple[str, str | int, bytes]]):
        self.code = MessageCode.PEER_LIST
        self.peerlist = peerlist

# Ask for the last `block_count` blocks in peer's blockchain view
class ResyncRequest(Message):
    def __init__(self, peer_id: bytes, block_index: int):
        self.peer_id = peer_id
        self.block_index = block_index

    def __str__(self):
        return f"ResyncRequest(peer_id={self.peer_id})"

    def __repr__(self):
        return self.__str__()

class ResyncResponse(Message):
    def __init__(self, block_received: Block):
        self.block_received = block_received

