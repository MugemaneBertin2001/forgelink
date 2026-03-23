import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/auth/auth_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/api/socket_service.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final socketStatus = ref.watch(socketStatusProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          // Profile section
          _ProfileSection(user: user),
          const Divider(),

          // Permissions section
          _PermissionsSection(user: user),
          const Divider(),

          // Connection status
          _ConnectionSection(status: socketStatus, ref: ref),
          const Divider(),

          // App info
          _AppInfoSection(),
          const Divider(),

          // Logout
          _LogoutSection(ref: ref),
        ],
      ),
    );
  }
}

class _ProfileSection extends StatelessWidget {
  final AuthUser? user;

  const _ProfileSection({this.user});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          CircleAvatar(
            radius: 36,
            backgroundColor: AppColors.primary,
            child: Text(
              user?.email.substring(0, 1).toUpperCase() ?? '?',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user?.email ?? 'Not logged in',
                  style: AppTypography.subtitle1,
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    user?.role ?? '',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (user?.areaCode != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Area: ${user!.areaCode}',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PermissionsSection extends StatelessWidget {
  final AuthUser? user;

  const _PermissionsSection({this.user});

  @override
  Widget build(BuildContext context) {
    if (user == null) return const SizedBox.shrink();

    final permissions = user!.permissions.toList()..sort();

    return ExpansionTile(
      leading: const Icon(Icons.security),
      title: const Text('Permissions'),
      subtitle: Text(
        '${permissions.length} permissions',
        style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
      ),
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: permissions.map((permission) {
              final parts = permission.split('.');
              final module = parts[0];
              final action = parts.length > 1 ? parts[1] : '';

              return Chip(
                label: Text(
                  '$module.$action',
                  style: AppTypography.caption,
                ),
                backgroundColor: _getModuleColor(module).withOpacity(0.1),
                side: BorderSide(color: _getModuleColor(module).withOpacity(0.3)),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }

  Color _getModuleColor(String module) {
    switch (module) {
      case 'assets':
        return AppColors.chartBlue;
      case 'alerts':
        return AppColors.chartOrange;
      case 'telemetry':
        return AppColors.chartGreen;
      case 'simulator':
        return AppColors.chartPurple;
      case 'admin':
        return AppColors.chartRed;
      default:
        return AppColors.textSecondary;
    }
  }
}

class _ConnectionSection extends StatelessWidget {
  final SocketStatus status;
  final WidgetRef ref;

  const _ConnectionSection({required this.status, required this.ref});

  @override
  Widget build(BuildContext context) {
    final (icon, color, text) = switch (status) {
      SocketStatus.connected => (
          Icons.cloud_done,
          AppColors.success,
          'Connected',
        ),
      SocketStatus.connecting => (
          Icons.sync,
          AppColors.warning,
          'Connecting...',
        ),
      SocketStatus.disconnected => (
          Icons.cloud_off,
          AppColors.textSecondary,
          'Disconnected',
        ),
      SocketStatus.error => (
          Icons.error_outline,
          AppColors.error,
          'Connection Error',
        ),
    };

    return ListTile(
      leading: Icon(icon, color: color),
      title: const Text('Real-time Connection'),
      subtitle: Text(
        text,
        style: AppTypography.caption.copyWith(color: color),
      ),
      trailing: status != SocketStatus.connected
          ? TextButton(
              onPressed: () {
                ref.read(socketServiceProvider.notifier).connect();
              },
              child: const Text('Reconnect'),
            )
          : null,
    );
  }
}

class _AppInfoSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ListTile(
          leading: const Icon(Icons.info_outline),
          title: const Text('App Version'),
          subtitle: const Text('1.0.0 (Build 1)'),
        ),
        ListTile(
          leading: const Icon(Icons.code),
          title: const Text('API Endpoint'),
          subtitle: Text(
            'http://localhost:8000',
            style: AppTypography.caption.copyWith(
              fontFamily: 'monospace',
            ),
          ),
        ),
        ListTile(
          leading: const Icon(Icons.schedule),
          title: const Text('Timezone'),
          subtitle: const Text('Africa/Kigali (CAT, UTC+2)'),
        ),
      ],
    );
  }
}

class _LogoutSection extends StatelessWidget {
  final WidgetRef ref;

  const _LogoutSection({required this.ref});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: ElevatedButton.icon(
        onPressed: () async {
          final confirmed = await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Logout'),
              content: const Text('Are you sure you want to logout?'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context, true),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.error,
                  ),
                  child: const Text('Logout'),
                ),
              ],
            ),
          );

          if (confirmed == true) {
            await ref.read(authServiceProvider.notifier).logout();
          }
        },
        icon: const Icon(Icons.logout),
        label: const Text('Logout'),
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.error,
          minimumSize: const Size(double.infinity, 48),
        ),
      ),
    );
  }
}
