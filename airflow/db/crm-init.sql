create table if not exists customers
(
    username   text primary key,
    email      text      not null,
    first_name text,
    last_name  text,
    created_at timestamp not null default now(),
    updated_at timestamp not null default now()
);

insert into customers (username, email, first_name, last_name)
values ('alice', 'alice@example.com', 'Alice', 'Green'),
       ('bob', 'bob@example.com', 'Bob', 'Brown')
on conflict do nothing;