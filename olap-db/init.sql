CREATE TABLE IF NOT EXISTS emg_sensor_data (
    user_id UInt32,
    prosthesis_type String,
    muscle_group String,
    signal_frequency UInt32,
    signal_duration UInt32,
    signal_amplitude Decimal(5,2),
    signal_time DateTime
) ENGINE = MergeTree()
ORDER BY (user_id, prosthesis_type, signal_time);

INSERT INTO emg_sensor_data
SELECT *
FROM file('olap.csv', 'CSV');

CREATE TABLE IF NOT EXISTS customers (
    id UInt32,
    name String,
    email String,
    age UInt8,
    gender String,
    country String,
    address String,
    phone String
) ENGINE = MergeTree
ORDER BY id;


CREATE TABLE IF NOT EXISTS customer_emg_analytics
(
    customer_id UInt32,
    name String,
    email String,
    country LowCardinality(String),
    prosthesis_type LowCardinality(String),
    muscle_group LowCardinality(String),
    total_signals UInt64,
    avg_frequency Float64,
    avg_duration Float64,
    avg_amplitude Float64,
    last_signal_time DateTime
)
ENGINE = MergeTree
ORDER BY (customer_id, prosthesis_type, muscle_group);