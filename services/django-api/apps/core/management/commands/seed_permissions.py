"""
Seed system permissions and default roles.

Run this after migrations to ensure all permissions and default roles exist.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import DEFAULT_ROLES, SYSTEM_PERMISSIONS, Permission, Role


class Command(BaseCommand):
    help = "Seed system permissions and default roles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset all permissions and roles (destructive)",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(
                self.style.WARNING("Resetting all permissions and roles...")
            )
            Permission.objects.all().delete()
            Role.objects.all().delete()

        with transaction.atomic():
            self._seed_permissions()
            self._seed_roles()

        # Clear all permission caches
        Role.clear_permission_cache()

        self.stdout.write(
            self.style.SUCCESS("Permissions and roles seeded successfully")
        )

    def _seed_permissions(self):
        """Create or update system permissions."""
        self.stdout.write("Seeding permissions...")

        created_count = 0
        updated_count = 0

        for idx, (code, name, module, description) in enumerate(SYSTEM_PERMISSIONS):
            permission, created = Permission.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "module": module,
                    "description": description,
                    "sort_order": idx,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(f"  + {code}")
            else:
                updated_count += 1

        self.stdout.write(
            f"  Permissions: {created_count} created, {updated_count} updated"
        )

    def _seed_roles(self):
        """Create or update default roles."""
        self.stdout.write("Seeding roles...")

        for role_code, config in DEFAULT_ROLES.items():
            role, created = Role.objects.update_or_create(
                code=role_code,
                defaults={
                    "name": config["name"],
                    "description": config["description"],
                    "is_system": config.get("is_system", False),
                    "is_active": True,
                },
            )

            # Set permissions
            if config["permissions"] == "*":
                # All permissions
                role_permissions = Permission.objects.all()
            else:
                role_permissions = Permission.objects.filter(
                    code__in=config["permissions"]
                )

            role.permissions.set(role_permissions)

            if created:
                self.stdout.write(
                    f"  + {role_code}: {role_permissions.count()} permissions"
                )
            else:
                self.stdout.write(
                    f"  ~ {role_code}: {role_permissions.count()} permissions"
                )

        self.stdout.write(f"  Roles: {len(DEFAULT_ROLES)} processed")
