create extension if not exists vector;

create table if not exists plans(
    code      text primary key,
    name      text not null,
    vcpu      int not null,
    ram_gb    int not null,
    disk_gb   int not null,
    price_kop bigint not null
);

create table if not exists services(
    code      text primary key,
    name      text not null,
    price_kop bigint not null
);

create table if not exists accounts(
    id    text primary key,
    name  text not null,
    email text not null,
    phone text not null
);

create table if not exists users(
    login      text primary key,
    sub        text unique not null,
    name       text not null,
    role       text not null,
    scopes     text[] not null,
    account_id text references accounts(id)
);

create table if not exists servers(
    id         text primary key,
    account_id text unique not null references accounts(id),
    hostname   text not null,
    plan_code  text not null references plans(code),
    disk_gb    int not null
);

create table if not exists account_services(
    account_id   text not null references accounts(id),
    service_code text not null references services(code),
    enabled      boolean not null,
    primary key (account_id, service_code)
);

create table if not exists charges(
    id         bigserial primary key,
    account_id text not null references accounts(id),
    period     text not null,
    label      text not null,
    amount_kop bigint not null
);

create table if not exists plan_changes(
    id              bigserial primary key,
    account_id      text not null references accounts(id),
    before          text not null,
    after           text not null,
    idempotency_key text not null,
    created_at      timestamptz not null default now()
);

create table if not exists billing_operations(
    idempotency_key text primary key,
    account_id      text not null,
    result          jsonb not null,
    created_at      timestamptz not null default now()
);

create table if not exists tickets(
    id         text primary key,
    account_id text not null,
    subject    text not null,
    note       text not null,
    status     text not null default 'open',
    created_at timestamptz not null default now()
);
