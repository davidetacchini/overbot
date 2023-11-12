-- Revises: V0
-- Creation Date: 2023-11-12 16:55:22.416885 UTC
-- Reason: Initial migration

CREATE TABLE IF NOT EXISTS command (
    id SERIAL PRIMARY KEY,
    name text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    author_id bigint NOT NULL,
    created_at timestamp NOT NULL
);

CREATE TABLE IF NOT EXISTS member (
    id bigint PRIMARY KEY NOT NULL,
    embed_color integer,
    premium boolean DEFAULT false NOT NULL
);

CREATE TABLE IF NOT EXISTS newsboard (
    id bigint PRIMARY KEY NOT NULL,
    server_id bigint REFERENCES server(id) ON UPDATE CASCADE ON DELETE CASCADE NOT NULL,
    member_id bigint REFERENCES member(id) ON UPDATE CASCADE ON DELETE CASCADE NOT NULL
);

CREATE TABLE IF NOT EXISTS profile (
    id SERIAL PRIMARY KEY,
    battletag varchar(100) NOT NULL,
    member_id bigint REFERENCES member(id) ON UPDATE CASCADE ON DELETE CASCADE NOT NULL
);

CREATE TABLE IF NOT EXISTS rating (
    id SERIAL PRIMARY KEY,
    tank smallint,
    damage smallint,
    support smallint,
    date date DEFAULT CURRENT_DATE,
    profile_id integer REFERENCES profile(id) ON UPDATE CASCADE ON DELETE CASCADE NOT NULL
);

CREATE TABLE IF NOT EXISTS server (
    id bigint PRIMARY KEY NOT NULL,
    premium boolean DEFAULT false NOT NULL
);

CREATE TABLE IF NOT EXISTS trivia (
    id bigint PRIMARY KEY NOT NULL,
    won integer DEFAULT 0 NOT NULL,
    lost integer DEFAULT 0 NOT NULL,
    started integer DEFAULT 0 NOT NULL
);
