"""
Django Unfold Admin for RBAC.

Allows factory admins to:
- View all permissions (read-only, system-defined)
- Create custom roles by combining permissions
- Modify existing custom roles
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter

from .models import Permission, Role


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    """
    Permission admin (read-only).

    Permissions are system-defined and cannot be modified via admin.
    They are created via migrations when new features are added.
    """

    list_display = ['code', 'name', 'module', 'description_short']
    list_filter = ['module']
    search_fields = ['code', 'name', 'description']
    ordering = ['module', 'sort_order', 'code']

    # Permissions are read-only
    readonly_fields = ['id', 'code', 'name', 'description', 'module', 'sort_order']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Description')
    def description_short(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    """
    Role admin for creating and managing roles.

    Factory admins can:
    - Create custom roles
    - Assign permissions to roles
    - Cannot delete system roles
    """

    list_display = ['code', 'name', 'permission_count', 'is_system', 'is_active', 'updated_at']
    list_filter = ['is_system', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['name']

    readonly_fields = ['id', 'created_at', 'updated_at']

    filter_horizontal = ['permissions']

    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'description')
        }),
        ('Permissions', {
            'fields': ('permissions',),
            'description': 'Select permissions granted by this role'
        }),
        ('Status', {
            'fields': ('is_active', 'is_system')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # Cannot delete system roles
        if obj and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.is_system:
            # System roles cannot have their code changed
            readonly.append('code')
            readonly.append('is_system')
        return readonly

    @admin.display(description='Permissions')
    def permission_count(self, obj):
        count = obj.permissions.count()
        return f"{count} permissions"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Clear permission cache
        Role.clear_permission_cache(obj.code)
