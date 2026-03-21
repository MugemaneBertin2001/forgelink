"""
Telemetry service layer for ForgeLink.

Provides high-level operations for telemetry data management,
coordinating between TDengine, Kafka, and the simulator.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum

from django.conf import settings

from .tdengine import (
    query_telemetry,
    query_latest_values,
    query_device_stats,
    query_area_summary,
    insert_telemetry_batch,
    insert_event,
)

logger = logging.getLogger(__name__)


class TimeRange(Enum):
    """Predefined time ranges for queries."""
    LAST_HOUR = '1h'
    LAST_6_HOURS = '6h'
    LAST_24_HOURS = '24h'
    LAST_7_DAYS = '7d'
    LAST_30_DAYS = '30d'


class AggregationInterval(Enum):
    """Aggregation intervals for time-series data."""
    RAW = None
    ONE_MINUTE = '1m'
    FIVE_MINUTES = '5m'
    FIFTEEN_MINUTES = '15m'
    ONE_HOUR = '1h'
    ONE_DAY = '1d'


@dataclass
class TelemetryPoint:
    """Single telemetry data point."""
    device_id: str
    timestamp: datetime
    value: float
    quality: str = 'good'
    sequence: int = 0
    unit: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'ts': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'value': self.value,
            'quality': self.quality,
            'sequence': self.sequence,
            'unit': self.unit,
        }


@dataclass
class DeviceReading:
    """Current device reading with context."""
    device_id: str
    value: float
    quality: str
    timestamp: datetime
    area: str
    unit: str
    avg_1h: Optional[float] = None
    min_1h: Optional[float] = None
    max_1h: Optional[float] = None


class TelemetryService:
    """
    High-level service for telemetry operations.

    Provides methods for:
    - Querying historical data
    - Getting live values
    - Computing statistics
    - Area-level summaries
    """

    @staticmethod
    def get_device_history(
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        time_range: Optional[TimeRange] = None,
        interval: Optional[AggregationInterval] = None,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Get historical telemetry for a device.

        Args:
            device_id: Device identifier
            start_time: Start of time range
            end_time: End of time range
            time_range: Predefined time range (alternative to start/end)
            interval: Aggregation interval (None for raw data)
            limit: Maximum records

        Returns:
            List of telemetry records
        """
        # Calculate time range
        if time_range:
            end_time = datetime.now(timezone.utc)
            duration_map = {
                TimeRange.LAST_HOUR: timedelta(hours=1),
                TimeRange.LAST_6_HOURS: timedelta(hours=6),
                TimeRange.LAST_24_HOURS: timedelta(hours=24),
                TimeRange.LAST_7_DAYS: timedelta(days=7),
                TimeRange.LAST_30_DAYS: timedelta(days=30),
            }
            start_time = end_time - duration_map.get(time_range, timedelta(hours=24))

        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now(timezone.utc)

        # Format times
        start_str = start_time.isoformat() if isinstance(start_time, datetime) else start_time
        end_str = end_time.isoformat() if isinstance(end_time, datetime) else end_time

        # Query TDengine
        aggregation = 'avg' if interval and interval != AggregationInterval.RAW else None
        interval_str = interval.value if interval and interval != AggregationInterval.RAW else None

        return query_telemetry(
            device_id=device_id,
            start_time=start_str,
            end_time=end_str,
            aggregation=aggregation,
            interval=interval_str,
            limit=limit
        )

    @staticmethod
    def get_latest_value(device_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest value for a single device."""
        results = query_latest_values(device_ids=[device_id])
        return results[0] if results else None

    @staticmethod
    def get_latest_values(
        device_ids: Optional[List[str]] = None,
        area: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get latest values for multiple devices.

        Args:
            device_ids: List of specific device IDs
            area: Filter by area (if device_ids not specified)

        Returns:
            List of latest readings
        """
        return query_latest_values(device_ids=device_ids, area=area)

    @staticmethod
    def get_device_statistics(
        device_id: str,
        period: str = '24h'
    ) -> Dict[str, Any]:
        """
        Get statistics for a device.

        Args:
            device_id: Device identifier
            period: Time period (1h, 6h, 24h, 7d, 30d)

        Returns:
            Statistics dict with avg, min, max, std, count
        """
        return query_device_stats(device_id=device_id, period=period)

    @staticmethod
    def get_area_overview(area: str) -> Dict[str, Any]:
        """
        Get overview of all devices in an area.

        Returns summary with device counts, status, and alerts.
        """
        devices = query_area_summary(area)

        # Categorize devices
        total = len(devices)
        online = sum(1 for d in devices if d.get('quality') == 'good')
        warning = sum(1 for d in devices if d.get('quality') == 'uncertain')
        fault = sum(1 for d in devices if d.get('quality') == 'bad')

        # Group by device type
        by_type = {}
        for device in devices:
            dtype = device.get('device_type', 'unknown')
            if dtype not in by_type:
                by_type[dtype] = []
            by_type[dtype].append(device)

        return {
            'area': area,
            'total_devices': total,
            'online': online,
            'warning': warning,
            'fault': fault,
            'devices': devices,
            'by_type': by_type,
        }

    @staticmethod
    def get_plant_dashboard() -> Dict[str, Any]:
        """
        Get plant-wide dashboard data.

        Returns overview of all areas with key metrics.
        """
        areas = ['melt-shop', 'continuous-casting', 'rolling-mill', 'finishing']
        dashboard = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'areas': {},
            'totals': {
                'devices': 0,
                'online': 0,
                'warning': 0,
                'fault': 0,
            }
        }

        for area in areas:
            try:
                overview = TelemetryService.get_area_overview(area)
                dashboard['areas'][area] = {
                    'total': overview['total_devices'],
                    'online': overview['online'],
                    'warning': overview['warning'],
                    'fault': overview['fault'],
                }
                dashboard['totals']['devices'] += overview['total_devices']
                dashboard['totals']['online'] += overview['online']
                dashboard['totals']['warning'] += overview['warning']
                dashboard['totals']['fault'] += overview['fault']
            except Exception as e:
                logger.error(f"Error getting overview for {area}: {e}")
                dashboard['areas'][area] = {'error': str(e)}

        return dashboard

    @staticmethod
    def record_telemetry(records: List[Dict[str, Any]]) -> int:
        """
        Record telemetry data points.

        Args:
            records: List of telemetry records

        Returns:
            Number of records inserted
        """
        if not records:
            return 0

        # Ensure timestamps are formatted
        for record in records:
            if 'ts' not in record and 'timestamp' in record:
                record['ts'] = record.pop('timestamp')
            if isinstance(record.get('ts'), datetime):
                record['ts'] = record['ts'].isoformat()

        return insert_telemetry_batch(records)

    @staticmethod
    def record_event(
        device_id: str,
        plant: str,
        area: str,
        event_type: str,
        severity: str,
        message: str,
        value: Optional[float] = None,
        threshold: Optional[float] = None
    ) -> bool:
        """Record an event/alarm."""
        return insert_event(
            device_id=device_id,
            plant=plant,
            area=area,
            event_type=event_type,
            severity=severity,
            message=message,
            value=value,
            threshold=threshold
        )

    @staticmethod
    def compare_devices(
        device_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        interval: str = '1h'
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Compare multiple devices over a time range.

        Returns aggregated data for each device for comparison.
        """
        start_str = start_time.isoformat()
        end_str = end_time.isoformat()

        result = {}
        for device_id in device_ids:
            result[device_id] = query_telemetry(
                device_id=device_id,
                start_time=start_str,
                end_time=end_str,
                aggregation='avg',
                interval=interval
            )

        return result

    @staticmethod
    def detect_anomalies(
        device_id: str,
        period: str = '24h',
        std_threshold: float = 3.0
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalous readings for a device.

        Uses simple statistical method (values > N standard deviations).
        """
        # Get statistics
        stats = query_device_stats(device_id, period)
        if not stats or not stats.get('avg_value') or not stats.get('std_value'):
            return []

        avg = stats['avg_value']
        std = stats['std_value']
        lower_bound = avg - (std_threshold * std)
        upper_bound = avg + (std_threshold * std)

        # Get raw data
        end_time = datetime.now(timezone.utc)
        duration_map = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}
        hours = duration_map.get(period, 24)
        start_time = end_time - timedelta(hours=hours)

        data = query_telemetry(
            device_id=device_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )

        # Find anomalies
        anomalies = []
        for point in data:
            value = point.get('value')
            if value is not None and (value < lower_bound or value > upper_bound):
                anomalies.append({
                    **point,
                    'anomaly_type': 'high' if value > upper_bound else 'low',
                    'deviation': abs(value - avg) / std if std > 0 else 0,
                })

        return anomalies
