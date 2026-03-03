CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    password_hash TEXT NOT NULL,
    nickname VARCHAR(64),
    email VARCHAR(255),
    phone VARCHAR(32),
    avatar_url VARCHAR(500),
    role VARCHAR(16) NOT NULL DEFAULT 'user',
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    CONSTRAINT users_role_check CHECK (role IN ('user', 'admin')),
    CONSTRAINT users_status_check CHECK (status IN ('active', 'disabled'))
);

CREATE UNIQUE INDEX IF NOT EXISTS users_username_key ON users (username);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS users_phone_key ON users (phone) WHERE phone IS NOT NULL;
