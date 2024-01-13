-- Revises: V0
-- Creation Date: 2023-11-12 16:55:22.416885 UTC
-- Reason: Initial migration

CREATE TABLE IF NOT EXISTS command (
    id SERIAL PRIMARY KEY,
    name text,
    guild_id bigint,
    channel_id bigint,
    author_id bigint,
    created_at timestamp
);

CREATE TABLE IF NOT EXISTS member (
    id bigint PRIMARY KEY,
    embed_color integer,
    premium boolean DEFAULT false
);

CREATE TABLE IF NOT EXISTS server (
    id bigint PRIMARY KEY,
    premium boolean DEFAULT false
);

CREATE TABLE IF NOT EXISTS newsboard (
    id bigint PRIMARY KEY,
    server_id bigint REFERENCES server(id) ON UPDATE CASCADE ON DELETE CASCADE,
    member_id bigint REFERENCES member(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile (
    id SERIAL PRIMARY KEY,
    battletag varchar(100),
    member_id bigint REFERENCES member(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rating (
    id SERIAL PRIMARY KEY,
    tank smallint,
    damage smallint,
    support smallint,
    date date DEFAULT CURRENT_DATE,
    profile_id integer REFERENCES profile(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trivia (
    id bigint PRIMARY KEY,
    won integer DEFAULT 0,
    lost integer DEFAULT 0,
    started integer DEFAULT 0
);
