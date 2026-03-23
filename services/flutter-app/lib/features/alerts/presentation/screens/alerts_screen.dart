import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timeago/timeago.dart' as timeago;
import '../../../../core/theme/app_theme.dart';
import '../../../../core/auth/auth_service.dart';
import '../../../../core/api/socket_service.dart';

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

    // Listen to real-time alerts
    ref.listen(alertStreamProvider, (prev, next) {
      next.whenData((alert) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('New alert: ${alert.message}'),
            backgroundColor: AppColors.severityColor(alert.severity),
            action: SnackBarAction(
              label: 'View',
              textColor: Colors.white,
              onPressed: () {
                // TODO: Navigate to alert detail
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
          tabs: const [
            Tab(text: 'Active'),
            Tab(text: 'Acknowledged'),
            Tab(text: 'History'),
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
      body: TabBarView(
        controller: _tabController,
        children: [
          _AlertList(
            status: 'active',
            severityFilter: _selectedSeverity,
            canAcknowledge: canAcknowledge,
            canResolve: canResolve,
          ),
          _AlertList(
            status: 'acknowledged',
            severityFilter: _selectedSeverity,
            canResolve: canResolve,
          ),
          _AlertList(
            status: 'resolved',
            severityFilter: _selectedSeverity,
            isHistory: true,
          ),
        ],
      ),
    );
  }
}

class _AlertList extends StatelessWidget {
  final String status;
  final String severityFilter;
  final bool canAcknowledge;
  final bool canResolve;
  final bool isHistory;

  const _AlertList({
    required this.status,
    required this.severityFilter,
    this.canAcknowledge = false,
    this.canResolve = false,
    this.isHistory = false,
  });

  @override
  Widget build(BuildContext context) {
    // TODO: Fetch from API with filters
    final alerts = _getMockAlerts(status);

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
      onRefresh: () async {
        // TODO: Refresh alerts
      },
      child: ListView.builder(
        padding: const EdgeInsets.all(8),
        itemCount: alerts.length,
        itemBuilder: (context, index) {
          final alert = alerts[index];
          return _AlertCard(
            alert: alert,
            canAcknowledge: canAcknowledge && status == 'active',
            canResolve: canResolve && status != 'resolved',
          );
        },
      ),
    );
  }

  List<Map<String, dynamic>> _getMockAlerts(String status) {
    if (status == 'active') {
      return [
        {
          'id': '1',
          'severity': 'critical',
          'message': 'EAF-1 temperature exceeds threshold: 1680°C',
          'device': 'temp-sensor-001',
          'area': 'Melt Shop',
          'value': 1680.0,
          'threshold': 1650.0,
          'unit': '°C',
          'triggeredAt': DateTime.now().subtract(const Duration(minutes: 2)),
        },
        {
          'id': '2',
          'severity': 'high',
          'message': 'Cooling water flow below minimum',
          'device': 'flow-meter-003',
          'area': 'Continuous Casting',
          'value': 85.0,
          'threshold': 100.0,
          'unit': 'L/min',
          'triggeredAt': DateTime.now().subtract(const Duration(minutes: 15)),
        },
        {
          'id': '3',
          'severity': 'high',
          'message': 'Motor vibration exceeds threshold',
          'device': 'vib-sensor-007',
          'area': 'Rolling Mill',
          'value': 5.2,
          'threshold': 4.5,
          'unit': 'mm/s',
          'triggeredAt': DateTime.now().subtract(const Duration(minutes: 32)),
        },
      ];
    }
    return [];
  }
}

class _AlertCard extends StatelessWidget {
  final Map<String, dynamic> alert;
  final bool canAcknowledge;
  final bool canResolve;

  const _AlertCard({
    required this.alert,
    this.canAcknowledge = false,
    this.canResolve = false,
  });

  @override
  Widget build(BuildContext context) {
    final severity = alert['severity'] as String;
    final color = AppColors.severityColor(severity);
    final triggeredAt = alert['triggeredAt'] as DateTime;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        onTap: () {
          // TODO: Navigate to alert detail
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
                      severity.toUpperCase(),
                      style: AppTypography.caption.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      alert['area'] as String,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                  Text(
                    timeago.format(triggeredAt),
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
                    alert['message'] as String,
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
                        alert['device'] as String,
                        style: AppTypography.caption.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(width: 16),
                      if (alert['value'] != null) ...[
                        Text(
                          '${alert['value']} ${alert['unit']}',
                          style: AppTypography.caption.copyWith(
                            color: color,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          ' / ${alert['threshold']} ${alert['unit']}',
                          style: AppTypography.caption.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ],
                  ),
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
                    if (canAcknowledge)
                      TextButton.icon(
                        onPressed: () {
                          // TODO: Acknowledge alert
                        },
                        icon: const Icon(Icons.check, size: 18),
                        label: const Text('Acknowledge'),
                      ),
                    if (canResolve)
                      TextButton.icon(
                        onPressed: () {
                          // TODO: Resolve alert
                        },
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
}
