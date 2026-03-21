"""GraphQL schema for telemetry data."""
import graphene
from graphene import ObjectType, Field, List, String, Float, Int, DateTime, Argument, Enum
from datetime import datetime, timezone

from .services import TelemetryService, TimeRange, AggregationInterval


class TimeRangeEnum(Enum):
    """Time range options for queries."""
    LAST_HOUR = '1h'
    LAST_6_HOURS = '6h'
    LAST_24_HOURS = '24h'
    LAST_7_DAYS = '7d'
    LAST_30_DAYS = '30d'


class AggregationIntervalEnum(Enum):
    """Aggregation interval options."""
    RAW = 'raw'
    ONE_MINUTE = '1m'
    FIVE_MINUTES = '5m'
    FIFTEEN_MINUTES = '15m'
    ONE_HOUR = '1h'
    ONE_DAY = '1d'


class QualityEnum(Enum):
    """Data quality indicators."""
    GOOD = 'good'
    BAD = 'bad'
    UNCERTAIN = 'uncertain'


class AnomalyTypeEnum(Enum):
    """Anomaly type indicators."""
    HIGH = 'high'
    LOW = 'low'


# ============================================
# Telemetry Types
# ============================================

class TelemetryPointType(ObjectType):
    """Single telemetry data point."""
    timestamp = DateTime(description="Point timestamp")
    value = Float(description="Sensor value")
    quality = String(description="Data quality (good/bad/uncertain)")
    sequence = Int(description="Sequence number")

    @staticmethod
    def resolve_timestamp(root, info):
        ts = root.get('ts') or root.get('timestamp')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts


class AggregatedTelemetryType(ObjectType):
    """Aggregated telemetry data."""
    timestamp = DateTime(description="Bucket timestamp")
    avg_value = Float(description="Average value")
    min_value = Float(description="Minimum value")
    max_value = Float(description="Maximum value")
    count = Int(description="Number of points")

    @staticmethod
    def resolve_timestamp(root, info):
        ts = root.get('ts') or root.get('timestamp')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts


class DeviceLatestType(ObjectType):
    """Latest value for a device."""
    device_id = String(description="Device identifier")
    timestamp = DateTime(description="Last update time")
    value = Float(description="Current value")
    quality = String(description="Data quality")
    area = String(description="Factory area")
    unit = String(description="Measurement unit")

    @staticmethod
    def resolve_timestamp(root, info):
        ts = root.get('ts') or root.get('last_ts')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts


class DeviceStatisticsType(ObjectType):
    """Device statistics over a time period."""
    device_id = String(description="Device identifier")
    period = String(description="Statistics period")
    avg_value = Float(description="Average value")
    min_value = Float(description="Minimum value")
    max_value = Float(description="Maximum value")
    std_value = Float(description="Standard deviation")
    count = Int(description="Total data points")
    first_timestamp = DateTime(description="First data point time")
    last_timestamp = DateTime(description="Last data point time")

    @staticmethod
    def resolve_first_timestamp(root, info):
        ts = root.get('first_ts')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts

    @staticmethod
    def resolve_last_timestamp(root, info):
        ts = root.get('last_ts')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts


class AnomalyType(ObjectType):
    """Detected anomaly."""
    timestamp = DateTime(description="Anomaly timestamp")
    value = Float(description="Anomalous value")
    quality = String(description="Data quality")
    anomaly_type = String(description="Type: high or low")
    deviation = Float(description="Standard deviations from mean")

    @staticmethod
    def resolve_timestamp(root, info):
        ts = root.get('ts') or root.get('timestamp')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts


# ============================================
# Area & Plant Types
# ============================================

class DeviceSummaryType(ObjectType):
    """Device summary in area overview."""
    device_id = String()
    device_type = String()
    unit = String()
    last_value = Float()
    last_timestamp = DateTime()
    quality = String()
    avg_1h = Float()

    @staticmethod
    def resolve_last_timestamp(root, info):
        ts = root.get('last_ts')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts


class AreaOverviewType(ObjectType):
    """Overview of an area."""
    area = String(description="Area name")
    total_devices = Int(description="Total device count")
    online = Int(description="Devices online (good quality)")
    warning = Int(description="Devices with warnings")
    fault = Int(description="Devices with faults")
    devices = List(DeviceSummaryType, description="Device summaries")


class AreaStatusType(ObjectType):
    """Area status in plant dashboard."""
    total = Int()
    online = Int()
    warning = Int()
    fault = Int()


class PlantTotalsType(ObjectType):
    """Plant-wide totals."""
    devices = Int()
    online = Int()
    warning = Int()
    fault = Int()


class PlantDashboardType(ObjectType):
    """Plant-wide dashboard data."""
    timestamp = DateTime(description="Dashboard timestamp")
    melt_shop = Field(AreaStatusType)
    continuous_casting = Field(AreaStatusType)
    rolling_mill = Field(AreaStatusType)
    finishing = Field(AreaStatusType)
    totals = Field(PlantTotalsType)

    @staticmethod
    def resolve_timestamp(root, info):
        ts = root.get('timestamp')
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return ts

    @staticmethod
    def resolve_melt_shop(root, info):
        return root.get('areas', {}).get('melt-shop')

    @staticmethod
    def resolve_continuous_casting(root, info):
        return root.get('areas', {}).get('continuous-casting')

    @staticmethod
    def resolve_rolling_mill(root, info):
        return root.get('areas', {}).get('rolling-mill')

    @staticmethod
    def resolve_finishing(root, info):
        return root.get('areas', {}).get('finishing')


# ============================================
# Device History Response
# ============================================

class DeviceHistoryType(ObjectType):
    """Device history response."""
    device_id = String()
    count = Int()
    data = List(TelemetryPointType)


class MultiDeviceLatestType(ObjectType):
    """Multiple device latest values response."""
    count = Int()
    data = List(DeviceLatestType)


class AnomalyDetectionType(ObjectType):
    """Anomaly detection response."""
    device_id = String()
    count = Int()
    anomalies = List(AnomalyType)


class DeviceComparisonType(ObjectType):
    """Device comparison data."""
    device_id = String()
    data = List(AggregatedTelemetryType)


# ============================================
# Query Type
# ============================================

class TelemetryQuery(ObjectType):
    """Telemetry GraphQL queries."""

    # Device queries
    device_history = Field(
        DeviceHistoryType,
        device_id=String(required=True, description="Device ID"),
        time_range=TimeRangeEnum(description="Predefined time range"),
        start_time=DateTime(description="Start time (ISO format)"),
        end_time=DateTime(description="End time (ISO format)"),
        interval=AggregationIntervalEnum(description="Aggregation interval"),
        limit=Int(default_value=10000, description="Max records"),
        description="Get historical telemetry for a device"
    )

    device_latest = Field(
        DeviceLatestType,
        device_id=String(required=True, description="Device ID"),
        description="Get latest value for a device"
    )

    device_statistics = Field(
        DeviceStatisticsType,
        device_id=String(required=True, description="Device ID"),
        period=String(default_value="24h", description="Period: 1h, 6h, 24h, 7d, 30d"),
        description="Get statistics for a device"
    )

    device_anomalies = Field(
        AnomalyDetectionType,
        device_id=String(required=True, description="Device ID"),
        period=String(default_value="24h", description="Period: 1h, 6h, 24h, 7d"),
        std_threshold=Float(default_value=3.0, description="Standard deviations threshold"),
        description="Detect anomalies for a device"
    )

    # Multi-device queries
    latest_values = Field(
        MultiDeviceLatestType,
        device_ids=List(String, description="List of device IDs"),
        area=String(description="Filter by area"),
        description="Get latest values for multiple devices"
    )

    compare_devices = List(
        DeviceComparisonType,
        device_ids=List(String, required=True, description="Device IDs to compare"),
        start_time=DateTime(required=True, description="Start time"),
        end_time=DateTime(required=True, description="End time"),
        interval=String(default_value="1h", description="Aggregation interval"),
        description="Compare multiple devices over a time range"
    )

    # Area queries
    area_overview = Field(
        AreaOverviewType,
        area=String(required=True, description="Area name"),
        description="Get overview of devices in an area"
    )

    # Plant queries
    plant_dashboard = Field(
        PlantDashboardType,
        description="Get plant-wide dashboard data"
    )

    # Resolvers
    @staticmethod
    def resolve_device_history(root, info, device_id, time_range=None, start_time=None,
                               end_time=None, interval=None, limit=10000):
        # Map enums to service enums
        tr = None
        if time_range:
            tr_map = {
                '1h': TimeRange.LAST_HOUR,
                '6h': TimeRange.LAST_6_HOURS,
                '24h': TimeRange.LAST_24_HOURS,
                '7d': TimeRange.LAST_7_DAYS,
                '30d': TimeRange.LAST_30_DAYS,
            }
            tr = tr_map.get(time_range)

        intv = None
        if interval and interval != 'raw':
            intv_map = {
                '1m': AggregationInterval.ONE_MINUTE,
                '5m': AggregationInterval.FIVE_MINUTES,
                '15m': AggregationInterval.FIFTEEN_MINUTES,
                '1h': AggregationInterval.ONE_HOUR,
                '1d': AggregationInterval.ONE_DAY,
            }
            intv = intv_map.get(interval)

        data = TelemetryService.get_device_history(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            time_range=tr,
            interval=intv,
            limit=limit
        )

        return {
            'device_id': device_id,
            'count': len(data),
            'data': data
        }

    @staticmethod
    def resolve_device_latest(root, info, device_id):
        return TelemetryService.get_latest_value(device_id)

    @staticmethod
    def resolve_device_statistics(root, info, device_id, period='24h'):
        return TelemetryService.get_device_statistics(device_id, period)

    @staticmethod
    def resolve_device_anomalies(root, info, device_id, period='24h', std_threshold=3.0):
        anomalies = TelemetryService.detect_anomalies(
            device_id=device_id,
            period=period,
            std_threshold=std_threshold
        )
        return {
            'device_id': device_id,
            'count': len(anomalies),
            'anomalies': anomalies
        }

    @staticmethod
    def resolve_latest_values(root, info, device_ids=None, area=None):
        data = TelemetryService.get_latest_values(device_ids=device_ids, area=area)
        return {
            'count': len(data),
            'data': data
        }

    @staticmethod
    def resolve_compare_devices(root, info, device_ids, start_time, end_time, interval='1h'):
        data = TelemetryService.compare_devices(
            device_ids=device_ids,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )
        return [
            {'device_id': device_id, 'data': points}
            for device_id, points in data.items()
        ]

    @staticmethod
    def resolve_area_overview(root, info, area):
        return TelemetryService.get_area_overview(area)

    @staticmethod
    def resolve_plant_dashboard(root, info):
        return TelemetryService.get_plant_dashboard()


# Export for integration into main schema
telemetry_query = TelemetryQuery
