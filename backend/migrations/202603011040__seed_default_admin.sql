-- Seed default admin account for local/dev usage.
-- Default credentials:
--   username: admin
--   password: Admin@123456
-- IMPORTANT: change this password immediately in non-local environments.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'users'
    ) THEN
        RAISE EXCEPTION 'Table public.users does not exist. Please run base migrations first.';
    END IF;
END $$;

-- Avoid ON CONFLICT dependency so this script still works even if
-- the current database doesn't have a unique constraint on username.
UPDATE users
SET
    password_hash = crypt('Admin@123456', gen_salt('bf')),
    nickname = '系统管理员',
    email = 'admin@example.com',
    role = 'admin',
    status = 'active',
    updated_at = NOW()
WHERE username = 'admin';

INSERT INTO users (
    id,
    username,
    password_hash,
    nickname,
    email,
    phone,
    avatar_url,
    role,
    status,
    created_at,
    updated_at,
    last_login_at
)
SELECT
    gen_random_uuid(),
    'admin',
    crypt('Admin@123456', gen_salt('bf')),
    '系统管理员',
    'admin@example.com',
    NULL,
    NULL,
    'admin',
    'active',
    NOW(),
    NOW(),
    NULL
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE username = 'admin'
);
