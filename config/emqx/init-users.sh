#!/bin/bash
# ForgeLink EMQX User Initialization
# Run this after EMQX starts to create authentication users

set -e

EMQX_HOST="${EMQX_HOST:-localhost}"
EMQX_API_PORT="${EMQX_API_PORT:-18083}"
EMQX_ADMIN_USER="${EMQX_DASHBOARD__DEFAULT_USERNAME:-admin}"
EMQX_ADMIN_PASS="${EMQX_DASHBOARD__DEFAULT_PASSWORD:-public}"

API_URL="http://${EMQX_HOST}:${EMQX_API_PORT}/api/v5"

echo "Waiting for EMQX to be ready..."
until curl -s -o /dev/null -w "%{http_code}" "${API_URL}/status" | grep -q "200"; do
    sleep 2
done
echo "EMQX is ready!"

# Function to create user
create_user() {
    local username=$1
    local password=$2

    echo "Creating user: ${username}"
    curl -s -X POST "${API_URL}/authentication/password_based:built_in_database/users" \
        -u "${EMQX_ADMIN_USER}:${EMQX_ADMIN_PASS}" \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"${username}\",
            \"password\": \"${password}\",
            \"is_superuser\": false
        }" || true
}

# Create service users
echo "Creating MQTT users..."

# Bridge user (for MQTT-Kafka bridge)
create_user "bridge" "${EMQX_MQTT_PASSWORD:-bridge_dev_password}"

# Device users (per area)
create_user "device-melt-shop" "melt_shop_device_password"
create_user "device-continuous-casting" "casting_device_password"
create_user "device-rolling-mill" "rolling_mill_device_password"
create_user "device-finishing" "finishing_device_password"

# Operator user (read-only)
create_user "operator" "operator_password"

# Admin user
create_user "admin" "${EMQX_ADMIN_PASSWORD:-admin_mqtt_password}"

# Simulator user (for testing)
create_user "simulator" "simulator_password"

echo "EMQX users created successfully!"
