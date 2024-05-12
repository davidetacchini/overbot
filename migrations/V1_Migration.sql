-- Revises: V0
-- Creation Date: 2023-11-12 16:55:22.416885 UTC
-- Reason: Initial migration

CREATE TABLE IF NOT EXISTS command (
    id SERIAL PRIMARY KEY,
    name TEXT,
    guild_id BIGINT,
    channel_id BIGINT,
    author_id BIGINT,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS member (
    id BIGINT PRIMARY KEY,
    embed_color INTEGER,
    premium BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS server (
    id BIGINT PRIMARY KEY,
    premium BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS newsboard (
    id BIGINT PRIMARY KEY,
    server_id BIGINT REFERENCES server(id) ON UPDATE CASCADE ON DELETE CASCADE,
    member_id BIGINT REFERENCES member(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profile (
    id SERIAL PRIMARY KEY,
    battletag VARCHAR(100),
    member_id BIGINT REFERENCES member(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rating (
    id SERIAL PRIMARY KEY,
    tank SMALLINT,
    damage SMALLINT,
    support SMALLINT,
    date DATE DEFAULT CURRENT_DATE,
    profile_id INTEGER REFERENCES profile(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trivia (
    id BIGINT PRIMARY KEY,
    won INTEGER DEFAULT 0,
    lost INTEGER DEFAULT 0,
    started INTEGER DEFAULT 0
);
