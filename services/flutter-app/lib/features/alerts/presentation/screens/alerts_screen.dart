import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timeago/timeago.dart' as timeago;
import '../../../../core/theme/app_theme.dart';
import '../../../../core/auth/auth_service.dart';
import '../../../../core/api/socket_service.dart';
import '../../../../core/services/alerts_service.dart';

class AlertsScreen extends ConsumerStatefulWidget {
  const AlertsScreen({super.key});

  @override
  ConsumerState<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends ConsumerState<AlertsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String _selectedSeverity = 'all';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    // Fetch alerts on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(alertsProvider.notifier).fetchAlerts();
      ref.read(alertsProvider.notifier).fetchStats();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final canAcknowledge = user?.hasPermission('alerts.acknowledge') ?? false;
    final canResolve = user?.hasPermission('alerts.resolve') ?? false;
    final alertsState = ref.watch(alertsProvider);

    // Listen to real-time alerts
    ref.listen(alertStreamProvider, (prev, next) {
      next.whenData((alert) {
        // Refresh alerts when new one arrives
        ref.read(alertsProvider.notifier).fetchAlerts();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('New alert: ${alert.message}'),
            backgroundColor: AppColors.severityColor(alert.severity),
            action: SnackBarAction(
              label: 'View',
              textColor: Colors.white,
              onPressed: () {
                _tabController.animateTo(0); // Go to active tab
              },
            ),
          ),
        );
      });
    });

    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          tabs: [
            Tab(text: 'Active (${alertsState.activeAlerts.length})'),
            Tab(text: 'Acknowledged (${alertsState.acknowledgedAlerts.length})'),
            const Tab(text: 'History'),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list),
            onSelected: (value) {
              setState(() => _selectedSeverity = value);
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'all', child: Text('All')),
              const PopupMenuItem(value: 'critical', child: Text('Critical')),
              const PopupMenuItem(value: 'high', child: Text('High')),
              const PopupMenuItem(value: 'medium', child: Text('Medium')),
              const PopupMenuItem(value: 'low', child: Text('Low')),
            ],
          ),
        ],
      ),
      body: alertsState.isLoading && alertsState.alerts.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : alertsState.error != null && alertsState.alerts.isEmpty
              ? _ErrorView(
                  error: alertsState.error!,
                  onRetry: () => ref.read(alertsProvider.notifier).fetchAlerts(),
                )
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _AlertList(
                      alerts: _filterBySeverity(alertsState.activeAlerts),
                      status: 'active',
                      canAcknowledge: canAcknowledge,
                      canResolve: canResolve,
                      onRefresh: () => ref.read(alertsProvider.notifier).fetchActiveAlerts(),
                      onAcknowledge: (id) => _acknowledgeAlert(id),
                      onResolve: (id) => _resolveAlert(id),
                    ),
                    _AlertList(
                      alerts: _filterBySeverity(alertsState.acknowledgedAlerts),
                      status: 'acknowledged',
                      canResolve: canResolve,
                      onRefresh: () => ref.read(alertsProvider.notifier).fetchAlerts(),
                      onResolve: (id) => _resolveAlert(id),
                    ),
                    _AlertList(
                      alerts: _filterBySeverity(alertsState.resolvedAlerts),
                      status: 'resolved',
                      isHistory: true,
                      onRefresh: () => ref.read(alertsProvider.notifier).fetchAlerts(status: 'resolved'),
                    ),
                  ],
                ),
    );
  }

  List<Alert> _filterBySeverity(List<Alert> alerts) {
    if (_selectedSeverity == 'all') return alerts;
    return alerts.where((a) => a.severity == _selectedSeverity).toList();
  }

  Future<void> _acknowledgeAlert(String alertId) async {
    final success = await ref.read(alertsProvider.notifier).acknowledgeAlert(alertId);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? 'Alert acknowledged' : 'Failed to acknowledge'),
        backgroundColor: success ? AppColors.success : AppColors.critical,
      ),
    );
  }

  Future<void> _resolveAlert(String alertId) async {
    final notes = await _showResolveDialog();
    if (notes == null) return;

    final success = await ref.read(alertsProvider.notifier).resolveAlert(
      alertId,
      notes: notes.isEmpty ? null : notes,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? 'Alert resolved' : 'Failed to resolve'),
        backgroundColor: success ? AppColors.success : AppColors.critical,
      ),
    );
  }

  Future<String?> _showResolveDialog() async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Resolve Alert'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Notes (optional)',
            hintText: 'Enter resolution notes...',
          ),
          maxLines: 3,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Resolve'),
          ),
        ],
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

class _AlertList extends StatelessWidget {
  final List<Alert> alerts;
  final String status;
  final bool canAcknowledge;
  final bool canResolve;
  final bool isHistory;
  final Future<void> Function() onRefresh;
  final Function(String)? onAcknowledge;
  final Function(String)? onResolve;

  const _AlertList({
    required this.alerts,
    required this.status,
    this.canAcknowledge = false,
    this.canResolve = false,
    this.isHistory = false,
    required this.onRefresh,
    this.onAcknowledge,
    this.onResolve,
  });

  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.check_circle_outline,
              size: 64,
              color: AppColors.success.withOpacity(0.5),
            ),
            const SizedBox(height: 16),
            Text(
              'No $status alerts',
              style: AppTypography.subtitle1.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView.builder(
        padding: const EdgeInsets.all(8),
        itemCount: alerts.length,
        itemBuilder: (context, index) {
          final alert = alerts[index];
          return _AlertCard(
            alert: alert,
            canAcknowledge: canAcknowledge && status == 'active',
            canResolve: canResolve && status != 'resolved',
            onAcknowledge: onAcknowledge,
            onResolve: onResolve,
          );
        },
      ),
    );
  }
}

class _AlertCard extends StatelessWidget {
  final Alert alert;
  final bool canAcknowledge;
  final bool canResolve;
  final Function(String)? onAcknowledge;
  final Function(String)? onResolve;

  const _AlertCard({
    required this.alert,
    this.canAcknowledge = false,
    this.canResolve = false,
    this.onAcknowledge,
    this.onResolve,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppColors.severityColor(alert.severity);

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        onTap: () {
          _showAlertDetail(context);
        },
        borderRadius: BorderRadius.circular(12),
        child: Column(
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(12),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      alert.severity.toUpperCase(),
                      style: AppTypography.caption.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      alert.alertType,
                      style: AppTypography.caption.copyWith(
                        fontSize: 10,
                      ),
                    ),
                  ),
                  const Spacer(),
                  Text(
                    timeago.format(alert.triggeredAt),
                    style: AppTypography.caption.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),

            // Body
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    alert.message,
                    style: AppTypography.body2,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(
                        Icons.sensors,
                        size: 14,
                        color: AppColors.textSecondary,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        alert.deviceName.isNotEmpty ? alert.deviceName : alert.deviceId,
                        style: AppTypography.caption.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(width: 16),
                      if (alert.value != null) ...[
                        Text(
                          '${alert.value!.toStringAsFixed(1)} ${alert.unit ?? ''}',
                          style: AppTypography.caption.copyWith(
                            color: color,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (alert.threshold != null)
                          Text(
                            ' / ${alert.threshold!.toStringAsFixed(1)} ${alert.unit ?? ''}',
                            style: AppTypography.caption.copyWith(
                              color: AppColors.textSecondary,
                            ),
                          ),
                      ],
                    ],
                  ),
                  if (alert.acknowledgedAt != null) ...[
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(Icons.check, size: 14, color: AppColors.success),
                        const SizedBox(width: 4),
                        Text(
                          'Acknowledged ${timeago.format(alert.acknowledgedAt!)}',
                          style: AppTypography.caption.copyWith(color: AppColors.success),
                        ),
                      ],
                    ),
                  ],
                  if (alert.resolvedAt != null) ...[
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.done_all, size: 14, color: AppColors.primary),
                        const SizedBox(width: 4),
                        Text(
                          'Resolved ${timeago.format(alert.resolvedAt!)}',
                          style: AppTypography.caption.copyWith(color: AppColors.primary),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),

            // Actions
            if (canAcknowledge || canResolve)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  border: Border(
                    top: BorderSide(color: Colors.grey.shade200),
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    if (canAcknowledge && onAcknowledge != null)
                      TextButton.icon(
                        onPressed: () => onAcknowledge!(alert.id),
                        icon: const Icon(Icons.check, size: 18),
                        label: const Text('Acknowledge'),
                      ),
                    if (canResolve && onResolve != null)
                      TextButton.icon(
                        onPressed: () => onResolve!(alert.id),
                        icon: const Icon(Icons.done_all, size: 18),
                        label: const Text('Resolve'),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  void _showAlertDetail(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text('Alert Details', style: AppTypography.headline3),
              const SizedBox(height: 16),
              _DetailRow('Status', alert.status.toUpperCase()),
              _DetailRow('Severity', alert.severity.toUpperCase()),
              _DetailRow('Type', alert.alertType),
              _DetailRow('Device', alert.deviceName.isNotEmpty ? alert.deviceName : alert.deviceId),
              _DetailRow('Device ID', alert.deviceId),
              const Divider(),
              _DetailRow('Message', alert.message),
              if (alert.value != null)
                _DetailRow('Value', '${alert.value!.toStringAsFixed(2)} ${alert.unit ?? ''}'),
              if (alert.threshold != null)
                _DetailRow('Threshold', '${alert.threshold!.toStringAsFixed(2)} ${alert.unit ?? ''}'),
              const Divider(),
              _DetailRow('Triggered', alert.triggeredAt.toLocal().toString()),
              if (alert.acknowledgedAt != null) ...[
                _DetailRow('Acknowledged', alert.acknowledgedAt!.toLocal().toString()),
                if (alert.acknowledgedBy != null)
                  _DetailRow('Acknowledged By', alert.acknowledgedBy!),
              ],
              if (alert.resolvedAt != null) ...[
                _DetailRow('Resolved', alert.resolvedAt!.toLocal().toString()),
                if (alert.resolvedBy != null)
                  _DetailRow('Resolved By', alert.resolvedBy!),
              ],
              _DetailRow('Duration', _formatDuration(alert.durationSeconds)),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDuration(int seconds) {
    if (seconds < 60) return '${seconds}s';
    if (seconds < 3600) return '${seconds ~/ 60}m ${seconds % 60}s';
    final hours = seconds ~/ 3600;
    final mins = (seconds % 3600) ~/ 60;
    return '${hours}h ${mins}m';
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: AppTypography.caption.copyWith(color: AppColors.textSecondary),
            ),
          ),
          Expanded(
            child: Text(value, style: AppTypography.body2),
          ),
        ],
      ),
    );
  }
}
