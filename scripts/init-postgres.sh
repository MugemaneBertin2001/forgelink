#!/bin/bash
# ============================================
# ForgeLink PostgreSQL Initialization
# ============================================
# Runs once, via docker-entrypoint-initdb.d, on first container start.
# Creates per-service databases and users. Schemas are then created by
# Django migrations (forgelink) and Flyway (idp) at app boot.
#
# Stock postgres:16 does NOT honor POSTGRES_MULTIPLE_DATABASES; that env var
# is a convention implemented by custom init scripts like this one.
# ============================================
set -euo pipefail

psql_as_root() {
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER:-postgres}" --dbname postgres "$@"
}

create_user_if_missing() {
  local username="$1"
  local password="$2"
  psql_as_root <<-EOSQL
    DO \$\$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${username}') THEN
        CREATE USER ${username} WITH PASSWORD '${password}';
      END IF;
    END
    \$\$;
EOSQL
}

create_database_if_missing() {
  local dbname="$1"
  local owner="$2"
  # CREATE DATABASE cannot run inside a transaction block, so we check first
  # and run it as a top-level statement.
  if ! psql_as_root -tAc "SELECT 1 FROM pg_database WHERE datname = '${dbname}'" | grep -q 1; then
    psql_as_root -c "CREATE DATABASE ${dbname} OWNER ${owner}"
  fi
}

create_schema_and_grants() {
  local dbname="$1"
  local schema="$2"
  local user="$3"
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER:-postgres}" --dbname "${dbname}" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS ${schema};
    GRANT ALL PRIVILEGES ON SCHEMA ${schema} TO ${user};
    GRANT ALL PRIVILEGES ON SCHEMA public TO ${user};
    ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT ALL ON TABLES TO ${user};
    ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT ALL ON SEQUENCES TO ${user};
EOSQL
}

echo "[init-postgres] Creating users..."
create_user_if_missing forgelink "${FORGELINK_DB_PASSWORD:-forgelink_dev_password}"
create_user_if_missing idp       "${IDP_DB_PASSWORD:-idp_dev_password}"

echo "[init-postgres] Creating databases..."
create_database_if_missing forgelink forgelink
create_database_if_missing idp       idp

echo "[init-postgres] Creating schemas and grants..."
create_schema_and_grants forgelink forgelink forgelink
create_schema_and_grants idp       idp       idp

echo "[init-postgres] Done."
