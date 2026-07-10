from __future__ import annotations
from enum import Enum

class State(Enum):
    UNKNOWN      = 0x99,
    INITIAL      = 0x00,
    INITIALIZING = 0x01,
    INITIALIZED  = 0x02,
    STARTING     = 0x03,
    PROPOSALS    = 0x04,
    FINALIZED    = 0x05,
    RESYNCING    = 0x06,
    IDLE         = 0x98,

class Peer:
    def __init__(self, peer_ip: str, peer_port: int, peer_id: bytes):
        self.ip = peer_ip
        self.port= peer_port
        self.id = peer_id
        self.state = State.UNKNOWN
        self.round = -1
        self.connected = False

    def update_state(self, state: State, round: int, connected: bool):
        self.state = state
        self.round = round
        self.connected = connected

    def __str__(self):
        return f"({self.ip}:{self.port}, {self.id.hex()[0:8]}, state={self.state.name}, round={self.round}, connected={self.connected})"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, peer: Peer):
        return self.id == peer.id
