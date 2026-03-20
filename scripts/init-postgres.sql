-- ============================================
-- ForgeLink PostgreSQL Initialization
-- Creates schemas and users for all services
-- ============================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS forgelink;
CREATE SCHEMA IF NOT EXISTS idp;
CREATE SCHEMA IF NOT EXISTS assets;
CREATE SCHEMA IF NOT EXISTS alerts;

-- Create users with schema access
DO $$
BEGIN
    -- Django user
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'forgelink') THEN
        CREATE USER forgelink WITH PASSWORD 'forgelink_dev_password';
    END IF;
    GRANT ALL PRIVILEGES ON SCHEMA forgelink TO forgelink;
    GRANT ALL PRIVILEGES ON SCHEMA public TO forgelink;

    -- IDP user
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'idp') THEN
        CREATE USER idp WITH PASSWORD 'idp_dev_password';
    END IF;
    GRANT ALL PRIVILEGES ON SCHEMA idp TO idp;

    -- Asset service user
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'assets') THEN
        CREATE USER assets WITH PASSWORD 'assets_dev_password';
    END IF;
    GRANT ALL PRIVILEGES ON SCHEMA assets TO assets;

    -- Alert service user
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'alerts') THEN
        CREATE USER alerts WITH PASSWORD 'alerts_dev_password';
    END IF;
    GRANT ALL PRIVILEGES ON SCHEMA alerts TO alerts;
END
$$;

-- Grant default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA forgelink GRANT ALL ON TABLES TO forgelink;
ALTER DEFAULT PRIVILEGES IN SCHEMA idp GRANT ALL ON TABLES TO idp;
ALTER DEFAULT PRIVILEGES IN SCHEMA assets GRANT ALL ON TABLES TO assets;
ALTER DEFAULT PRIVILEGES IN SCHEMA alerts GRANT ALL ON TABLES TO alerts;

-- Grant sequence privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA forgelink GRANT ALL ON SEQUENCES TO forgelink;
ALTER DEFAULT PRIVILEGES IN SCHEMA idp GRANT ALL ON SEQUENCES TO idp;
ALTER DEFAULT PRIVILEGES IN SCHEMA assets GRANT ALL ON SEQUENCES TO assets;
ALTER DEFAULT PRIVILEGES IN SCHEMA alerts GRANT ALL ON SEQUENCES TO alerts;
