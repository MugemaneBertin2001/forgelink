"""
ForgeLink RBAC Models.

Permission-based access control where:
- Permissions are atomic actions (what you CAN do)
- Roles are groups of permissions (convenience)
- Admin can create custom roles combining permissions
"""

import uuid

from django.core.cache import cache
from django.db import models


class Permission(models.Model):
    """
    Atomic permission representing a single action.

    Permissions are predefined by the system. When new features are added,
    new permissions are created via migrations.

    Format: <module>.<action>
    Examples: alerts.acknowledge, assets.create, telemetry.export
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Permission identifier (e.g., 'alerts.acknowledge')
    code = models.CharField(max_length=64, unique=True, db_index=True)

    # Human-readable name
    name = models.CharField(max_length=128)

    # Description of what this permission allows
    description = models.TextField(blank=True)

    # Module grouping for UI organization
    MODULE_CHOICES = [
        ("assets", "Assets"),
        ("alerts", "Alerts"),
        ("telemetry", "Telemetry"),
        ("simulator", "Simulator"),
        ("admin", "Administration"),
        ("audit", "Audit"),
    ]
    module = models.CharField(max_length=32, choices=MODULE_CHOICES)

    # Order for display
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "core_permission"
        ordering = ["module", "sort_order", "code"]
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Role(models.Model):
    """
    Role that groups permissions together.

    Default roles are seeded, but admins can create custom roles
    via Django admin by combining permissions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Role identifier (e.g., 'FACTORY_ADMIN', 'SHIFT_SUPERVISOR')
    code = models.CharField(max_length=64, unique=True, db_index=True)

    # Human-readable name
    name = models.CharField(max_length=128)

    # Description
    description = models.TextField(blank=True)

    # Permissions granted by this role
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
    )

    # Is this a system role (cannot be deleted)?
    is_system = models.BooleanField(
        default=False, help_text="System roles cannot be deleted"
    )

    # Is this role active?
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_role"
        ordering = ["name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.name

    def get_permission_codes(self) -> set:
        """Get all permission codes for this role."""
        return set(self.permissions.values_list("code", flat=True))

    @classmethod
    def get_permissions_for_role(cls, role_code: str) -> set:
        """
        Get permission codes for a role with caching.
        """
        cache_key = f"role_permissions:{role_code}"
        permissions = cache.get(cache_key)

        if permissions is None:
            try:
                role = cls.objects.prefetch_related("permissions").get(
                    code=role_code, is_active=True
                )
                permissions = role.get_permission_codes()
                cache.set(cache_key, permissions, 300)  # 5 min cache
            except cls.DoesNotExist:
                permissions = set()

        return permissions

    @classmethod
    def get_permissions_for_roles(cls, role_codes: list) -> set:
        """
        Get combined permission codes for multiple roles.
        """
        all_permissions = set()
        for role_code in role_codes:
            all_permissions |= cls.get_permissions_for_role(role_code)
        return all_permissions

    @classmethod
    def clear_permission_cache(cls, role_code: str = None):
        """Clear permission cache for a role or all roles."""
        if role_code:
            cache.delete(f"role_permissions:{role_code}")
        else:
            # Clear all role caches
            for role in cls.objects.values_list("code", flat=True):
                cache.delete(f"role_permissions:{role}")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Clear cache on save
        self.clear_permission_cache(self.code)


# =============================================================================
# System Permissions Registry
# =============================================================================

SYSTEM_PERMISSIONS = [
    # Assets Module
    ("assets.view", "View Assets", "assets", "View asset hierarchy and device details"),
    (
        "assets.create",
        "Create Assets",
        "assets",
        "Create new plants, areas, lines, cells, devices",
    ),
    ("assets.update", "Update Assets", "assets", "Update existing assets"),
    ("assets.delete", "Delete Assets", "assets", "Delete assets"),
    (
        "assets.manage_maintenance",
        "Manage Maintenance",
        "assets",
        "Create and manage maintenance records",
    ),
    # Alerts Module
    ("alerts.view", "View Alerts", "alerts", "View active alerts and history"),
    ("alerts.acknowledge", "Acknowledge Alerts", "alerts", "Acknowledge active alerts"),
    ("alerts.resolve", "Resolve Alerts", "alerts", "Resolve alerts"),
    ("alerts.create_rule", "Create Alert Rules", "alerts", "Create new alert rules"),
    (
        "alerts.update_rule",
        "Update Alert Rules",
        "alerts",
        "Modify existing alert rules",
    ),
    ("alerts.delete_rule", "Delete Alert Rules", "alerts", "Delete alert rules"),
    # Telemetry Module
    ("telemetry.view", "View Telemetry", "telemetry", "View telemetry data and charts"),
    (
        "telemetry.view_raw",
        "View Raw Telemetry",
        "telemetry",
        "View raw telemetry data",
    ),
    (
        "telemetry.export",
        "Export Telemetry",
        "telemetry",
        "Export telemetry data to files",
    ),
    (
        "telemetry.manage_retention",
        "Manage Retention",
        "telemetry",
        "Configure data retention policies",
    ),
    # Simulator Module
    ("simulator.view", "View Simulator", "simulator", "View simulation status"),
    ("simulator.control", "Control Simulator", "simulator", "Start/stop simulations"),
    (
        "simulator.inject_faults",
        "Inject Faults",
        "simulator",
        "Inject device faults for testing",
    ),
    (
        "simulator.manage_profiles",
        "Manage Profiles",
        "simulator",
        "Create and modify device profiles",
    ),
    # Admin Module
    ("admin.view_users", "View Users", "admin", "View user list"),
    ("admin.manage_users", "Manage Users", "admin", "Create, update, delete users"),
    ("admin.view_roles", "View Roles", "admin", "View roles and permissions"),
    ("admin.manage_roles", "Manage Roles", "admin", "Create and modify roles"),
    ("admin.view_audit", "View Audit Logs", "admin", "View audit trail"),
    ("admin.system_config", "System Configuration", "admin", "Modify system settings"),
    # Audit Module
    ("audit.view", "View Audit Logs", "audit", "View audit logs"),
    ("audit.export", "Export Audit Logs", "audit", "Export audit logs"),
]

# Default role definitions
DEFAULT_ROLES = {
    "FACTORY_ADMIN": {
        "name": "Factory Administrator",
        "description": "Full access to all system functions",
        "permissions": "*",  # All permissions
        "is_system": True,
    },
    "PLANT_OPERATOR": {
        "name": "Plant Operator",
        "description": "Operate plant equipment, manage alerts",
        "permissions": [
            "assets.view",
            "assets.manage_maintenance",
            "alerts.view",
            "alerts.acknowledge",
            "alerts.resolve",
            "telemetry.view",
            "telemetry.view_raw",
            "simulator.view",
            "audit.view",
        ],
        "is_system": True,
    },
    "TECHNICIAN": {
        "name": "Technician",
        "description": "View assigned area, acknowledge alerts",
        "permissions": [
            "assets.view",
            "alerts.view",
            "alerts.acknowledge",
            "telemetry.view",
            "simulator.view",
        ],
        "is_system": True,
    },
    "VIEWER": {
        "name": "Viewer",
        "description": "Read-only access to dashboards",
        "permissions": [
            "assets.view",
            "alerts.view",
            "telemetry.view",
        ],
        "is_system": True,
    },
}
