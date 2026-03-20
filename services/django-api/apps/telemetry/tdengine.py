"""TDengine connection and utilities for ForgeLink telemetry."""
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from django.conf import settings
import taosrest

logger = logging.getLogger(__name__)


def get_tdengine_connection():
    """
    Get a TDengine REST connection.
    Returns None if connection fails.
    """
    try:
        conn = taosrest.connect(
            url=f"http://{settings.TDENGINE['HOST']}:{settings.TDENGINE['PORT']}",
            user=settings.TDENGINE['USER'],
            password=settings.TDENGINE['PASSWORD'],
            database=settings.TDENGINE['DATABASE'],
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to TDengine: {e}")
        return None


@contextmanager
def tdengine_cursor():
    """Context manager for TDengine cursor."""
    conn = get_tdengine_connection()
    if not conn:
        raise ConnectionError("Could not connect to TDengine")

    try:
        cursor = conn.cursor()
        yield cursor
    finally:
        cursor.close()
        conn.close()


def init_tdengine_schema():
    """
    Initialize TDengine database and supertables.
    Called on first startup.
    """
    conn = get_tdengine_connection()
    if not conn:
        logger.error("Cannot initialize TDengine schema - connection failed")
        return False

    try:
        cursor = conn.cursor()

        # Create database if not exists
        cursor.execute(f"""
            CREATE DATABASE IF NOT EXISTS {settings.TDENGINE['DATABASE']}
            KEEP 365
            DURATION 10
            BUFFER 256
            WAL_LEVEL 1
            CACHEMODEL 'last_row'
        """)

        cursor.execute(f"USE {settings.TDENGINE['DATABASE']}")

        # Create supertable for telemetry data
        cursor.execute("""
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

        # Create supertable for device status
        cursor.execute("""
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

        logger.info("TDengine schema initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize TDengine schema: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def insert_telemetry_batch(records: List[Dict[str, Any]]) -> int:
    """
    Batch insert telemetry records into TDengine.

    Args:
        records: List of telemetry records with keys:
            - device_id, plant, area, line, cell, unit, device_type (tags)
            - ts, value, quality, sequence (values)

    Returns:
        Number of records inserted
    """
    if not records:
        return 0

    conn = get_tdengine_connection()
    if not conn:
        raise ConnectionError("Could not connect to TDengine")

    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {settings.TDENGINE['DATABASE']}")

        inserted = 0
        for record in records:
            # Generate child table name from device path
            table_name = _generate_table_name(record)

            # Create child table if not exists and insert
            sql = f"""
                INSERT INTO {table_name}
                USING telemetry
                TAGS (
                    '{record['device_id']}',
                    '{record['plant']}',
                    '{record['area']}',
                    '{record.get('line', '')}',
                    '{record.get('cell', '')}',
                    '{record.get('unit', '')}',
                    '{record.get('device_type', '')}'
                )
                VALUES (
                    '{record['ts']}',
                    {record['value']},
                    '{record.get('quality', 'good')}',
                    {record.get('sequence', 0)}
                )
            """
            cursor.execute(sql)
            inserted += 1

        return inserted

    except Exception as e:
        logger.error(f"Failed to insert telemetry batch: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def _generate_table_name(record: Dict[str, Any]) -> str:
    """Generate child table name from device path."""
    parts = [
        record.get('plant', ''),
        record.get('area', ''),
        record.get('line', ''),
        record.get('cell', ''),
        record['device_id'],
    ]
    # Remove empty parts and sanitize
    parts = [p.replace('-', '_').replace(' ', '_').lower() for p in parts if p]
    return '_'.join(parts)


def query_telemetry(
    device_id: str,
    start_time: str,
    end_time: str,
    aggregation: Optional[str] = None,
    interval: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query telemetry data for a device.

    Args:
        device_id: Device identifier
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        aggregation: Optional aggregation function (avg, max, min, sum)
        interval: Optional interval for aggregation (1m, 1h, 1d)

    Returns:
        List of telemetry records
    """
    conn = get_tdengine_connection()
    if not conn:
        raise ConnectionError("Could not connect to TDengine")

    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {settings.TDENGINE['DATABASE']}")

        if aggregation and interval:
            sql = f"""
                SELECT
                    _wstart as ts,
                    {aggregation}(value) as value,
                    LAST(quality) as quality
                FROM telemetry
                WHERE device_id = '{device_id}'
                    AND ts >= '{start_time}'
                    AND ts <= '{end_time}'
                INTERVAL({interval})
            """
        else:
            sql = f"""
                SELECT ts, value, quality, sequence
                FROM telemetry
                WHERE device_id = '{device_id}'
                    AND ts >= '{start_time}'
                    AND ts <= '{end_time}'
                ORDER BY ts ASC
            """

        cursor.execute(sql)
        results = cursor.fetchall()

        return [
            {
                'ts': row[0],
                'value': row[1],
                'quality': row[2] if len(row) > 2 else 'good',
                'sequence': row[3] if len(row) > 3 else None,
            }
            for row in results
        ]

    except Exception as e:
        logger.error(f"Failed to query telemetry: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
