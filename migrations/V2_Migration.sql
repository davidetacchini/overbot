-- Revises: V1
-- Creation Date: 2023-11-12 16:57:06.157424 UTC
-- Reason: Store latest overwatch news ID

CREATE TABLE IF NOT EXISTS news (
    id integer DEFAULT 1 PRIMARY KEY NOT NULL,
    latest_id integer DEFAULT 0 NOT NULL
);
