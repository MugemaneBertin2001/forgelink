import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';
import 'alerts_service.dart';

/// Area status
class AreaStatus {
  final String code;
  final String name;
  final int totalDevices;
  final int onlineDevices;
  final int offlineDevices;
  final int faultDevices;
  final int activeAlerts;

  AreaStatus({
    required this.code,
    required this.name,
    required this.totalDevices,
    required this.onlineDevices,
    required this.offlineDevices,
    required this.faultDevices,
    required this.activeAlerts,
  });

  factory AreaStatus.fromJson(Map<String, dynamic> json) {
    return AreaStatus(
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      totalDevices: json['total_devices'] ?? 0,
      onlineDevices: json['online'] ?? 0,
      offlineDevices: json['offline'] ?? 0,
      faultDevices: json['fault'] ?? 0,
      activeAlerts: json['active_alerts'] ?? 0,
    );
  }

  double get healthPercent {
    if (totalDevices == 0) return 100;
    return (onlineDevices / totalDevices) * 100;
  }

  String get statusLabel {
    if (faultDevices > 0) return 'Fault';
    if (offlineDevices > totalDevices / 2) return 'Degraded';
    if (onlineDevices == totalDevices) return 'Healthy';
    return 'Partial';
  }
}

/// Dashboard summary
class DashboardSummary {
  final int totalDevices;
  final int onlineDevices;
  final int offlineDevices;
  final int faultDevices;
  final int activeAlerts;
  final int criticalAlerts;
  final int highAlerts;
  final List<AreaStatus> areaStatuses;
  final List<Alert> recentAlerts;

  DashboardSummary({
    required this.totalDevices,
    required this.onlineDevices,
    required this.offlineDevices,
    required this.faultDevices,
    required this.activeAlerts,
    required this.criticalAlerts,
    required this.highAlerts,
    required this.areaStatuses,
    required this.recentAlerts,
  });

  factory DashboardSummary.empty() {
    return DashboardSummary(
      totalDevices: 0,
      onlineDevices: 0,
      offlineDevices: 0,
      faultDevices: 0,
      activeAlerts: 0,
      criticalAlerts: 0,
      highAlerts: 0,
      areaStatuses: [],
      recentAlerts: [],
    );
  }

  double get healthPercent {
    if (totalDevices == 0) return 100;
    return (onlineDevices / totalDevices) * 100;
  }
}

/// Dashboard state
class DashboardState {
  final DashboardSummary summary;
  final bool isLoading;
  final String? error;
  final DateTime? lastUpdated;

  DashboardState({
    DashboardSummary? summary,
    this.isLoading = false,
    this.error,
    this.lastUpdated,
  }) : summary = summary ?? DashboardSummary.empty();

  DashboardState copyWith({
    DashboardSummary? summary,
    bool? isLoading,
    String? error,
    DateTime? lastUpdated,
  }) {
    return DashboardState(
      summary: summary ?? this.summary,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }
}

/// Dashboard service notifier
class DashboardNotifier extends StateNotifier<DashboardState> {
  final Dio _dio;

  DashboardNotifier(this._dio) : super(DashboardState());

  /// Refresh all dashboard data
  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      // Fetch data in parallel
      final results = await Future.wait([
        _fetchAssetDashboard(),
        _fetchAlertStats(),
        _fetchActiveAlerts(),
        _fetchAreaStatuses(),
      ]);

      final assetData = results[0] as Map<String, dynamic>;
      final alertStats = results[1] as AlertStats;
      final recentAlerts = results[2] as List<Alert>;
      final areaStatuses = results[3] as List<AreaStatus>;

      final byStatus = assetData['by_status'] as Map<String, dynamic>? ?? {};

      final summary = DashboardSummary(
        totalDevices: assetData['summary']?['total_devices'] ?? 0,
        onlineDevices: byStatus['online'] ?? 0,
        offlineDevices: byStatus['offline'] ?? 0,
        faultDevices: byStatus['fault'] ?? 0,
        activeAlerts: alertStats.totalActive,
        criticalAlerts: alertStats.bySeverity['critical'] ?? 0,
        highAlerts: alertStats.bySeverity['high'] ?? 0,
        areaStatuses: areaStatuses,
        recentAlerts: recentAlerts,
      );

      state = state.copyWith(
        summary: summary,
        isLoading: false,
        lastUpdated: DateTime.now(),
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load dashboard data',
      );
    }
  }

  Future<Map<String, dynamic>> _fetchAssetDashboard() async {
    try {
      final response = await _dio.get('/api/assets/dashboard/');
      return response.data;
    } catch (e) {
      return {};
    }
  }

  Future<AlertStats> _fetchAlertStats() async {
    try {
      final response = await _dio.get('/api/alerts/stats/');
      return AlertStats.fromJson(response.data);
    } catch (e) {
      return AlertStats.empty();
    }
  }

  Future<List<Alert>> _fetchActiveAlerts() async {
    try {
      final response = await _dio.get(
        '/api/alerts/alerts/active/',
        queryParameters: {'limit': 5},
      );
      final List<dynamic> data = response.data['alerts'] ?? response.data;
      return data.map((json) => Alert.fromJson(json)).toList();
    } catch (e) {
      return [];
    }
  }

  Future<List<AreaStatus>> _fetchAreaStatuses() async {
    try {
      final response = await _dio.get('/api/assets/dashboard/');
      final List<dynamic> areas = response.data['areas'] ?? [];
      return areas.map((json) => AreaStatus.fromJson(json)).toList();
    } catch (e) {
      return [];
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Providers
final dashboardProvider = StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
  final dio = ref.watch(apiClientProvider);
  return DashboardNotifier(dio);
});

final dashboardSummaryProvider = Provider<DashboardSummary>((ref) {
  return ref.watch(dashboardProvider).summary;
});

final areaStatusesProvider = Provider<List<AreaStatus>>((ref) {
  return ref.watch(dashboardProvider).summary.areaStatuses;
});

final recentAlertsProvider = Provider<List<Alert>>((ref) {
  return ref.watch(dashboardProvider).summary.recentAlerts;
});
