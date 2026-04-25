from __future__ import annotations
from hashlib import sha256
from cpos.core.transactions import TransactionList
from time import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

class MiniBlock:
    # TODO: document the following changes:
    # - Use regular SHA-256 hashes instead of Merkle tree roots for transactions
    # - Use the node's pubkey as its ID
    # - When calculating the node hash, use the hash of the previous block instead
    #   of the epoch head
    def __init__(self, parent_hash: bytes, transactionlist: TransactionList,
                 owner_pubkey: bytes, signed_node_hash: bytes,
                 round: int, index: int, ticket_number: int):
        self.parent_hash = parent_hash
        self.owner_pubkey = owner_pubkey
        self.signed_node_hash = signed_node_hash
        self.round = round
        self.index = index
        self.transactions = transactionlist.transactions # Only string with transations
        self.transaction_hash = transactionlist.transactions_hash
        self.ticket_number = ticket_number
        self.create_hash()

    def create_hash(self):
        self.node_hash = self.calculate_node_hash()
        self.hash = self.calculate_hash()

    def calculate_node_hash(self):
        # TODO: document somewhere that we're representing the
        # round number and block index as little-endian uint32_t
        # TODO: document that we're using the owner_pubkey as the ID
        return sha256(self.owner_pubkey +
                      self.round.to_bytes(4, "little", signed=False) +
                      self.parent_hash).digest()

    def calculate_hash(self) -> bytes:
        return sha256(self.parent_hash + self.transaction_hash).digest()

    def __str__(self):
        return f"MiniBlock (hash={self.hash.hex()[0:8]}, parent={self.parent_hash.hex()[0:8]}, owner={self.owner_pubkey.hex()[0:8]}, round={self.round}, index={self.index})"

    def __repr__(self):
        return self.__str__()

    def sign_miniBlock(self, privkey: Ed25519PrivateKey, miniBlock: MiniBlock):
        self.signed_node_hash = privkey.sign(miniBlock.node_hash)
        
    def compose_miniBlock(self, miniBlock_info):
        transaction_list = TransactionList()
        transaction_list.set_transactions(miniBlock_info[9])
        b = MiniBlock(parent_hash=bytes.fromhex(miniBlock_info[3]),
                      owner_pubkey=bytes.fromhex(miniBlock_info[5]),
                      signed_node_hash=bytes.fromhex(miniBlock_info[6]), 
                      round=miniBlock_info[2],
                      index=miniBlock_info[0],
                      transactionlist=transaction_list, 
                      ticket_number=miniBlock_info[8])
        return b
        
class MiniBlockList:
    def __init__(self, miniBlockList: List[MiniBlock] = None):
        self.miniBlocks = miniBlockList if miniBlockList is not None else []
        self.miniBlockParent = b"\x00"
        self.round = -1
        self.index = -1
        self.timestamp = time()
    
    def __str__(self):
        return (
            f"MiniBlockList(hash={self.miniBlocks}, parent={self.miniBlockParent.hex()}, "
                        f"round={self.round}, index={self.index}, timestamp={self.timestamp})"
        )

    def insert_miniBlock(self, miniBlock: MiniBlock):
        if miniBlock is None:
            return

        if self.miniBlocks is None or len(self.miniBlocks) == 0:
            self.miniBlockParent = miniBlock.parent_hash
            self.round = miniBlock.round
            self.index = miniBlock.index

        if miniBlock.parent_hash != self.miniBlockParent:
            return
        self.miniBlocks.append(miniBlock.hash)
    
    def clear_miniBlocks(self):
        self.miniBlocks = []
        self.miniBlockParent = b"\x00"
        self.round = -1
        self.index = -1
        self.timestamp = time()

    def get_hash(self) -> bytes:
        if self.miniBlocks is not None and len(self.miniBlocks) > 0:
            return sha256(''.join(self.miniBlocks).encode()).digest()
        else:
            return None
    