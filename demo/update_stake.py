import base64
import datetime
import hashlib
import mysql.connector
import numpy as np
import os
import signal

from time import sleep

HOST = "localhost"
USER = "CPoS"
PASSWORD = "CPoSPW"
DATABASE = "mempool"
INSERT_QUERY = "INSERT INTO stakes (stake_id, value, stake_hash, timestamp) VALUES (%s, %s, %s, %s)"
UPDATE_QUERY = "UPDATE stakes SET value = %s WHERE stake_id = %s"

PROGRAM_INTERRUPTED = False

def sighandler(*args):
    global PROGRAM_INTERRUPTED 
    PROGRAM_INTERRUPTED = True

class RandomStakeGenerator:
    def __init__(self) -> None:
        self.value: int = 1 #We should get it from Environment variable

    def generate_random_stake(self,node_id) -> tuple:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] 
        stake_hash = self.generate_hash(
            str(node_id) +
            str(self.value) +
            str(timestamp)
        )

        stake = (
            str(node_id),
            self.value,
            stake_hash,
            timestamp
        )

        return stake

    def generate_hash(self, data:str) -> str:
        sha = hashlib.sha256()
        sha.update(base64.b64encode(data.encode('ASCII')))
        hash_bytes = sha.digest()
        hash_string = base64.b64encode(hash_bytes).decode('ASCII')
        return hash_string

    def get_stake_id(self) -> str:
        return self.stake_id
    
    def get_value(self) -> int:
        return self.value

    def get_nodes(self):
        nodes = []
        with open("/proc/net/arp") as arp:
            next(arp) #skip header
            for line in arp:
                ip, hw_type, flags, mac, mask, dev = line.split()
                if mac == "00:00:00:00:00:00":
                    continue

                nodes.append({
                    "ip": ip,
                })
        print(nodes)
        return nodes

def update_stake() -> None:
    
    generator = RandomStakeGenerator()
    initiated = {}    
    while not PROGRAM_INTERRUPTED:
        
        nodes = generator.get_nodes()
        stakes = []
        total_stake = 0
        for node in nodes:
            stake = generator.generate_random_stake(node['ip'])
            stakes.append(stake)
            total_stake = total_stake + stake[1]
            aux = initiated.get(node['ip'],False)
            if aux is False:
                initiated[node['ip']] = False
         
        for node in nodes:
            try:
                connection = mysql.connector.connect(
                    host=node['ip'],
                    user=USER,
                    password=PASSWORD,
                    database=DATABASE
                )

                cursor = connection.cursor() 
                if initiated[node['ip']] is False:
                    cursor.executemany(INSERT_QUERY, stakes)
                    initiated.update({node['ip']: True})
                else: 
                    #cursor.execute(UPDATE_QUERY, (generator.get_value(), generator.get_stake_id()))
                    print("TODO: UPDATE - ", node['ip'])

                connection.commit()
                cursor.close()
                connection.close()

            except mysql.connector.Error as err:
                print(f"Error: {err}")
    
            finally:
                if 'connection' in locals():
                    connection.close()
        
        sleep(10)


if __name__ == "__main__":
    update_stake()
