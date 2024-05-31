-- Revises: V2
-- Creation Date: 2024-05-11 12:40:34.301529+00:00 UTC
-- Reason: Saving player ratings and stats

-- Renaming the old rating table; not using it anymore
ALTER TABLE rating RENAME TO old_ratings;

CREATE TABLE IF NOT EXISTS stats (
    id SERIAL PRIMARY KEY,
    author_id BIGINT,
    guild_id BIGINT,
    battletag TEXT,
    data JSONB DEFAULT ('{}'::jsonb) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
