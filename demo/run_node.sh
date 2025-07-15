echo "starting container..."

# Database related commands
service mariadb start
echo "initializing mempool"
#mysql -e "CREATE USER 'CPoS'@localhost IDENTIFIED BY 'CPoSPW';"
mysql -e "CREATE USER 'CPoS'@'%' IDENTIFIED BY 'CPoSPW';"
#mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'CPoS'@'localhost';"
mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'CPoS'@'%';"
mysql -e "CREATE DATABASE mempool;"
mysql mempool < cpos/db/mempool.sql
mysql mempool < cpos/db/stakes.sql
echo "initializing local blockchain database"
mysql -e "CREATE DATABASE localBlockchain;"
mysql localBlockchain < cpos/db/localBlockchain.sql

# CPoS related commands
export GENESIS_TIMESTAMP=$(date -d '2024-06-01 00:00:00' +%s)
echo "GENESIS_TIMESTAMP: $GENESIS_TIMESTAMP"
poetry run python demo/main.py --beacon-ip $BEACON_IP --beacon-port $BEACON_PORT -p $PORT --genesis-timestamp $GENESIS_TIMESTAMP --total-rounds $NUMBER_OF_ROUNDS --period-size $PERIOD_SIZE &
pid=$!

# trap "send_data" INT TERM

# Makes sure to execute demo/send_data.py before exiting
send_data() {
    echo "sending data..."
    poetry run python demo/send_data.py
    kill -SIGTERM $pid
    exit
}

wait $pid
poetry run python demo/send_data.py
echo "exiting!"
