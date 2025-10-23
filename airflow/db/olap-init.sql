create schema if not exists stg;

create table if not exists stg.customers_like_src
(
    username   text primary key,
    email      text      not null,
    first_name text,
    last_name  text,
    updated_at timestamp not null
);

create table if not exists stg.events_like_src
(
    username    text      not null,
    event_time  timestamp not null,
    event_type  text      not null,
    event_value numeric
);

create schema if not exists mart;

create table if not exists mart.customer_telemetry_daily
(
    username   text    not null,
    date       date    not null,
    accuracy   bigint  not null default 0,
    movements  bigint  not null default 0,
    intensity  numeric not null default 0,
    last_event timestamp,
    primary key (username, date)
);

create index if not exists ix_mart_username on mart.customer_telemetry_daily (username);