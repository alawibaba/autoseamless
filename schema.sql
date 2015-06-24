drop table if exists users;
create table users (
        id serial primary key,
        username varchar(128) not null,
        password varchar(128) not null,
        favorites text not null,
        minute integer,
        disabled boolean not null);

drop table if exists messages;
create table messages (
        id serial primary key,
        user_id integer references users (id),
        message text not null,
        created_at timestamp not null);
