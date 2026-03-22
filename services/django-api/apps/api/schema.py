"""ForgeLink GraphQL Schema.

Provides comprehensive GraphQL API for:
- Telemetry data queries
- Asset hierarchy queries
- Alert management queries and mutations
"""

import graphene
from graphene_django import DjangoObjectType

from apps.alerts.models import Alert, AlertHistory, AlertRule
from apps.assets.models import Area, Cell, Device, DeviceType, Line, Plant
from apps.telemetry.schema import TelemetryQuery

# =============================================================================
# Asset Types
# =============================================================================


class PlantType(DjangoObjectType):
    """GraphQL type for Plant model."""

    class Meta:
        model = Plant
        fields = [
            "id",
            "code",
            "name",
            "description",
            "timezone",
            "latitude",
            "longitude",
            "address",
            "is_active",
            "commissioned_at",
            "created_at",
            "updated_at",
        ]

    area_count = graphene.Int()
    device_count = graphene.Int()

    def resolve_area_count(self, info):
        return self.areas.count()

    def resolve_device_count(self, info):
        count = 0
        for area in self.areas.all():
            for line in area.lines.all():
                for cell in line.cells.all():
                    count += cell.devices.count()
        return count


class AreaType(DjangoObjectType):
    """GraphQL type for Area model."""

    class Meta:
        model = Area
        fields = [
            "id",
            "code",
            "name",
            "description",
            "area_type",
            "sequence",
            "is_active",
            "created_at",
            "updated_at",
        ]

    plant_code = graphene.String()
    line_count = graphene.Int()
    device_count = graphene.Int()

    def resolve_plant_code(self, info):
        return self.plant.code

    def resolve_line_count(self, info):
        return self.lines.count()

    def resolve_device_count(self, info):
        count = 0
        for line in self.lines.all():
            for cell in line.cells.all():
                count += cell.devices.count()
        return count


class LineType(DjangoObjectType):
    """GraphQL type for Line model."""

    class Meta:
        model = Line
        fields = [
            "id",
            "code",
            "name",
            "description",
            "design_capacity",
            "capacity_unit",
            "is_active",
            "created_at",
            "updated_at",
        ]

    area_code = graphene.String()
    cell_count = graphene.Int()

    def resolve_area_code(self, info):
        return self.area.code

    def resolve_cell_count(self, info):
        return self.cells.count()


class CellType(DjangoObjectType):
    """GraphQL type for Cell model."""

    class Meta:
        model = Cell
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]

    line_code = graphene.String()
    device_count = graphene.Int()

    def resolve_line_code(self, info):
        return self.line.code

    def resolve_device_count(self, info):
        return self.devices.count()


class DeviceTypeType(DjangoObjectType):
    """GraphQL type for DeviceType model."""

    class Meta:
        model = DeviceType
        fields = [
            "id",
            "code",
            "name",
            "description",
            "default_unit",
            "typical_min",
            "typical_max",
            "icon",
        ]

    device_count = graphene.Int()

    def resolve_device_count(self, info):
        return self.devices.count()


class DeviceGraphQLType(DjangoObjectType):
    """GraphQL type for Device model."""

    class Meta:
        model = Device
        fields = [
            "id",
            "device_id",
            "name",
            "description",
            "manufacturer",
            "model",
            "serial_number",
            "unit",
            "precision",
            "sampling_rate_ms",
            "warning_low",
            "warning_high",
            "critical_low",
            "critical_high",
            "status",
            "is_active",
            "last_seen",
            "installed_at",
            "last_calibration",
            "next_calibration",
            "tags",
            "created_at",
            "updated_at",
        ]

    full_path = graphene.String()
    uns_topic = graphene.String()
    effective_unit = graphene.String()
    cell_code = graphene.String()
    device_type_code = graphene.String()
    area_code = graphene.String()
    plant_code = graphene.String()

    def resolve_full_path(self, info):
        return self.full_path

    def resolve_uns_topic(self, info):
        return self.uns_topic

    def resolve_effective_unit(self, info):
        return self.effective_unit

    def resolve_cell_code(self, info):
        return self.cell.code

    def resolve_device_type_code(self, info):
        return self.device_type.code

    def resolve_area_code(self, info):
        return self.cell.line.area.code

    def resolve_plant_code(self, info):
        return self.cell.line.area.plant.code


# =============================================================================
# Alert Types
# =============================================================================


class AlertRuleType(DjangoObjectType):
    """GraphQL type for AlertRule model."""

    class Meta:
        model = AlertRule
        fields = [
            "id",
            "name",
            "description",
            "rule_type",
            "threshold_value",
            "threshold_low",
            "threshold_high",
            "rate_threshold",
            "stale_minutes",
            "severity",
            "notify_slack",
            "slack_channel",
            "cooldown_minutes",
            "is_active",
            "created_at",
            "updated_at",
            "created_by",
        ]

    device_id = graphene.String()
    device_type_code = graphene.String()
    alert_count = graphene.Int()

    def resolve_device_id(self, info):
        return self.device.device_id if self.device else None

    def resolve_device_type_code(self, info):
        return self.device_type.code if self.device_type else None

    def resolve_alert_count(self, info):
        return self.alerts.filter(status="active").count()


class AlertType(DjangoObjectType):
    """GraphQL type for Alert model."""

    class Meta:
        model = Alert
        fields = [
            "id",
            "alert_type",
            "severity",
            "message",
            "value",
            "threshold",
            "unit",
            "status",
            "triggered_at",
            "acknowledged_at",
            "acknowledged_by",
            "resolved_at",
            "resolved_by",
            "notified_slack",
            "notified_at",
        ]

    device_id = graphene.String()
    rule_name = graphene.String()
    duration_seconds = graphene.Int()
    area_code = graphene.String()
    plant_code = graphene.String()

    def resolve_device_id(self, info):
        return self.device.device_id

    def resolve_rule_name(self, info):
        return self.rule.name if self.rule else None

    def resolve_duration_seconds(self, info):
        return self.duration_seconds

    def resolve_area_code(self, info):
        return self.device.cell.line.area.code

    def resolve_plant_code(self, info):
        return self.device.cell.line.area.plant.code


class AlertHistoryType(DjangoObjectType):
    """GraphQL type for AlertHistory model."""

    class Meta:
        model = AlertHistory
        fields = [
            "id",
            "alert_id",
            "rule_id",
            "device_id",
            "plant",
            "area",
            "alert_type",
            "severity",
            "message",
            "value",
            "threshold",
            "triggered_at",
            "acknowledged_at",
            "resolved_at",
            "duration_seconds",
            "acknowledged_by",
            "resolved_by",
            "resolution_notes",
            "archived_at",
        ]


# =============================================================================
# Asset Queries
# =============================================================================


class AssetQuery(graphene.ObjectType):
    """GraphQL queries for assets."""

    # Plants
    plants = graphene.List(PlantType, is_active=graphene.Boolean())
    plant = graphene.Field(PlantType, code=graphene.String(required=True))

    # Areas
    areas = graphene.List(
        AreaType,
        plant_code=graphene.String(),
        is_active=graphene.Boolean(),
    )
    area = graphene.Field(AreaType, id=graphene.UUID(required=True))

    # Lines
    lines = graphene.List(
        LineType,
        area_id=graphene.UUID(),
        is_active=graphene.Boolean(),
    )
    line = graphene.Field(LineType, id=graphene.UUID(required=True))

    # Cells
    cells = graphene.List(
        CellType,
        line_id=graphene.UUID(),
        is_active=graphene.Boolean(),
    )
    cell = graphene.Field(CellType, id=graphene.UUID(required=True))

    # Device Types
    device_types = graphene.List(DeviceTypeType)
    device_type = graphene.Field(DeviceTypeType, code=graphene.String(required=True))

    # Devices
    devices = graphene.List(
        DeviceGraphQLType,
        area_code=graphene.String(),
        device_type_code=graphene.String(),
        status=graphene.String(),
        is_active=graphene.Boolean(),
        limit=graphene.Int(default_value=100),
    )
    device = graphene.Field(DeviceGraphQLType, device_id=graphene.String(required=True))

    def resolve_plants(self, info, is_active=None):
        qs = Plant.objects.all()
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    def resolve_plant(self, info, code):
        return Plant.objects.filter(code=code).first()

    def resolve_areas(self, info, plant_code=None, is_active=None):
        qs = Area.objects.select_related("plant").all()
        if plant_code:
            qs = qs.filter(plant__code=plant_code)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    def resolve_area(self, info, id):
        return Area.objects.filter(id=id).first()

    def resolve_lines(self, info, area_id=None, is_active=None):
        qs = Line.objects.select_related("area").all()
        if area_id:
            qs = qs.filter(area_id=area_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    def resolve_line(self, info, id):
        return Line.objects.filter(id=id).first()

    def resolve_cells(self, info, line_id=None, is_active=None):
        qs = Cell.objects.select_related("line").all()
        if line_id:
            qs = qs.filter(line_id=line_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    def resolve_cell(self, info, id):
        return Cell.objects.filter(id=id).first()

    def resolve_device_types(self, info):
        return DeviceType.objects.all()

    def resolve_device_type(self, info, code):
        return DeviceType.objects.filter(code=code).first()

    def resolve_devices(
        self,
        info,
        area_code=None,
        device_type_code=None,
        status=None,
        is_active=None,
        limit=100,
    ):
        qs = Device.objects.select_related(
            "cell__line__area__plant", "device_type"
        ).all()
        if area_code:
            qs = qs.filter(cell__line__area__code=area_code)
        if device_type_code:
            qs = qs.filter(device_type__code=device_type_code)
        if status:
            qs = qs.filter(status=status)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs[:limit]

    def resolve_device(self, info, device_id):
        return Device.objects.filter(device_id=device_id).first()


# =============================================================================
# Alert Queries
# =============================================================================


class AlertQuery(graphene.ObjectType):
    """GraphQL queries for alerts."""

    # Alert Rules
    alert_rules = graphene.List(
        AlertRuleType,
        severity=graphene.String(),
        is_active=graphene.Boolean(),
    )
    alert_rule = graphene.Field(AlertRuleType, id=graphene.UUID(required=True))

    # Active Alerts
    alerts = graphene.List(
        AlertType,
        status=graphene.String(),
        severity=graphene.String(),
        device_id=graphene.String(),
        area_code=graphene.String(),
        limit=graphene.Int(default_value=100),
    )
    alert = graphene.Field(AlertType, id=graphene.UUID(required=True))
    active_alerts = graphene.List(
        AlertType,
        severity=graphene.String(),
        area_code=graphene.String(),
    )

    # Alert History
    alert_history = graphene.List(
        AlertHistoryType,
        device_id=graphene.String(),
        area=graphene.String(),
        severity=graphene.String(),
        limit=graphene.Int(default_value=100),
    )

    # Statistics
    alert_stats = graphene.JSONString(area_code=graphene.String())

    def resolve_alert_rules(self, info, severity=None, is_active=None):
        qs = AlertRule.objects.all()
        if severity:
            qs = qs.filter(severity=severity)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    def resolve_alert_rule(self, info, id):
        return AlertRule.objects.filter(id=id).first()

    def resolve_alerts(
        self,
        info,
        status=None,
        severity=None,
        device_id=None,
        area_code=None,
        limit=100,
    ):
        qs = Alert.objects.select_related("device", "rule").all()
        if status:
            qs = qs.filter(status=status)
        if severity:
            qs = qs.filter(severity=severity)
        if device_id:
            qs = qs.filter(device__device_id=device_id)
        if area_code:
            qs = qs.filter(device__cell__line__area__code=area_code)
        return qs[:limit]

    def resolve_alert(self, info, id):
        return Alert.objects.filter(id=id).first()

    def resolve_active_alerts(self, info, severity=None, area_code=None):
        qs = Alert.objects.filter(status="active").select_related("device", "rule")
        if severity:
            qs = qs.filter(severity=severity)
        if area_code:
            qs = qs.filter(device__cell__line__area__code=area_code)
        return qs

    def resolve_alert_history(
        self, info, device_id=None, area=None, severity=None, limit=100
    ):
        qs = AlertHistory.objects.all()
        if device_id:
            qs = qs.filter(device_id=device_id)
        if area:
            qs = qs.filter(area=area)
        if severity:
            qs = qs.filter(severity=severity)
        return qs[:limit]

    def resolve_alert_stats(self, info, area_code=None):
        from django.db.models import Count

        qs = Alert.objects.all()
        if area_code:
            qs = qs.filter(device__cell__line__area__code=area_code)

        by_severity = dict(
            qs.values("severity")
            .annotate(count=Count("id"))
            .values_list("severity", "count")
        )
        by_status = dict(
            qs.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        active_count = qs.filter(status="active").count()

        return {
            "total": qs.count(),
            "active": active_count,
            "by_severity": by_severity,
            "by_status": by_status,
        }


# =============================================================================
# Alert Mutations
# =============================================================================


class AcknowledgeAlert(graphene.Mutation):
    """Acknowledge an active alert."""

    class Arguments:
        alert_id = graphene.UUID(required=True)
        user = graphene.String(required=True)

    success = graphene.Boolean()
    alert = graphene.Field(AlertType)
    error = graphene.String()

    def mutate(self, info, alert_id, user):
        try:
            alert = Alert.objects.get(id=alert_id)
            if alert.status != "active":
                return AcknowledgeAlert(
                    success=False,
                    alert=alert,
                    error=f"Alert is already {alert.status}",
                )
            alert.acknowledge(user)
            return AcknowledgeAlert(success=True, alert=alert, error=None)
        except Alert.DoesNotExist:
            return AcknowledgeAlert(success=False, alert=None, error="Alert not found")


class ResolveAlert(graphene.Mutation):
    """Resolve an alert."""

    class Arguments:
        alert_id = graphene.UUID(required=True)
        user = graphene.String(required=True)
        notes = graphene.String()

    success = graphene.Boolean()
    alert = graphene.Field(AlertType)
    error = graphene.String()

    def mutate(self, info, alert_id, user, notes=None):
        try:
            alert = Alert.objects.get(id=alert_id)
            if alert.status == "resolved":
                return ResolveAlert(
                    success=False,
                    alert=alert,
                    error="Alert is already resolved",
                )
            alert.resolve(user)
            return ResolveAlert(success=True, alert=alert, error=None)
        except Alert.DoesNotExist:
            return ResolveAlert(success=False, alert=None, error="Alert not found")


class BulkAcknowledgeAlerts(graphene.Mutation):
    """Acknowledge multiple alerts at once."""

    class Arguments:
        alert_ids = graphene.List(graphene.UUID, required=True)
        user = graphene.String(required=True)

    success = graphene.Boolean()
    acknowledged_count = graphene.Int()
    errors = graphene.List(graphene.String)

    def mutate(self, info, alert_ids, user):
        errors = []
        acknowledged = 0
        for alert_id in alert_ids:
            try:
                alert = Alert.objects.get(id=alert_id)
                if alert.status == "active":
                    alert.acknowledge(user)
                    acknowledged += 1
            except Alert.DoesNotExist:
                errors.append(f"Alert {alert_id} not found")
        return BulkAcknowledgeAlerts(
            success=len(errors) == 0,
            acknowledged_count=acknowledged,
            errors=errors if errors else None,
        )


class BulkResolveAlerts(graphene.Mutation):
    """Resolve multiple alerts at once."""

    class Arguments:
        alert_ids = graphene.List(graphene.UUID, required=True)
        user = graphene.String(required=True)

    success = graphene.Boolean()
    resolved_count = graphene.Int()
    errors = graphene.List(graphene.String)

    def mutate(self, info, alert_ids, user):
        errors = []
        resolved = 0
        for alert_id in alert_ids:
            try:
                alert = Alert.objects.get(id=alert_id)
                if alert.status != "resolved":
                    alert.resolve(user)
                    resolved += 1
            except Alert.DoesNotExist:
                errors.append(f"Alert {alert_id} not found")
        return BulkResolveAlerts(
            success=len(errors) == 0,
            resolved_count=resolved,
            errors=errors if errors else None,
        )


class Mutation(graphene.ObjectType):
    """Root GraphQL Mutation."""

    acknowledge_alert = AcknowledgeAlert.Field()
    resolve_alert = ResolveAlert.Field()
    bulk_acknowledge_alerts = BulkAcknowledgeAlerts.Field()
    bulk_resolve_alerts = BulkResolveAlerts.Field()


# =============================================================================
# Root Schema
# =============================================================================


class Query(TelemetryQuery, AssetQuery, AlertQuery, graphene.ObjectType):
    """Root GraphQL Query.

    Inherits from:
    - TelemetryQuery: Device history, statistics, anomalies, dashboard
    - AssetQuery: Plants, areas, lines, cells, devices
    - AlertQuery: Alert rules, alerts, history, statistics
    """

    hello = graphene.String(default_value="Welcome to ForgeLink Steel Factory IoT")
    version = graphene.String(default_value="1.0.0")


schema = graphene.Schema(query=Query, mutation=Mutation)
