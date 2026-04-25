import base64
import datetime
import hashlib
import mysql.connector
import numpy as np
import os
import signal
from time import sleep
from cpos.core.block import Block, GenesisBlock
from cpos.core.transactions import TransactionList, MockTransactionList
from cpos.core.sortition import fork_threshold, run_sortition, confirmation_threshold
from cpos.core.miniBlock import MiniBlock
from time import time
from typing import Optional
from collections import OrderedDict
import logging
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature


HOST = "localhost"
USER = "CPoS"
PASSWORD = "CPoSPW"
DATABASE = "localBlockchain"
PROGRAM_INTERRUPTED = False

try:
    connection = mysql.connector.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )

except mysql.connector.Error as err:
    print(f"Error: {err}")

def sighandler(*args):
    global PROGRAM_INTERRUPTED 
    PROGRAM_INTERRUPTED = True

class BlockChainParameters:
    def __init__(self, round_time: float, tolerance: int, tau: int, miniTau:int, total_stake: int, period: int):
        self.round_time = round_time
        self.tolerance = tolerance
        self.tau = tau
        self.miniTau = miniTau
        self.total_stake = total_stake
        self.period = period
        pass

class BlockChainDatabase:

    def __init__(self):
        self.cursor = None

    def get_cursor(self):
        self.cursor = connection.cursor()

    def close_cursor(self):
        self.cursor.close()
        self.cursor = None

    def _dump_state(self):
        self.cursor.execute("SELECT * FROM localChains ORDER BY block_index ASC")
        for block in cursor:
            print(block)
        connection.commit()

    def _dump_indexes(self):
        self.cursor.execute("SELECT block_index FROM localChains ORDER BY block_index ASC")
        for index in cursor:
            print(index)
        connection.commit()
    
    def _dump_block_hashes(self):
        block_hashes = []
        self.cursor.execute("SELECT hash FROM localChains ORDER BY block_index ASC")
        for hash in self.cursor:
            block_hashes.append(hash[0][0:min(len(hash[0]),8)])
        connection.commit()
        return block_hashes

    def insert_block(self, block: Block, arrive_time: int, confirmed: int):
        database_atributes = [block.index, block.hash.hex(), block.round, block.parent_hash.hex(), block.hash.hex(), block.owner_pubkey.hex(), block.signed_node_hash.hex(), block.merkle_root.hex(), block.ticket_number,
                            block.transactions, arrive_time, 0, confirmed, 0, block.proof_hash.hex(), 0, 0] # TODO hash as id? TODO implement real merkle tree
        INSERT_QUERY = "INSERT INTO localChains (block_index, id, round, parent_hash, hash, owner_pubkey, signed_node_hash, merkle_root, ticket_number, miniBlocks, arrive_time, fork, confirmed, subuser, proof_hash, numSuc, round_stable) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        self.cursor.execute(INSERT_QUERY, database_atributes)
        connection.commit()

    def insert_genesis_block(self, block: Block, arrive_time: int, confirmed: int):
        database_atributes = [block.index, block.hash.hex(), block.round, block.parent_hash.hex(), block.hash.hex(), block.owner_pubkey.hex(), block.signed_node_hash.hex(), block.miniBlocks, block.ticket_number,
                              str([]), arrive_time, 0, confirmed, 0, block.proof_hash.hex(), 0, 0] # TODO hash as id? TODO implement real merkle tree
        INSERT_QUERY = "INSERT INTO localChains (block_index, id, round, parent_hash, hash, owner_pubkey, signed_node_hash, merkle_root, ticket_number, miniBlocks, arrive_time, fork, confirmed, subuser, proof_hash, numSuc, round_stable) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        self.cursor.execute(INSERT_QUERY, database_atributes)
        connection.commit()
    
    def block_in_blockchain(self, block: Block):
        FIND_BLOCK_QUERY = "SELECT * FROM localChains WHERE id = %s LIMIT 1" # TODO hash as id?
        self.cursor.execute(FIND_BLOCK_QUERY, [block.hash.hex()])
        element = self.cursor.fetchone()
        block_in_blockchain = (element != None)
        return block_in_blockchain
    
    def number_of_blocks(self):
        self.cursor.execute("SELECT COUNT(*) FROM localChains")
        count = self.cursor.fetchone()[0]
        return count

    def has_correct_parent(self, block: Block):
        self.cursor.execute(f"SELECT hash FROM localChains WHERE block_index = {block.index - 1}")
        hash = bytes.fromhex(self.cursor.fetchone()[0])
        return hash == block.parent_hash

    def delete_blocks_since(self, index: int):
        self.cursor.execute(f"DELETE FROM localChains WHERE block_index >= {index}")
        connection.commit()
    
    def last_confirmed_block_info(self):
        self.cursor.execute("SELECT block_index, id, round FROM localChains WHERE confirmed = 1 ORDER BY block_index DESC LIMIT 1")
        block_index, id, round = self.cursor.fetchone()
        id = bytes.fromhex(id)
        return block_index, id, round
    
    def last_block_id(self):
        self.cursor.execute("SELECT id FROM localChains ORDER BY block_index DESC LIMIT 1")
        id = bytes.fromhex(self.cursor.fetchone()[0])
        return id
    
    def oldest_unconfirmed_block(self):
        self.cursor.execute("SELECT block_index, id, numSuc, round FROM localChains WHERE confirmed = 0 ORDER BY block_index ASC LIMIT 1")
        block_index, id, numSuc, round = self.cursor.fetchone()
        id = bytes.fromhex(id)
        return block_index, id, numSuc, round
    
    def confirm_block(self, id):
        self.cursor.execute(f'UPDATE localChains SET confirmed = 1 WHERE id = "{id.hex()}"')
        connection.commit()

    def update_successfull_sortition(self, index, winning_tickets):
        self.cursor.execute(f"UPDATE localChains SET numSuc = numSuc + {winning_tickets} WHERE block_index < {index} AND confirmed = 0")
        connection.commit()

    def get_proof_hash_of_block(self, index):
        self.cursor.execute(f"SELECT proof_hash FROM localChains WHERE block_index = {index}")
        proof_hash = bytes.fromhex(self.cursor.fetchone()[0])
        return proof_hash
    
    def get_round_of_block(self, index):
        self.cursor.execute(f"SELECT round FROM localChains WHERE block_index = {index}")
        block_round = self.cursor.fetchone()[0]
        return block_round
    
    def contains_in_db(self, block: Block): # TODO hash as id? OPTIMIZABLE WITH SQL COMMAND
        self.cursor.execute(f"SELECT hash FROM localChains")
        for h in self.cursor:
            hash = bytes.fromhex(h)
            if hash == block.hash:
                return True
        return False
    
    def get_last_block_hash(self): # TODO hash as id?
        self.cursor.execute("SELECT hash FROM localChains ORDER BY block_index DESC LIMIT 1")
        block_hash = bytes.fromhex(self.cursor.fetchone()[0])
        return block_hash
    
    def block_of_hash(self, hash):
        # Returns a two element list in format [id, block_index] or None
        BLOCK_OF_HASH_QUERY = f'SELECT id, block_index FROM localChains WHERE hash = "{hash.hex()}" ORDER BY block_index ASC LIMIT 1'
        self.cursor.execute(BLOCK_OF_HASH_QUERY)
        info = self.cursor.fetchone()
        if info != None:
            info = list(info)
            info[0] = bytes.fromhex(info[0])
        return info
    
    def blocks_since_index(self, index):
        blocks_info = []
        self.cursor.execute(f"SELECT * FROM localChains WHERE block_index >= {index} ORDER BY block_index")
        for i in self.cursor:
            blocks_info.append(i)
        return blocks_info
    
    def reintroduce_blocks(self, list_of_blocks_data):
        for block_data in list_of_blocks_data:
            INSERT_QUERY = "INSERT INTO localChains (block_index, id, round, parent_hash, hash, owner_pubkey, signed_node_hash, merkle_root, ticket_number, transactions, arrive_time, fork, confirmed, subuser, proof_hash, numSuc, round_stable) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            self.cursor.execute(INSERT_QUERY, block_data)
        connection.commit()
    
    def last_n_blocks(self, n):
        # Returns in the form of a list of blocks
        block_list = []
        self.cursor.execute(f"SELECT * FROM localChains ORDER BY block_index ASC LIMIT {n}")
        for block_info in self.cursor:
            block_list.append(self.compose_block(block_info))
        return block_list

    def block_by_index(self, block_index):
        # Returns in the form of a Block class
        if block_index < 0:
            block_index = self.number_of_blocks() + block_index
        self.cursor.execute(f"SELECT * FROM localChains WHERE block_index = {block_index}")
        block_info = self.cursor.fetchone()
        return self.compose_block(block_info)

    def insert_miniBlock(self, miniBlock: MiniBlock, arrive_time: int, confirmed: int, winning_tickets: int):
        database_atributes = [miniBlock.index, miniBlock.hash.hex(), miniBlock.round, miniBlock.parent_hash.hex(), miniBlock.hash.hex(), miniBlock.owner_pubkey.hex(), miniBlock.signed_node_hash.hex(), "", miniBlock.ticket_number,
                            miniBlock.transactions, arrive_time, confirmed, 0, winning_tickets, 0] # TODO hash as id? TODO implement real merkle tree
        INSERT_QUERY = "INSERT INTO localMiniBlocks (miniBlock_index, id, round, parent_hash, hash, owner_pubkey, signed_node_hash, merkle_root, ticket_number, transactions, arrive_time, confirmed, subuser, numSuc, round_stable) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        self.cursor.execute(INSERT_QUERY, database_atributes)

        temp_attributes = {miniBlock.hash.hex()}
        TEMP_QUERY = f"INSERT INTO tempMiniBlocks (hash) VALUES (%s)"
        self.cursor.execute(TEMP_QUERY, (miniBlock.hash.hex(),))
        connection.commit()

    def clear_tempMiniBlocks(self):
        TRUNCATE_QUERY = "TRUNCATE TABLE tempMiniBlocks"
        self.cursor.execute(TRUNCATE_QUERY)
        connection.commit()

class BlockChain:

    def __init__(self, parameters: BlockChainParameters, genesis: Optional[GenesisBlock] = None, node_id: bytes = None):
        logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(f"[%(asctime)s][%(levelname)s] {__name__}: [{node_id.hex()[0:8]}] %(message)s")
        logger.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.logger = logger
        
        self.parameters: BlockChainParameters = parameters
        self.blockChainDatabase: BlockChainDatabase = BlockChainDatabase()

        if genesis is not None:
            self.genesis: GenesisBlock = genesis
        else:
            self.genesis: GenesisBlock = GenesisBlock()

        self.blockChainDatabase.get_cursor()
        self.blockChainDatabase.insert_genesis_block(genesis, 0, 1) # TODO CHECK ARRIVE TIME OF GENESIS BLOCK, genesis block is altomatically confirmed
        # TODO: this stores the number of successful sortitions that have
        # a certain block into the foreign blockchain view; document/find
        # better naming later
        self.blockChainDatabase.close_cursor()
        self.last_confirmation_delay: int = 0
        self.fork_detected = False
        self.forks_detected = 0 

        self.current_round: int = 0
        # TODO: this is a temporary hack, we should be able to query the total number of nodes in the network at runtime for a period
        self.total_nodes = parameters.total_stake 
        self.confirmation_delays = []
        self.update_round()

    def update_round(self):
        current_time = time()
        genesis_time = self.genesis.timestamp
        delta_t = current_time - genesis_time
        round = int(delta_t / self.parameters.round_time)

        if self.current_round == round:
            return

        self.blockChainDatabase.get_cursor()
        self.current_round = round

        self.logger.info(f"starting round {round}")
        self.logger.info(f"current chain: {self.blockChainDatabase._dump_block_hashes()}") 
        self.blockChainDatabase.clear_tempMiniBlocks()

        # verify whether we can confirm the oldest unconfirmed block or
        # whether a fork has been detected
        # (this fork detection logic really, REALLY needs to be its own class)

        # should only happen if the chain only has the genesis block
        last_confirmed_block_index, last_confirmed_block_id, last_confirmed_block_round = self.blockChainDatabase.last_confirmed_block_info()

        if last_confirmed_block_id == self.blockChainDatabase.last_block_id(): 
            return
        
        block_confirmed = True

        while block_confirmed:
            oldest_index, oldest_id, oldest_numSuc, oldest_round = self.blockChainDatabase.oldest_unconfirmed_block()
            delta_r = round - oldest_round - 1

            if delta_r > 0 and oldest_index > 0:
                successful_avg = oldest_numSuc / delta_r
                self.logger.debug(f"oldest unconfirmed block: {oldest_id}, delta_r: {delta_r}, s: {successful_avg}")

                # TODO: make the epsilon threshold variable
                conf_thresh = confirmation_threshold(total_stake=self.parameters.total_stake,
                                    tau=self.parameters.tau,
                                    delta_r=delta_r,
                                    threshold=1e-6)
                self.logger.debug(f"s_min: {conf_thresh}")

                if successful_avg > conf_thresh:
                    self.logger.debug(f"confirmed block {oldest_id}")
                    self.blockChainDatabase.confirm_block(oldest_id)
                    self.confirmation_delays.append([oldest_id, oldest_index, self.current_round - oldest_round]) # measured in rounds
                    self.last_confirmation_delay = self.current_round - last_confirmed_block_round
                
                else:
                    block_confirmed = False

            else:
                block_confirmed = False

        if delta_r > 0 and oldest_index > 0:
            fork_thresh = fork_threshold(total_stake=self.parameters.total_stake,
                                tau=self.parameters.tau,
                                delta_r=delta_r,
                                threshold=0.95)
        
            if successful_avg < fork_thresh:
                self.fork_detected = True
                self.forks_detected += 1
                self.logger.info(f"fork detected!")
        self.blockChainDatabase.close_cursor()

    def _log_failed_verification(self, block: Block, reason: str):
        self.logger.debug(f"failed to verify block {block.hash.hex()} ({reason})")

    # TODO: these two are stubs, we need to implement an actual search
    # through the blockchain transactions later
    def lookup_node_stake(self, node_id: bytes) -> int:
        return 1
    def lookup_total_stake(self) -> int:
        return self.parameters.total_stake

    def validate_block(self, block: Block) -> Optional[int]:
        pubkey = None
        try:
            pubkey = Ed25519PublicKey.from_public_bytes(block.owner_pubkey)
        except ValueError:
            self._log_failed_verification(block, "bad pubkey")
            return None
        
        try:
            pubkey.verify(block.signed_node_hash, block.node_hash)
        except InvalidSignature:
            self._log_failed_verification(block, "bad node_hash signature")
            return None

        stake = self.lookup_node_stake(block.owner_pubkey)
        total_stake = self.lookup_total_stake()
        success_probability = self.parameters.tau / total_stake
        winning_tickets = run_sortition(block.signed_node_hash, stake, success_probability)
        self.logger.debug(f"ran sortition for block {block.hash.hex()[0:7]} (p = {success_probability}); result = {winning_tickets}") 
        if winning_tickets == 0 or winning_tickets < block.ticket_number:
            self._log_failed_verification(block, "sortition failed")
            return None
        
        return winning_tickets
    
    def _log_failed_insertion(self, block: Block, reason: str):
        self.logger.info(f"discarding block {block.hash.hex()} ({reason})")

    # try to insert a block at the end of the chain
    def insert_block(self, block: Block) -> bool:

        if self.block_in_blockchain(block):
            self._log_failed_insertion(block, "already in local chain")
            return False

        if block.index == 0:
            self._log_failed_insertion(block, "new genesis block")
            return False
        
        if block.index > self.number_of_blocks():
            self._log_failed_insertion(block, "gap in local chain")
            return False

        if not self.has_correct_parent(block):
            self._log_failed_insertion(block, f"parent mismatch")
            return False

        winning_tickets = self.validate_block(block)
        if not winning_tickets:
            self._log_failed_insertion(block, "validation failed")
            return False
        else:
            self.update_successfull_sortition(block.index, winning_tickets)

        # in case there is already a block present at block.index
        if self.number_of_blocks() > block.index:
            if block.proof_hash >= self.get_proof_hash_of_block(block.index):
                self._log_failed_insertion(block, f"smaller proof_hash")
                return False
        
        # reject block if it was added in the same round as the parent
        parent_idx = block.index - 1

        if block.round <= self.get_round_of_block(parent_idx):
            self._log_failed_insertion(block, "same round as parent")
            return False
        
        self.logger.info(f"inserting {block}")
        self.blockChainDatabase.delete_blocks_since(block.index)
        self.blockChainDatabase.insert_block(block, time(), 0) # TODO CHECK ARRIVAL TIME
        return True

    #def merge_chain(self, foreign_blocks: list[Block]) -> bool:
    #    self.logger.info(f"starting merge process with fork: {foreign_blocks}")
    #    first_foreign_block = foreign_blocks[0]
    #
    #    id_and_idx = self.block_of_hash(first_foreign_block.parent_hash)
    #
    #    if id_and_idx is None:
    #        self.logger.error(f"foreign subchain has no common ancestor with local chain")
    #        return False
    #    
    #    id, idx = id_and_idx
    #
    #    self.logger.info(f"found common ancestor: {id}")  
    #    # temporarily remove local fork from the chain
    #    # TODO from this point this function seems very optimizable
    #    original_local_subchain = self.blocks_since_index(idx + 1)
    #   self.delete_blocks_since(idx+1)
    #
    #    # try inserting the head of the fork
    #    if not self.insert(foreign_blocks.pop(0)):
    #        self.logger.info(f"merge failed: foreign chain is worse than local chain")
    #        self.reintroduce_blocks(original_local_subchain)
    #        return False
    #    # if successful, try inserting all following blocks
    #    else:
    #        self.logger.info(f"merge success")
    #        for block in foreign_blocks:
    #            if not self.insert(block):
    #                break
    #
    #    return True

    def compose_block(self, block_info):
        # Receives a line from the database containing block info and returns a block with that info
        transaction_list = TransactionList()
        transaction_list.set_transactions(block_info[9])
        b = Block(parent_hash=bytes.fromhex(block_info[3]),
                owner_pubkey=bytes.fromhex(block_info[5]), 
                signed_node_hash=bytes.fromhex(block_info[6]), 
                round=block_info[2],
                index=block_info[0],
                transactionlist=transaction_list, 
                ticket_number=block_info[8])
        return b

    def validate_miniBlock(self, miniBlock: MiniBlock) -> Optional[int]:
        pubkey = None
        try:
            pubkey = Ed25519PublicKey.from_public_bytes(miniBlock.owner_pubkey)
        except ValueError:
            self._log_failed_verification(miniBlock, "bad pubkey")
            return None
        
        try:
            pubkey.verify(miniBlock.signed_node_hash, miniBlock.node_hash)
        except InvalidSignature:
            self._log_failed_verification(miniBlock, "bad node_hash signature")
            return None

        stake = self.lookup_node_stake(miniBlock.owner_pubkey)
        total_nodes = self.total_nodes
        miniTau = self.parameters.miniTau
        success_probability = miniTau / total_nodes
        winning_tickets = run_sortition(miniBlock.signed_node_hash, stake, success_probability)
        self.logger.debug(f"ran sortition for miniBlock {miniBlock.hash.hex()[0:7]} (p = {success_probability}); result = {winning_tickets}") 
        if winning_tickets == 0 or winning_tickets < miniBlock.ticket_number:
            self._log_failed_verification(miniBlock, "sortition failed")
            return None
        
        return winning_tickets

    def generate_miniBlock(self, id: bytes, privkey: Ed25519PrivateKey, public_key: bytes, use_mock_transactions: bool) -> Optional[Block]:
        self.blockChainDatabase.get_cursor()
        stake = self.lookup_node_stake(id)
        candidate: Optional[MiniBlock] = None
        for i in range(0, stake):
            if use_mock_transactions:
                tx = MockTransactionList()
            else:
                tx = TransactionList()
            
            miniBlock = MiniBlock(parent_hash=self.blockChainDatabase.get_last_block_hash(),
                                  transactionlist=tx,
                                  owner_pubkey=public_key,
                                  signed_node_hash=b"",
                                  round=self.current_round,
                                  index=self.blockChainDatabase.number_of_blocks(),
                                  ticket_number=i)

            miniBlock.sign_miniBlock(privkey, miniBlock)

            miniBlock.ticket_number = i

            if not self.validate_miniBlock(miniBlock):
                continue

            self.logger.debug(f"miniBlock candidate: {miniBlock}")
            
            if candidate is None or miniBlock.proof_hash < candidate.proof_hash:
                candidate = miniBlock

        if candidate is not None:
            self.logger.info(f"successfully generated a miniBlock: {candidate}")
        
        self.blockChainDatabase.close_cursor()
        return candidate

    # try to insert a block at the end of the chain
    def insert_miniBlock(self, miniBlock: MiniBlock) -> bool:
        self.blockChainDatabase.get_cursor()
        if self.blockChainDatabase.block_in_blockchain(miniBlock):
            self._log_failed_insertion(miniBlock, "already in local chain")
            self.blockChainDatabase.close_cursor()
            return False

        if miniBlock.index == 0:
            self._log_failed_insertion(miniBlock, "new genesis block")
            self.blockChainDatabase.close_cursor()
            return False
        
        if miniBlock.index > self.blockChainDatabase.number_of_blocks():
            self._log_failed_insertion(miniBlock, "gap in local chain")
            self.blockChainDatabase.close_cursor()
            return False

        if not self.blockChainDatabase.has_correct_parent(miniBlock):
            self._log_failed_insertion(miniBlock, f"parent mismatch")
            self.blockChainDatabase.close_cursor()
            return False

        winning_tickets = self.validate_miniBlock(miniBlock)
        if not winning_tickets:
            self._log_failed_insertion(miniBlock, "validation failed")
            self.blockChainDatabase.close_cursor()
            return False

        # in case there is already a block present at block.index
        if self.blockChainDatabase.number_of_blocks() > miniBlock.index:
            if miniBlock.proof_hash >= self.blockChainDatabase.get_proof_hash_of_block(miniBlock.index):
                self._log_failed_insertion(miniBlock, f"smaller proof_hash")
                self.blockChainDatabase.close_cursor()
                return False
        
        # reject block if it was added in the same round as the parent
        parent_idx = miniBlock.index - 1
        if miniBlock.round <= self.blockChainDatabase.get_round_of_block(parent_idx):
            self._log_failed_insertion(miniBlock, "same round as parent")
            self.blockChainDatabase.close_cursor()
            return False
        
        self.logger.info(f"inserting {miniBlock}")
        self.blockChainDatabase.delete_blocks_since(miniBlock.index)
        self.blockChainDatabase.insert_miniBlock(miniBlock, time(), 0, winning_tickets) # TODO CHECK ARRIVAL TIME
        self.blockChainDatabase.close_cursor()
        return True

