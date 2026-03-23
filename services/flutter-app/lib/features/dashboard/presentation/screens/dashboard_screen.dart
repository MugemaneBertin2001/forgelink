import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/auth/auth_service.dart';
import '../../../../core/api/socket_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/config/router.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final socketStatus = ref.watch(socketStatusProvider);
    // Watch alert stream to trigger rebuilds on new alerts
    ref.watch(alertStreamProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          // Connection indicator
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Icon(
              socketStatus == SocketStatus.connected
                  ? Icons.cloud_done
                  : Icons.cloud_off,
              color: socketStatus == SocketStatus.connected
                  ? Colors.green
                  : Colors.grey,
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          // TODO: Refresh dashboard data
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Welcome card
            _WelcomeCard(user: user),
            const SizedBox(height: 16),

            // Alert summary
            _AlertSummaryCard(),
            const SizedBox(height: 16),

            // Quick stats grid
            _QuickStatsGrid(),
            const SizedBox(height: 16),

            // Recent alerts
            _RecentAlertsCard(),
            const SizedBox(height: 16),

            // Area overview
            _AreaOverviewCard(),
          ],
        ),
      ),
    );
  }
}

class _WelcomeCard extends StatelessWidget {
  final AuthUser? user;

  const _WelcomeCard({this.user});

  @override
  Widget build(BuildContext context) {
    final greeting = _getGreeting();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: AppColors.primary,
              child: Text(
                user?.email.substring(0, 1).toUpperCase() ?? '?',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 24,
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
                    '$greeting!',
                    style: AppTypography.headline3,
                  ),
                  Text(
                    user?.email ?? '',
                    style: AppTypography.body2.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 2,
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
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }
}

class _AlertSummaryCard extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // TODO: Fetch from API
    return Card(
      color: AppColors.critical.withOpacity(0.1),
      child: InkWell(
        onTap: () => context.go(AppRoutes.alerts),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.critical,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.warning_amber_rounded,
                  color: Colors.white,
                  size: 28,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '3 Active Alerts',
                      style: AppTypography.subtitle1.copyWith(
                        color: AppColors.critical,
                      ),
                    ),
                    Text(
                      '1 critical, 2 high severity',
                      style: AppTypography.body2.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.chevron_right,
                color: AppColors.critical,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuickStatsGrid extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.5,
      children: [
        _StatCard(
          title: 'Devices Online',
          value: '65',
          total: '68',
          icon: Icons.sensors,
          color: AppColors.success,
        ),
        _StatCard(
          title: 'Areas Active',
          value: '4',
          total: '4',
          icon: Icons.location_on,
          color: AppColors.primary,
        ),
        _StatCard(
          title: 'Data Points/sec',
          value: '1,240',
          icon: Icons.speed,
          color: AppColors.chartBlue,
        ),
        _StatCard(
          title: 'Alerts Today',
          value: '12',
          icon: Icons.notifications,
          color: AppColors.warning,
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final String? total;
  final IconData icon;
  final Color color;

  const _StatCard({
    required this.title,
    required this.value,
    this.total,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(icon, color: color, size: 20),
                if (total != null)
                  Text(
                    '/ $total',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
              ],
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: AppTypography.headline2.copyWith(color: color),
                ),
                Text(
                  title,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RecentAlertsCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Recent Alerts', style: AppTypography.subtitle1),
                TextButton(
                  onPressed: () => context.go(AppRoutes.alerts),
                  child: const Text('View All'),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          // TODO: Fetch from API
          _AlertListItem(
            severity: 'critical',
            message: 'EAF-1 temperature exceeds threshold',
            device: 'temp-sensor-001',
            time: '2 min ago',
          ),
          _AlertListItem(
            severity: 'high',
            message: 'Cooling water flow deviation',
            device: 'flow-meter-003',
            time: '15 min ago',
          ),
          _AlertListItem(
            severity: 'high',
            message: 'Motor vibration spike detected',
            device: 'vib-sensor-007',
            time: '32 min ago',
          ),
        ],
      ),
    );
  }
}

class _AlertListItem extends StatelessWidget {
  final String severity;
  final String message;
  final String device;
  final String time;

  const _AlertListItem({
    required this.severity,
    required this.message,
    required this.device,
    required this.time,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppColors.severityColor(severity);

    return InkWell(
      onTap: () {
        // TODO: Navigate to alert detail
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 4,
              height: 40,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message,
                    style: AppTypography.body2,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '$device • $time',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              color: AppColors.textSecondary,
            ),
          ],
        ),
      ),
    );
  }
}

class _AreaOverviewCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text('Area Status', style: AppTypography.subtitle1),
          ),
          const Divider(height: 1),
          _AreaStatusItem(
            name: 'Melt Shop',
            devices: 18,
            alerts: 1,
            status: 'warning',
          ),
          _AreaStatusItem(
            name: 'Continuous Casting',
            devices: 15,
            alerts: 0,
            status: 'normal',
          ),
          _AreaStatusItem(
            name: 'Rolling Mill',
            devices: 22,
            alerts: 2,
            status: 'critical',
          ),
          _AreaStatusItem(
            name: 'Finishing',
            devices: 13,
            alerts: 0,
            status: 'normal',
          ),
        ],
      ),
    );
  }
}

class _AreaStatusItem extends StatelessWidget {
  final String name;
  final int devices;
  final int alerts;
  final String status;

  const _AreaStatusItem({
    required this.name,
    required this.devices,
    required this.alerts,
    required this.status,
  });

  @override
  Widget build(BuildContext context) {
    final color = status == 'critical'
        ? AppColors.critical
        : status == 'warning'
            ? AppColors.warning
            : AppColors.success;

    return InkWell(
      onTap: () => context.go(AppRoutes.assets),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(name, style: AppTypography.body2),
            ),
            Text(
              '$devices devices',
              style: AppTypography.caption.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(width: 8),
            if (alerts > 0)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '$alerts',
                  style: AppTypography.caption.copyWith(
                    color: color,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            const SizedBox(width: 8),
            Icon(
              Icons.chevron_right,
              color: AppColors.textSecondary,
              size: 20,
            ),
          ],
        ),
      ),
    );
  }
}
