create table if not exists kb_chunks(
    id        bigserial primary key,
    source    text not null,
    title     text not null,
    body      text not null,
    embedding vector(768)
);
