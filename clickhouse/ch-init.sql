USE analytic;

DROP TABLE IF EXISTS reports;
CREATE TABLE IF NOT EXISTS reports (
    id UInt64,
    username String,
    age UInt16,
    prosthesis_id UInt64,
    sensor_name String,
    sensor_type String,
    installed_at DateTime,
    metric_timestamp DateTime,
    force_newtons UInt32,
    force_direction Decimal,
    acceleration_x UInt32,
    acceleration_y UInt32,
    acceleration_z UInt32,
    temperature_celsius UInt32,
    battery_level_percent UInt32
)
ENGINE = MergeTree()
ORDER BY id
PRIMARY KEY id;


INSERT INTO reports (username, age, prosthesis_id, sensor_name, sensor_type, installed_at,
                     metric_timestamp, force_newtons, force_direction,
                     acceleration_x, acceleration_y, acceleration_z,
                     temperature_celsius, battery_level_percent)
VALUES (
   'prothetic1', 24, 1, 'Sensor A', 'below_elbow',
   '2025-10-01 15:30:00', '2025-10-01 15:30:00',2554, 109.0,
   87, 95, 78, 90, 80
);

INSERT INTO reports (username, age, prosthesis_id, sensor_name, sensor_type, installed_at,
                     metric_timestamp, force_newtons, force_direction,
                     acceleration_x, acceleration_y, acceleration_z,
                     temperature_celsius, battery_level_percent)
VALUES (
   'prothetic1', 24, 2, 'Sensor B', 'below_elbow',
   '2025-10-02 15:30:00', '2025-10-02 15:30:00',2554, 109.0,
   87, 95, 78, 90, 90
);

INSERT INTO reports (username, age, prosthesis_id, sensor_name, sensor_type, installed_at,
                     metric_timestamp, force_newtons, force_direction,
                     acceleration_x, acceleration_y, acceleration_z,
                     temperature_celsius, battery_level_percent)
VALUES (
   'prothetic2', 35, 4, 'Sensor C', 'below_elbow',
   '2025-10-02 15:30:00', '2025-10-02 15:30:00',2554, 109.0,
   87, 95, 78, 90, 90
);
