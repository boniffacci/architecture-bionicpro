CREATE DATABASE sample;

GRANT ALL PRIVILEGES ON DATABASE sample TO airflow;

\connect sample;

CREATE TABLE crm (
  id SERIAL PRIMARY KEY NOT NULL,
  email VARCHAR NOT NULL,
  name VARCHAR,
  country VARCHAR,
  prosthesis_id VARCHAR,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE telemetry (
  id SERIAL PRIMARY KEY NOT NULL,
  user_id INT NOT NULL,
  prosthesis_id VARCHAR,
  ts TIMESTAMP NOT NULL,
  metric_type VARCHAR,
  metric_value FLOAT
);

INSERT INTO crm(email, name, country, prosthesis_id)
VALUES
  (
    'prothetic1@example.com',
    'prothetic1',
    'RU',
    'P001'
  ),
  (
    'prothetic2@example.com',
    'prothetic2',
    'DE',
    'P002'
  ),
  (
    'prothetic3@example.com',
    'prothetic3',
    'CN',
    'P003'
  );

INSERT INTO telemetry(user_id, prosthesis_id, ts, metric_type, metric_value)
VALUES
  (1, 'P001', '2025-10-18 10:15:00', 'type_1', 12.0),
  (1, 'P001', '2025-10-18 11:45:00', 'type_1', 16.0),
  (1, 'P001', '2025-10-18 15:00:00', 'type_1', 12.0),
  (1, 'P001', '2025-10-20 09:20:00', 'type_1', 18.0),
  (1, 'P001', '2025-10-20 13:05:00', 'type_2', 19.0),
  (2, 'P002', '2025-10-21 08:10:00', 'type_1', 9.0),
  (2, 'P002', '2025-10-21 19:30:00', 'type_1', 12.0),
  (2, 'P002', '2025-10-22 10:00:00', 'type_1', 9.0),
  (3, 'P003', '2025-10-19 14:10:00', 'type_2', 28.0),
  (3, 'P003', '2025-10-19 18:40:00', 'type_2', 31.0);
