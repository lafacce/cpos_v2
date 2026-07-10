from typing import Self
import pickle
from cpos.p2p.peer import Peer

class MessageCode:
    UNIMPLEMENTED = 0xFF,
    NOTIFY_BEACON = 0x00,
    HELLO = 0x1,
    BLOCK_BROADCAST = 0x2,
    PEER_LIST_REQUEST = 0x3,
    PEER_LIST = 0x4,
    PEER_FORGET_REQUEST = 0x5,
    SMR = 0x6,

class Message:
    def __init__(self, code):
        self.code = MessageCode.UNIMPLEMENTED

    def serialize(self) -> bytes:
        msg_raw = pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)
        return msg_raw

    @classmethod
    def deserialize(cls, raw) -> Self:
        return pickle.loads(raw)

class Hello(Message):
    def __init__(self, port: int, id: bytes, ip: str):
        self.code = MessageCode.HELLO
        self.port = port
        self.id = id
        self.ip = ip
    
    def __str__(self):
        return f"SelfIntroduction: (port={self.port}, id={self.id.hex()[0:8]}, ip={self.ip})"

class PeerList(Message):
    def __init__(self, peerlist: list[Peer]):
        self.code = MessageCode.PEER_LIST
        self.peers = peerlist

    def __str__(self):
        return f"{self.peers}"
    
    def __repr__(self):
        return self.__str__()

class PeerListRequest(Message):
    def __init__(self, requester_id: bytes):
        self.code = MessageCode.PEER_LIST_REQUEST
        self.requester_id = requester_id

class NotifyBeacon(Message):
    def __init__(self, port: int, id: bytes, ip: str):
        self.code = MessageCode.NOTIFY_BEACON
        self.port = port
        self.id = id
        self.ip = ip
