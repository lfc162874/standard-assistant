CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(128) NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS chat_sessions_session_id_key ON chat_sessions (session_id);
CREATE INDEX IF NOT EXISTS chat_sessions_user_id_updated_at_idx ON chat_sessions (user_id, updated_at DESC);
