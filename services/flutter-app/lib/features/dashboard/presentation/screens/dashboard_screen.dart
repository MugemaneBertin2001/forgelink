import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:timeago/timeago.dart' as timeago;
import '../../../../core/auth/auth_service.dart';
import '../../../../core/api/socket_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/config/router.dart';
import '../../../../core/services/dashboard_service.dart';
import '../../../../core/services/alerts_service.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(dashboardProvider.notifier).refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final socketStatus = ref.watch(socketStatusProvider);
    final dashboardState = ref.watch(dashboardProvider);

    // Listen to real-time alerts to refresh dashboard
    ref.listen(alertStreamProvider, (prev, next) {
      next.whenData((alert) {
        ref.read(dashboardProvider.notifier).refresh();
      });
    });

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          // Connection indicator
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Row(
              children: [
                Icon(
                  socketStatus == SocketStatus.connected
                      ? Icons.cloud_done
                      : Icons.cloud_off,
                  color: socketStatus == SocketStatus.connected
                      ? Colors.green
                      : Colors.grey,
                  size: 20,
                ),
                if (dashboardState.lastUpdated != null) ...[
                  const SizedBox(width: 4),
                  Text(
                    timeago.format(dashboardState.lastUpdated!),
                    style: AppTypography.caption.copyWith(color: Colors.white70),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
      body: dashboardState.isLoading && dashboardState.summary.totalDevices == 0
          ? const Center(child: CircularProgressIndicator())
          : dashboardState.error != null && dashboardState.summary.totalDevices == 0
              ? _ErrorView(
                  error: dashboardState.error!,
                  onRetry: () => ref.read(dashboardProvider.notifier).refresh(),
                )
              : RefreshIndicator(
                  onRefresh: () => ref.read(dashboardProvider.notifier).refresh(),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      // Welcome card
                      _WelcomeCard(user: user),
                      const SizedBox(height: 16),

                      // Alert summary
                      _AlertSummaryCard(summary: dashboardState.summary),
                      const SizedBox(height: 16),

                      // Quick stats grid
                      _QuickStatsGrid(summary: dashboardState.summary),
                      const SizedBox(height: 16),

                      // Recent alerts
                      _RecentAlertsCard(alerts: dashboardState.summary.recentAlerts),
                      const SizedBox(height: 16),

                      // Area overview
                      _AreaOverviewCard(areaStatuses: dashboardState.summary.areaStatuses),
                    ],
                  ),
                ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: AppColors.critical.withOpacity(0.5)),
          const SizedBox(height: 16),
          Text(error, style: AppTypography.body2.copyWith(color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
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

class _AlertSummaryCard extends StatelessWidget {
  final DashboardSummary summary;

  const _AlertSummaryCard({required this.summary});

  @override
  Widget build(BuildContext context) {
    final hasAlerts = summary.activeAlerts > 0;
    final color = summary.criticalAlerts > 0
        ? AppColors.critical
        : summary.highAlerts > 0
            ? AppColors.warning
            : AppColors.success;

    return Card(
      color: color.withOpacity(0.1),
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
                  color: color,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  hasAlerts ? Icons.warning_amber_rounded : Icons.check_circle_outline,
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
                      hasAlerts ? '${summary.activeAlerts} Active Alerts' : 'All Systems Healthy',
                      style: AppTypography.subtitle1.copyWith(
                        color: color,
                      ),
                    ),
                    Text(
                      hasAlerts
                          ? _buildAlertSummaryText(summary)
                          : 'No active alerts at this time',
                      style: AppTypography.body2.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: color,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _buildAlertSummaryText(DashboardSummary summary) {
    final parts = <String>[];
    if (summary.criticalAlerts > 0) {
      parts.add('${summary.criticalAlerts} critical');
    }
    if (summary.highAlerts > 0) {
      parts.add('${summary.highAlerts} high');
    }
    final other = summary.activeAlerts - summary.criticalAlerts - summary.highAlerts;
    if (other > 0) {
      parts.add('$other other');
    }
    return parts.join(', ') + ' severity';
  }
}

class _QuickStatsGrid extends StatelessWidget {
  final DashboardSummary summary;

  const _QuickStatsGrid({required this.summary});

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
          value: summary.onlineDevices.toString(),
          total: summary.totalDevices.toString(),
          icon: Icons.sensors,
          color: AppColors.success,
        ),
        _StatCard(
          title: 'Health Score',
          value: '${summary.healthPercent.toStringAsFixed(0)}%',
          icon: Icons.favorite,
          color: summary.healthPercent >= 90
              ? AppColors.success
              : summary.healthPercent >= 70
                  ? AppColors.warning
                  : AppColors.critical,
        ),
        _StatCard(
          title: 'Faults',
          value: summary.faultDevices.toString(),
          icon: Icons.error_outline,
          color: summary.faultDevices > 0 ? AppColors.critical : AppColors.success,
        ),
        _StatCard(
          title: 'Active Alerts',
          value: summary.activeAlerts.toString(),
          icon: Icons.notifications,
          color: summary.activeAlerts > 0 ? AppColors.warning : AppColors.success,
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
  final List<Alert> alerts;

  const _RecentAlertsCard({required this.alerts});

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
          if (alerts.isEmpty)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Center(
                child: Text(
                  'No recent alerts',
                  style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
                ),
              ),
            )
          else
            ...alerts.take(5).map((alert) => _AlertListItem(alert: alert)),
        ],
      ),
    );
  }
}

class _AlertListItem extends StatelessWidget {
  final Alert alert;

  const _AlertListItem({required this.alert});

  @override
  Widget build(BuildContext context) {
    final color = AppColors.severityColor(alert.severity);

    return InkWell(
      onTap: () => context.go(AppRoutes.alerts),
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
                    alert.message,
                    style: AppTypography.body2,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '${alert.deviceName.isNotEmpty ? alert.deviceName : alert.deviceId} • ${timeago.format(alert.triggeredAt)}',
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
  final List<AreaStatus> areaStatuses;

  const _AreaOverviewCard({required this.areaStatuses});

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
          if (areaStatuses.isEmpty)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Center(
                child: Text(
                  'No area data available',
                  style: AppTypography.body2.copyWith(color: AppColors.textSecondary),
                ),
              ),
            )
          else
            ...areaStatuses.map((area) => _AreaStatusItem(area: area)),
        ],
      ),
    );
  }
}

class _AreaStatusItem extends StatelessWidget {
  final AreaStatus area;

  const _AreaStatusItem({required this.area});

  @override
  Widget build(BuildContext context) {
    final color = area.faultDevices > 0
        ? AppColors.critical
        : area.offlineDevices > area.totalDevices / 2
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(area.name, style: AppTypography.body2),
                  Text(
                    '${area.onlineDevices}/${area.totalDevices} online • ${area.statusLabel}',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            if (area.activeAlerts > 0)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.warning.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.warning_amber, size: 12, color: AppColors.warning),
                    const SizedBox(width: 4),
                    Text(
                      '${area.activeAlerts}',
                      style: AppTypography.caption.copyWith(
                        color: AppColors.warning,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
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
