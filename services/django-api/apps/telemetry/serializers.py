"""REST API serializers for telemetry data."""
from rest_framework import serializers
from datetime import datetime


class TelemetryPointSerializer(serializers.Serializer):
    """Serializer for a single telemetry data point."""

    ts = serializers.DateTimeField(source='timestamp', required=False)
    timestamp = serializers.DateTimeField(required=False)
    value = serializers.FloatField()
    quality = serializers.ChoiceField(
        choices=['good', 'bad', 'uncertain'],
        default='good'
    )
    sequence = serializers.IntegerField(required=False, default=0)


class TelemetryRecordSerializer(serializers.Serializer):
    """Serializer for telemetry record with device context."""

    device_id = serializers.CharField(max_length=64)
    ts = serializers.DateTimeField(required=False)
    timestamp = serializers.DateTimeField(required=False)
    value = serializers.FloatField()
    quality = serializers.CharField(max_length=10, default='good')
    sequence = serializers.IntegerField(required=False, default=0)
    unit = serializers.CharField(max_length=20, required=False)
    plant = serializers.CharField(max_length=32, required=False)
    area = serializers.CharField(max_length=32, required=False)
    line = serializers.CharField(max_length=32, required=False)
    cell = serializers.CharField(max_length=32, required=False)
    device_type = serializers.CharField(max_length=32, required=False)

    def validate(self, data):
        """Ensure either ts or timestamp is provided."""
        if 'ts' not in data and 'timestamp' not in data:
            data['ts'] = datetime.utcnow().isoformat()
        elif 'timestamp' in data and 'ts' not in data:
            data['ts'] = data.pop('timestamp')
        return data


class AggregatedTelemetrySerializer(serializers.Serializer):
    """Serializer for aggregated telemetry data."""

    ts = serializers.DateTimeField()
    avg_value = serializers.FloatField()
    min_value = serializers.FloatField()
    max_value = serializers.FloatField()
    count = serializers.IntegerField()


class DeviceLatestValueSerializer(serializers.Serializer):
    """Serializer for device's latest value."""

    device_id = serializers.CharField()
    ts = serializers.DateTimeField()
    value = serializers.FloatField()
    quality = serializers.CharField()
    area = serializers.CharField(required=False)
    unit = serializers.CharField(required=False)


class DeviceStatisticsSerializer(serializers.Serializer):
    """Serializer for device statistics."""

    device_id = serializers.CharField()
    period = serializers.CharField()
    avg_value = serializers.FloatField(allow_null=True)
    min_value = serializers.FloatField(allow_null=True)
    max_value = serializers.FloatField(allow_null=True)
    std_value = serializers.FloatField(allow_null=True)
    count = serializers.IntegerField()
    first_ts = serializers.DateTimeField(allow_null=True)
    last_ts = serializers.DateTimeField(allow_null=True)


class AreaDeviceSummarySerializer(serializers.Serializer):
    """Serializer for device summary in an area."""

    device_id = serializers.CharField()
    device_type = serializers.CharField(allow_null=True)
    unit = serializers.CharField(allow_null=True)
    last_value = serializers.FloatField(allow_null=True)
    last_ts = serializers.DateTimeField(allow_null=True)
    quality = serializers.CharField(allow_null=True)
    avg_1h = serializers.FloatField(allow_null=True)


class AreaOverviewSerializer(serializers.Serializer):
    """Serializer for area overview."""

    area = serializers.CharField()
    total_devices = serializers.IntegerField()
    online = serializers.IntegerField()
    warning = serializers.IntegerField()
    fault = serializers.IntegerField()
    devices = AreaDeviceSummarySerializer(many=True)
    by_type = serializers.DictField()


class PlantDashboardAreaSerializer(serializers.Serializer):
    """Serializer for area in plant dashboard."""

    total = serializers.IntegerField()
    online = serializers.IntegerField()
    warning = serializers.IntegerField()
    fault = serializers.IntegerField()


class PlantDashboardTotalsSerializer(serializers.Serializer):
    """Serializer for plant dashboard totals."""

    devices = serializers.IntegerField()
    online = serializers.IntegerField()
    warning = serializers.IntegerField()
    fault = serializers.IntegerField()


class PlantDashboardSerializer(serializers.Serializer):
    """Serializer for plant-wide dashboard."""

    timestamp = serializers.DateTimeField()
    areas = serializers.DictField(child=PlantDashboardAreaSerializer())
    totals = PlantDashboardTotalsSerializer()


class AnomalySerializer(serializers.Serializer):
    """Serializer for anomaly detection results."""

    ts = serializers.DateTimeField()
    value = serializers.FloatField()
    quality = serializers.CharField()
    anomaly_type = serializers.ChoiceField(choices=['high', 'low'])
    deviation = serializers.FloatField()


# ============================================
# Request Serializers
# ============================================

class TelemetryQuerySerializer(serializers.Serializer):
    """Serializer for telemetry query parameters."""

    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    time_range = serializers.ChoiceField(
        choices=['1h', '6h', '24h', '7d', '30d'],
        required=False
    )
    interval = serializers.ChoiceField(
        choices=['raw', '1m', '5m', '15m', '1h', '1d'],
        required=False,
        default='raw'
    )
    limit = serializers.IntegerField(required=False, default=10000, max_value=100000)


class BatchTelemetrySerializer(serializers.Serializer):
    """Serializer for batch telemetry insertion."""

    records = TelemetryRecordSerializer(many=True)


class DeviceCompareSerializer(serializers.Serializer):
    """Serializer for device comparison request."""

    device_ids = serializers.ListField(
        child=serializers.CharField(max_length=64),
        min_length=2,
        max_length=10
    )
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    interval = serializers.ChoiceField(
        choices=['1m', '5m', '15m', '1h', '1d'],
        default='1h'
    )


class AnomalyDetectionSerializer(serializers.Serializer):
    """Serializer for anomaly detection request."""

    period = serializers.ChoiceField(
        choices=['1h', '6h', '24h', '7d'],
        default='24h'
    )
    std_threshold = serializers.FloatField(default=3.0, min_value=1.0, max_value=5.0)


# ============================================
# Event Serializers
# ============================================

class TelemetryEventSerializer(serializers.Serializer):
    """Serializer for telemetry events."""

    device_id = serializers.CharField(max_length=64)
    plant = serializers.CharField(max_length=32)
    area = serializers.CharField(max_length=32)
    event_type = serializers.ChoiceField(choices=[
        'threshold_high', 'threshold_low',
        'critical_high', 'critical_low',
        'device_fault', 'device_recovery',
        'rate_of_change'
    ])
    severity = serializers.ChoiceField(choices=[
        'critical', 'high', 'medium', 'low', 'info'
    ])
    message = serializers.CharField(max_length=512)
    value = serializers.FloatField(required=False, allow_null=True)
    threshold = serializers.FloatField(required=False, allow_null=True)
    ts = serializers.DateTimeField(required=False)
