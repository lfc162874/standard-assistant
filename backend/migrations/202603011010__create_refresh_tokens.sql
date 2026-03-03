CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    ip VARCHAR(64) NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS auth_refresh_tokens_token_hash_key ON auth_refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS auth_refresh_tokens_user_id_expires_at_idx ON auth_refresh_tokens (user_id, expires_at);
