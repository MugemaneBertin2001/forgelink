"""
TDengine client and connection management for ForgeLink telemetry.

This module provides:
- Connection pooling and management
- Schema initialization
- Batch insert operations
- Query utilities with aggregation support
- Continuous aggregation management
"""

import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# Connection pool (thread-local)
_local = threading.local()


class TDEngineClient:
    """
    TDengine client with connection management and query utilities.

    Uses taosrest for HTTP-based connections (compatible with Docker/K8s).
    """

    def __init__(self):
        self._conn = None
        self._database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    def connect(self):
        """Establish connection to TDengine."""
        import taosrest

        try:
            host = settings.TDENGINE.get("HOST", "localhost")
            port = settings.TDENGINE.get("PORT", 6041)
            user = settings.TDENGINE.get("USER", "root")
            password = settings.TDENGINE.get("PASSWORD", "taosdata")

            self._conn = taosrest.connect(
                url=f"http://{host}:{port}",
                user=user,
                password=password,
                database=self._database,
            )
            logger.debug(f"Connected to TDengine at {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to TDengine: {e}")
            self._conn = None
            return False

    def disconnect(self):
        """Close connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    @property
    def connection(self):
        """Get or create connection."""
        if not self._conn:
            self.connect()
        return self._conn

    def execute(self, sql: str) -> Any:
        """Execute SQL statement."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql)
            return cursor
        except Exception as e:
            logger.error(f"TDengine execute error: {e}\nSQL: {sql[:500]}")
            raise

    def fetchall(self, sql: str) -> List[Tuple]:
        """Execute SQL and fetch all results."""
        cursor = self.execute(sql)
        try:
            return cursor.fetchall()
        finally:
            cursor.close()

    def fetchone(self, sql: str) -> Optional[Tuple]:
        """Execute SQL and fetch one result."""
        cursor = self.execute(sql)
        try:
            return cursor.fetchone()
        finally:
            cursor.close()


def get_client() -> TDEngineClient:
    """Get thread-local TDengine client."""
    if not hasattr(_local, "client") or _local.client is None:
        _local.client = TDEngineClient()
        _local.client.connect()
    return _local.client


@contextmanager
def tdengine_cursor():
    """Context manager for TDengine cursor."""
    client = get_client()
    cursor = client.connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def init_tdengine_schema() -> bool:
    """
    Initialize TDengine database and supertables.

    Creates:
    - Database with retention policies
    - telemetry supertable (raw sensor data)
    - device_status supertable (device health)
    - events supertable (alarms, alerts)
    - Aggregate supertables (1m, 1h, 1d)
    """
    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        # Create database
        client.execute(f"""
            CREATE DATABASE IF NOT EXISTS {database}
            KEEP 365
            DURATION 10
            BUFFER 256
            WAL_LEVEL 1
            CACHEMODEL 'last_row'
        """)

        client.execute(f"USE {database}")

        # Telemetry supertable (raw sensor readings)
        client.execute("""
            CREATE STABLE IF NOT EXISTS telemetry (
                ts TIMESTAMP,
                value DOUBLE,
                quality NCHAR(10),
                sequence BIGINT
            ) TAGS (
                device_id NCHAR(64),
                plant NCHAR(32),
                area NCHAR(32),
                line NCHAR(32),
                cell NCHAR(32),
                unit NCHAR(20),
                device_type NCHAR(32)
            )
        """)

        # Device status supertable
        client.execute("""
            CREATE STABLE IF NOT EXISTS device_status (
                ts TIMESTAMP,
                online BOOL,
                last_seen TIMESTAMP,
                error_code NCHAR(32),
                error_message NCHAR(256)
            ) TAGS (
                device_id NCHAR(64),
                plant NCHAR(32),
                area NCHAR(32)
            )
        """)

        # Events supertable (alarms, threshold breaches)
        client.execute("""
            CREATE STABLE IF NOT EXISTS events (
                ts TIMESTAMP,
                event_type NCHAR(32),
                severity NCHAR(16),
                message NCHAR(512),
                value DOUBLE,
                threshold DOUBLE,
                acknowledged BOOL,
                acknowledged_by NCHAR(64),
                acknowledged_at TIMESTAMP
            ) TAGS (
                device_id NCHAR(64),
                plant NCHAR(32),
                area NCHAR(32)
            )
        """)

        # 1-minute aggregates supertable
        client.execute("""
            CREATE STABLE IF NOT EXISTS telemetry_1m (
                ts TIMESTAMP,
                avg_value DOUBLE,
                min_value DOUBLE,
                max_value DOUBLE,
                count INT
            ) TAGS (
                device_id NCHAR(64),
                plant NCHAR(32),
                area NCHAR(32),
                unit NCHAR(20)
            )
        """)

        # 1-hour aggregates supertable
        client.execute("""
            CREATE STABLE IF NOT EXISTS telemetry_1h (
                ts TIMESTAMP,
                avg_value DOUBLE,
                min_value DOUBLE,
                max_value DOUBLE,
                std_value DOUBLE,
                count INT
            ) TAGS (
                device_id NCHAR(64),
                plant NCHAR(32),
                area NCHAR(32),
                unit NCHAR(20)
            )
        """)

        # 1-day aggregates supertable
        client.execute("""
            CREATE STABLE IF NOT EXISTS telemetry_1d (
                ts TIMESTAMP,
                avg_value DOUBLE,
                min_value DOUBLE,
                max_value DOUBLE,
                std_value DOUBLE,
                count INT,
                uptime_percent DOUBLE
            ) TAGS (
                device_id NCHAR(64),
                plant NCHAR(32),
                area NCHAR(32),
                unit NCHAR(20)
            )
        """)

        logger.info("TDengine schema initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize TDengine schema: {e}")
        return False


def generate_table_name(
    plant: str, area: str, line: str = "", cell: str = "", device_id: str = ""
) -> str:
    """
    Generate child table name from device path.

    Follows naming convention: plant_area_line_cell_device_id
    """
    parts = [plant, area, line, cell, device_id]
    parts = [p.replace("-", "_").replace(" ", "_").lower() for p in parts if p]
    return "_".join(parts)


def insert_telemetry_batch(records: List[Dict[str, Any]]) -> int:
    """
    Batch insert telemetry records into TDengine.

    Uses INSERT INTO ... USING ... VALUES syntax for auto-table creation.

    Args:
        records: List of dicts with keys:
            - device_id, plant, area, line, cell, unit, device_type (tags)
            - ts, value, quality, sequence (values)

    Returns:
        Number of records inserted
    """
    if not records:
        return 0

    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        client.execute(f"USE {database}")

        # Build batch INSERT statement
        # TDengine supports multi-table batch insert
        sql_parts = []

        for record in records:
            table_name = generate_table_name(
                record.get("plant", "unknown"),
                record.get("area", "unknown"),
                record.get("line", ""),
                record.get("cell", ""),
                record["device_id"],
            )

            # Escape single quotes in values
            quality = str(record.get("quality", "good")).replace("'", "''")
            device_id = str(record["device_id"]).replace("'", "''")

            sql_parts.append(f"""
                {table_name} USING telemetry TAGS (
                    '{device_id}',
                    '{record.get('plant', '')}',
                    '{record.get('area', '')}',
                    '{record.get('line', '')}',
                    '{record.get('cell', '')}',
                    '{record.get('unit', '')}',
                    '{record.get('device_type', '')}'
                ) VALUES (
                    '{record['ts']}',
                    {float(record['value'])},
                    '{quality}',
                    {int(record.get('sequence', 0))}
                )
            """)

        # Execute batch insert
        sql = "INSERT INTO " + " ".join(sql_parts)
        client.execute(sql)

        return len(records)

    except Exception as e:
        logger.error(f"Failed to insert telemetry batch: {e}")
        raise


def insert_event(
    device_id: str,
    plant: str,
    area: str,
    event_type: str,
    severity: str,
    message: str,
    value: Optional[float] = None,
    threshold: Optional[float] = None,
    ts: Optional[str] = None,
) -> bool:
    """Insert an event record."""
    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        client.execute(f"USE {database}")

        table_name = f"{plant}_{area}_{device_id}_events".replace("-", "_").lower()
        ts = ts or datetime.utcnow().isoformat()

        sql = f"""
            INSERT INTO {table_name}
            USING events TAGS ('{device_id}', '{plant}', '{area}')
            VALUES (
                '{ts}',
                '{event_type}',
                '{severity}',
                '{message.replace("'", "''")}',
                {value if value is not None else 'NULL'},
                {threshold if threshold is not None else 'NULL'},
                false,
                '',
                NULL
            )
        """
        client.execute(sql)
        return True

    except Exception as e:
        logger.error(f"Failed to insert event: {e}")
        return False


def query_telemetry(
    device_id: str,
    start_time: str,
    end_time: str,
    aggregation: Optional[str] = None,
    interval: Optional[str] = None,
    limit: int = 10000,
) -> List[Dict[str, Any]]:
    """
    Query telemetry data for a device.

    Args:
        device_id: Device identifier
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        aggregation: Aggregation function (avg, max, min, sum, count)
        interval: Interval for aggregation (1m, 5m, 1h, 1d)
        limit: Maximum records to return

    Returns:
        List of telemetry records
    """
    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        client.execute(f"USE {database}")

        if aggregation and interval:
            sql = f"""
                SELECT
                    _wstart as ts,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    COUNT(*) as count
                FROM telemetry
                WHERE device_id = '{device_id}'
                    AND ts >= '{start_time}'
                    AND ts <= '{end_time}'
                INTERVAL({interval})
                LIMIT {limit}
            """
        else:
            sql = f"""
                SELECT ts, value, quality, sequence
                FROM telemetry
                WHERE device_id = '{device_id}'
                    AND ts >= '{start_time}'
                    AND ts <= '{end_time}'
                ORDER BY ts ASC
                LIMIT {limit}
            """

        results = client.fetchall(sql)

        if aggregation and interval:
            return [
                {
                    "ts": row[0],
                    "avg_value": row[1],
                    "min_value": row[2],
                    "max_value": row[3],
                    "count": row[4],
                }
                for row in results
            ]
        else:
            return [
                {
                    "ts": row[0],
                    "value": row[1],
                    "quality": row[2] if len(row) > 2 else "good",
                    "sequence": row[3] if len(row) > 3 else None,
                }
                for row in results
            ]

    except Exception as e:
        logger.error(f"Failed to query telemetry: {e}")
        raise


def query_latest_values(
    device_ids: Optional[List[str]] = None, area: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query latest values for devices.

    Uses TDengine's LAST_ROW function for fast last-value lookup.
    """
    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        client.execute(f"USE {database}")

        where_clauses = []
        if device_ids:
            ids = "', '".join(device_ids)
            where_clauses.append(f"device_id IN ('{ids}')")
        if area:
            where_clauses.append(f"area = '{area}'")

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        sql = f"""
            SELECT
                device_id,
                LAST_ROW(ts) as ts,
                LAST_ROW(value) as value,
                LAST_ROW(quality) as quality,
                area,
                unit
            FROM telemetry
            {where}
            GROUP BY device_id, area, unit
        """

        results = client.fetchall(sql)

        return [
            {
                "device_id": row[0],
                "ts": row[1],
                "value": row[2],
                "quality": row[3],
                "area": row[4],
                "unit": row[5],
            }
            for row in results
        ]

    except Exception as e:
        logger.error(f"Failed to query latest values: {e}")
        raise


def query_device_stats(device_id: str, period: str = "24h") -> Dict[str, Any]:
    """
    Query statistics for a device over a period.

    Returns avg, min, max, std, count for the period.
    """
    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        client.execute(f"USE {database}")

        sql = f"""
            SELECT
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                STDDEV(value) as std_value,
                COUNT(*) as count,
                FIRST(ts) as first_ts,
                LAST(ts) as last_ts
            FROM telemetry
            WHERE device_id = '{device_id}'
                AND ts >= NOW() - {period}
        """

        result = client.fetchone(sql)

        if result:
            return {
                "device_id": device_id,
                "period": period,
                "avg_value": result[0],
                "min_value": result[1],
                "max_value": result[2],
                "std_value": result[3],
                "count": result[4],
                "first_ts": result[5],
                "last_ts": result[6],
            }
        return {}

    except Exception as e:
        logger.error(f"Failed to query device stats: {e}")
        raise


def query_area_summary(area: str) -> List[Dict[str, Any]]:
    """
    Query summary for all devices in an area.
    """
    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        client.execute(f"USE {database}")

        sql = f"""
            SELECT
                device_id,
                device_type,
                unit,
                LAST_ROW(value) as last_value,
                LAST_ROW(ts) as last_ts,
                LAST_ROW(quality) as quality,
                AVG(value) as avg_1h
            FROM telemetry
            WHERE area = '{area}'
                AND ts >= NOW() - 1h
            GROUP BY device_id, device_type, unit
        """

        results = client.fetchall(sql)

        return [
            {
                "device_id": row[0],
                "device_type": row[1],
                "unit": row[2],
                "last_value": row[3],
                "last_ts": row[4],
                "quality": row[5],
                "avg_1h": row[6],
            }
            for row in results
        ]

    except Exception as e:
        logger.error(f"Failed to query area summary: {e}")
        raise


def compute_aggregates(
    source_table: str, target_table: str, interval: str, start_time: str, end_time: str
) -> int:
    """
    Compute aggregates from source to target table.

    Used by Celery tasks for continuous aggregation.
    """
    client = get_client()
    database = settings.TDENGINE.get("DATABASE", "forgelink_telemetry")

    try:
        client.execute(f"USE {database}")

        # Get distinct devices
        devices_sql = f"""
            SELECT DISTINCT device_id, plant, area, unit
            FROM {source_table}
            WHERE ts >= '{start_time}' AND ts < '{end_time}'
        """
        devices = client.fetchall(devices_sql)

        inserted = 0
        for device_id, plant, area, unit in devices:
            table_name = f"{plant}_{area}_{device_id}_{interval}".replace(
                "-", "_"
            ).lower()

            agg_sql = f"""
                SELECT
                    _wstart as ts,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    COUNT(*) as count
                FROM {source_table}
                WHERE device_id = '{device_id}'
                    AND ts >= '{start_time}'
                    AND ts < '{end_time}'
                INTERVAL({interval})
            """

            results = client.fetchall(agg_sql)

            for row in results:
                insert_sql = f"""
                    INSERT INTO {table_name}
                    USING {target_table} TAGS ('{device_id}', '{plant}', '{area}', '{unit}')
                    VALUES ('{row[0]}', {row[1]}, {row[2]}, {row[3]}, {row[4]})
                """
                client.execute(insert_sql)
                inserted += 1

        return inserted

    except Exception as e:
        logger.error(f"Failed to compute aggregates: {e}")
        raise
