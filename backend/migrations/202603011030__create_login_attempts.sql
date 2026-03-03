CREATE TABLE IF NOT EXISTS login_attempts (
    id UUID PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    ip VARCHAR(64) NOT NULL,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS login_attempts_user_ip_created_idx ON login_attempts (username, ip, created_at DESC);
