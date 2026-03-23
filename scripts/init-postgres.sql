-- ============================================
-- ForgeLink PostgreSQL Initialization
-- Creates schemas and users for services
-- ============================================
-- Django API: owns all business data (assets, alerts, telemetry, audit, simulator)
-- Spring IDP: owns authentication data only
-- ============================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS forgelink;
CREATE SCHEMA IF NOT EXISTS idp;

-- Create users with schema access
DO $$
BEGIN
    -- Django user (owns all business data)
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'forgelink') THEN
        CREATE USER forgelink WITH PASSWORD 'forgelink_dev_password';
    END IF;
    GRANT ALL PRIVILEGES ON SCHEMA forgelink TO forgelink;
    GRANT ALL PRIVILEGES ON SCHEMA public TO forgelink;

    -- IDP user (authentication only)
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'idp') THEN
        CREATE USER idp WITH PASSWORD 'idp_dev_password';
    END IF;
    GRANT ALL PRIVILEGES ON SCHEMA idp TO idp;
END
$$;

-- Grant default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA forgelink GRANT ALL ON TABLES TO forgelink;
ALTER DEFAULT PRIVILEGES IN SCHEMA idp GRANT ALL ON TABLES TO idp;

-- Grant sequence privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA forgelink GRANT ALL ON SEQUENCES TO forgelink;
ALTER DEFAULT PRIVILEGES IN SCHEMA idp GRANT ALL ON SEQUENCES TO idp;
