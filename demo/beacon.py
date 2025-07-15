import argparse
import signal
from time import sleep
import threading
import time

from cpos.p2p.discovery.beacon import Beacon
from demo.update_stake import update_stake

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="which port to bind the CPoS beacon to", type=int, required=True)
    args = parser.parse_args()

    beacon = Beacon(port=args.port, instant_reply=True)

    def sighandler(*args):
        print(f"Received SIGTERM! Halting node...")
        exit(1)

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    
    thread_update_stake = threading.Thread(target=update_stake)
    thread_update_stake.start()

    try:
        beacon.start()
    except KeyboardInterrupt:
        print("exiting...")

if __name__ == "__main__":
    main()

