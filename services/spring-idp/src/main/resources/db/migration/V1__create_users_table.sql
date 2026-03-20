-- ForgeLink IDP Schema Migration V1
-- Create users table and related structures

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS idp;

-- Users table
CREATE TABLE idp.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    plant_id VARCHAR(64),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip VARCHAR(45),
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- User roles table (many-to-many via element collection)
CREATE TABLE idp.user_roles (
    user_id UUID NOT NULL REFERENCES idp.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, role)
);

-- Indexes
CREATE INDEX idx_users_email ON idp.users(email);
CREATE INDEX idx_users_plant_id ON idp.users(plant_id);
CREATE INDEX idx_users_enabled ON idp.users(enabled);
CREATE INDEX idx_user_roles_user_id ON idp.user_roles(user_id);

-- Updated at trigger
CREATE OR REPLACE FUNCTION idp.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON idp.users
    FOR EACH ROW
    EXECUTE FUNCTION idp.update_updated_at();
