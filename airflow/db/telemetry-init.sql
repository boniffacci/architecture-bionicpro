create table if not exists events
(
    event_id bigserial primary key,
    username text not null,
    event_type text not null, --- 'accuracy' | 'movement' | 'intensity'
    event_value numeric, --- 'intensity' aggregation
    event_time timestamp not null default now()
);

create index if not exists idx_events_user_time on events (username, event_time);

insert into events (username, event_type, event_value, event_time)
values ('alice', 'accuracy', null, now() - interval '1 day'),
       ('alice', 'movement', null, now() - interval '3 hours'),
       ('alice', 'intensity', 0.7, now() - interval '2 hours'),
       ('bob', 'movement', null, now() - interval '4 hours'),
       ('bob', 'intensity', 1.2, now() - interval '1 hour');