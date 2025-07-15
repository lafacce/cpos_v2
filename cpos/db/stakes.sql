CREATE TABLE IF NOT EXISTS stakes (
        stake_id VARCHAR(256) NOT NULL,
        value integer,
        stake_hash text NOT NULL,
        timestamp text NOT NULL,
        PRIMARY KEY (stake_id))
