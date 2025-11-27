USE bionicpro;

CREATE TABLE IF NOT EXISTS report (
    id UUID default generateUUIDv4(),
    user_id UInt32,
    user_name String,
    user_email String,
    user_age UInt32,
    user_gender String,
    user_country String,
    user_address String,
    user_phone String,
    prosthesis_type String,
    muscle_group String,
    signal_frequency UInt32,
    signal_duration UInt32,
    signal_amplitude Decimal(5,2),
    signal_time DateTime,
    report_date DateTime
) ENGINE = MergeTree()
ORDER BY (user_id, prosthesis_type, signal_time);

CREATE TABLE IF NOT EXISTS report_date (
    id UInt32,
    report_date DateTime
) ENGINE = ReplacingMergeTree
PRIMARY KEY (id)
ORDER BY (id);