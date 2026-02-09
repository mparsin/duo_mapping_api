-- Migration: GitHub connection (single row) for long-lived PAT used by create-schema-pr.
-- Run this before using PUT /api/github-connection and POST /api/create-schema-pr.

CREATE TABLE IF NOT EXISTS github_connection (
    id SERIAL PRIMARY KEY,
    encrypted_token TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

COMMENT ON TABLE github_connection IS 'App-wide GitHub PAT (encrypted) for creating schema PRs; single row.';
