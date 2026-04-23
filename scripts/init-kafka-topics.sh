#!/bin/bash
# ForgeLink Kafka Topic Initialization
# Run this after Kafka starts to create required topics

set -e

KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:9092}"
PARTITIONS="${PARTITIONS:-3}"
REPLICATION="${REPLICATION:-1}"

echo "Waiting for Kafka to be ready..."
until kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" --list &>/dev/null; do
    sleep 2
done
echo "Kafka is ready!"

# Function to create topic if not exists
create_topic() {
    local topic=$1
    local partitions=${2:-$PARTITIONS}
    local retention_ms=${3:-604800000}  # Default 7 days
    local cleanup_policy=${4:-delete}

    if kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" --list | grep -q "^${topic}$"; then
        echo "Topic '$topic' already exists"
    else
        echo "Creating topic: $topic (partitions=$partitions, retention=${retention_ms}ms)"
        kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" \
            --create \
            --topic "$topic" \
            --partitions "$partitions" \
            --replication-factor "$REPLICATION" \
            --config retention.ms="$retention_ms" \
            --config cleanup.policy="$cleanup_policy"
    fi
}

echo "============================================"
echo "Creating ForgeLink Kafka Topics"
echo "============================================"

# ============================================
# Telemetry Topics (per production area)
# High volume, short retention
# ============================================
echo ""
echo "Creating telemetry topics..."

# Melt Shop telemetry (EAF, LRF)
create_topic "telemetry.melt-shop" 3 604800000  # 7 days

# Continuous Casting telemetry
create_topic "telemetry.continuous-casting" 3 604800000

# Rolling Mill telemetry
create_topic "telemetry.rolling-mill" 3 604800000

# Finishing area telemetry
create_topic "telemetry.finishing" 3 604800000

# ============================================
# Event Topics
# Medium volume, longer retention
# ============================================
echo ""
echo "Creating event topics..."

# All device events (alarms, threshold breaches)
create_topic "events.all" 3 7776000000  # 90 days

# ============================================
# Status Topics
# Low volume, moderate retention
# ============================================
echo ""
echo "Creating status topics..."

# Device status (online/offline, health)
create_topic "status.all" 3 2592000000  # 30 days

# ============================================
# Command Topics
# Low volume, short retention
# ============================================
echo ""
echo "Creating command topics..."

# Commands sent to devices
create_topic "commands.all" 3 604800000  # 7 days

# ============================================
# Asset Topics
# Low volume, long retention
# ============================================
echo ""
echo "Creating asset topics..."

# Asset mutations (create, update, delete)
create_topic "assets.changes" 3 31536000000  # 1 year

# ============================================
# Dead Letter Queue
# Unparseable/failed messages
# ============================================
echo ""
echo "Creating DLQ topics..."

# Dead letter queue for unparseable messages
create_topic "dlq.unparseable" 1 2592000000  # 30 days

# Failed processing attempts
create_topic "dlq.processing-failed" 1 2592000000  # 30 days

# ============================================
# Analytics Topics
# Aggregated data for dashboards
# ============================================
echo ""
echo "Creating analytics topics..."

# Pre-aggregated metrics (1-minute intervals)
create_topic "analytics.metrics-1m" 3 7776000000  # 90 days

# Hourly aggregates
create_topic "analytics.metrics-1h" 3 31536000000  # 1 year

# ============================================
# Alert Topics
# Processed alerts for notifications
# ============================================
echo ""
echo "Creating alert topics..."

# Alerts for notification dispatch
create_topic "alerts.notifications" 3 2592000000  # 30 days

# ============================================
# Compacted Topics (latest state only)
# ============================================
echo ""
echo "Creating compacted topics..."

# Latest device state (compacted)
kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" --list | grep -q "^device-state$" || \
kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" \
    --create \
    --topic "device-state" \
    --partitions 3 \
    --replication-factor "$REPLICATION" \
    --config cleanup.policy=compact \
    --config min.cleanable.dirty.ratio=0.1 \
    --config segment.ms=100

# Latest asset state (compacted)
kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" --list | grep -q "^asset-state$" || \
kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" \
    --create \
    --topic "asset-state" \
    --partitions 3 \
    --replication-factor "$REPLICATION" \
    --config cleanup.policy=compact \
    --config min.cleanable.dirty.ratio=0.1

echo ""
echo "============================================"
echo "Kafka topic initialization complete!"
echo "============================================"

# List all topics
echo ""
echo "Current topics:"
kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" --list
