import os
from os.path import join
import pickle

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# rest of imports
import cpos


def main():
    cwd = os.getcwd() 
    log_dir = join(cwd, "demo/logs/")

    avg_throughput = 0
    total_message_count = 0
    total_message_bytes = 0
    total_blocks = 0
    total_confirmed_blocks = 0
    total_received_blocks = 0
    total_received_block_data = 0
    total_sent_blocks = 0
    total_sent_block_data = 0
    total = 0
    smallest_confirmation_delays = {}
    successfull_nodes = 0
    total_blocks_onChain = 0
    
    for filename in os.listdir(log_dir):
        if not filename.endswith(".data"):
            continue
        successfull_nodes += 1
        

        # plot local blockchain views and update statistics
        #print(f"processing {filename}")
        with open(join(log_dir, filename), "rb") as file:
            bc, last_confirmed_block_info, ini_confirmation_delays, message_count, message_bytes, blockchain_info, debug_info, network_info = pickle.load(file)
            confirmation_delays = select_valid_confirmation_delays(bc, ini_confirmation_delays)
            throughput, block_count, confirmed_blocks = plot_bc(bc, last_confirmed_block_info, filename, blockchain_info, confirmation_delays)
            avg_throughput += throughput
            total_message_count += message_count
            total_message_bytes += message_bytes
            total_blocks += block_count
            total_confirmed_blocks += confirmed_blocks
            received_blocks      = network_info[0]
            received_block_data  = network_info[1]
            sent_blocks          = network_info[2]
            sent_block_data      = network_info[3]
            blocks_onChain       = blockchain_info[3]
            total_blocks_onChain      += blockchain_info[3]
            total_received_blocks     += network_info[0]
            total_received_block_data += network_info[1] / 1024
            total_sent_blocks         += network_info[2] 
            total_sent_block_data     += network_info[3] / 1024
            total_blocks_onChain      += blockchain_info[3]
            total += 1
            # block_delay has a format: [block_id, block_index, confirmation_delay (in rounds)]
            for block_delay in confirmation_delays:
                if not block_delay[1] in smallest_confirmation_delays or smallest_confirmation_delays[block_delay[1]] > block_delay[2]:
                    smallest_confirmation_delays[block_delay[1]] = block_delay[2]
        print(f"************** RAW DATA *******************************")
        print(f"received_blocks       = {received_blocks}")
        print(f"received_block_data   = {received_block_data}")
        print(f"sent_blocks           = {sent_blocks}")
        print(f"sent_block_data       = {sent_block_data}")
        print(f"blocks_onChain        = {blocks_onChain}")
        print(f"*******************************************************")
        
        print(f"Produced blocks: {debug_info[0]},   Received Blocks: {debug_info[1]},   Discarded Blocks: {debug_info[2]}, Inserted Blocks: {debug_info[3]},  Forks Detected: {debug_info[4]},    Resyncs: {debug_info[5]},    Successfull Resyncs: {debug_info[6]}, Known Peers: {len(debug_info[7])}")
        print(f"Overturns: {len(ini_confirmation_delays) - len(confirmation_delays)}")
        print(f"-------------------------------------\n")

    print(f"************** SUMMARY DATA *******************************")
    print(f"total_received_blocks       = {total_received_blocks}")
    print(f"total_received_block_data   = {total_received_block_data:.2f} KBytes")
    print(f"total_sent_blocks           = {total_sent_blocks}")
    print(f"total_sent_block_data       = {total_sent_block_data:.2f} KBytes")
    
    avg_received_blocks       = total_received_blocks / total
    avg_received_block_data   = total_received_block_data / total
    avg_sent_blocks           = total_sent_blocks / total
    avg_sent_block_data       = total_sent_block_data / total
    avg_blocks_onChain        = total_blocks_onChain / total
    
    print(f"avg_received_blocks       = {avg_received_blocks:.2f}")
    print(f"avg_received_block_data   = {avg_received_block_data:.2f} KBytes")
    print(f"avg_sent_blocks           = {avg_sent_blocks:.2f}")
    print(f"avg_sent_block_data       = {avg_sent_block_data:.2f} KBytes")
    
    print(f"avg_blocks_onChain       = {avg_blocks_onChain:.2f} ")
    
    print(f"***********************************************************")
        
    avg_throughput /= total
    try:
        average_confirmation_delay = round(sum(smallest_confirmation_delays) / len(smallest_confirmation_delays), 3)
    except ZeroDivisionError:
        average_confirmation_delay = '0 CONFIRMED'
    

    print(f"statistics: average throughput = {avg_throughput} blocks/min; average confirmation delay = {average_confirmation_delay}")
    print(f"total messages: {total_message_count} ({total_message_bytes / (1024 * 1024)} MiB)")
    print(f"total blocks = {total_blocks}; total confirmed blocks = {total_confirmed_blocks}")
    print(f"Nodes = {successfull_nodes}")

    return successfull_nodes, round(avg_throughput, 3), average_confirmation_delay, total_message_count, total_message_bytes, total_blocks, total_confirmed_blocks

def plot_bc(bc, last_confirmed_block_info, filename: str, blockchain_info: list, confirmation_delays):
    block_count = 0
    last_confirmed_block_index, last_confirmed_block_id, last_confirmed_block_round = last_confirmed_block_info
    round_time, last_confirmation_delay, current_round, chain_size = blockchain_info
    confirmed_blocks = 0
    i = -1
    for block in bc:
        if i < len(confirmation_delays) and i != -1:
            print(block, confirmation_delays[i][0].hex()[0:8], confirmation_delays[i][1], confirmation_delays[i][2])
        else:
            print(block)
        i += 1
        block_count += 1
        if block.hash == last_confirmed_block_id:
            confirmed_blocks = block_count
            print("=== [UNCONFIRMED BLOCKS] ===")

    # confirmed blocks per minute
    throughput = last_confirmed_block_index * 60 / (round_time * 30)

    return throughput, len(bc), confirmed_blocks

def select_valid_confirmation_delays(bc, confirmation_delays):
    # Sometimes, blocks are confirmed but do not appear in the final blockchain
    # TODO: Optimize this. Its clealy not the optimal algorithm for a big blockchain.
    block_hashes = []
    for block in bc:
        block_hashes.append(block.hash)
    valid_confirmation_delays = []
    for delay in confirmation_delays:
        if delay[0] in block_hashes:
            valid_confirmation_delays.append(delay)
            block_hashes.remove(delay[0])
    return valid_confirmation_delays

if __name__ == "__main__":
    main()
  
