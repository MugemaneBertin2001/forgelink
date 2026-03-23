import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';

/// Alert model
class Alert {
  final String id;
  final String deviceId;
  final String deviceName;
  final String alertType;
  final String severity;
  final String message;
  final String status;
  final double? value;
  final double? threshold;
  final String? unit;
  final DateTime triggeredAt;
  final DateTime? acknowledgedAt;
  final String? acknowledgedBy;
  final DateTime? resolvedAt;
  final String? resolvedBy;

  Alert({
    required this.id,
    required this.deviceId,
    required this.deviceName,
    required this.alertType,
    required this.severity,
    required this.message,
    required this.status,
    this.value,
    this.threshold,
    this.unit,
    required this.triggeredAt,
    this.acknowledgedAt,
    this.acknowledgedBy,
    this.resolvedAt,
    this.resolvedBy,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      id: json['id']?.toString() ?? '',
      deviceId: json['device']?['device_id'] ?? json['device_id'] ?? '',
      deviceName: json['device']?['name'] ?? json['device_name'] ?? '',
      alertType: json['alert_type'] ?? '',
      severity: json['severity'] ?? 'medium',
      message: json['message'] ?? '',
      status: json['status'] ?? 'active',
      value: json['value']?.toDouble(),
      threshold: json['threshold']?.toDouble(),
      unit: json['unit'],
      triggeredAt: DateTime.parse(json['triggered_at'] ?? DateTime.now().toIso8601String()),
      acknowledgedAt: json['acknowledged_at'] != null
          ? DateTime.parse(json['acknowledged_at'])
          : null,
      acknowledgedBy: json['acknowledged_by'],
      resolvedAt: json['resolved_at'] != null
          ? DateTime.parse(json['resolved_at'])
          : null,
      resolvedBy: json['resolved_by'],
    );
  }

  bool get isActive => status == 'active';
  bool get isAcknowledged => status == 'acknowledged';
  bool get isResolved => status == 'resolved';

  int get durationSeconds {
    final end = resolvedAt ?? DateTime.now();
    return end.difference(triggeredAt).inSeconds;
  }
}

/// Alert statistics model
class AlertStats {
  final int totalActive;
  final int totalAcknowledged;
  final int totalResolved;
  final Map<String, int> bySeverity;
  final Map<String, int> byArea;

  AlertStats({
    required this.totalActive,
    required this.totalAcknowledged,
    required this.totalResolved,
    required this.bySeverity,
    required this.byArea,
  });

  factory AlertStats.fromJson(Map<String, dynamic> json) {
    return AlertStats(
      totalActive: json['total_active'] ?? 0,
      totalAcknowledged: json['total_acknowledged'] ?? 0,
      totalResolved: json['total_resolved'] ?? 0,
      bySeverity: Map<String, int>.from(json['by_severity'] ?? {}),
      byArea: Map<String, int>.from(json['by_area'] ?? {}),
    );
  }

  factory AlertStats.empty() {
    return AlertStats(
      totalActive: 0,
      totalAcknowledged: 0,
      totalResolved: 0,
      bySeverity: {},
      byArea: {},
    );
  }
}

/// Alerts state
class AlertsState {
  final List<Alert> alerts;
  final bool isLoading;
  final String? error;
  final AlertStats stats;

  AlertsState({
    this.alerts = const [],
    this.isLoading = false,
    this.error,
    AlertStats? stats,
  }) : stats = stats ?? AlertStats.empty();

  AlertsState copyWith({
    List<Alert>? alerts,
    bool? isLoading,
    String? error,
    AlertStats? stats,
  }) {
    return AlertsState(
      alerts: alerts ?? this.alerts,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      stats: stats ?? this.stats,
    );
  }

  List<Alert> get activeAlerts =>
      alerts.where((a) => a.status == 'active').toList();

  List<Alert> get acknowledgedAlerts =>
      alerts.where((a) => a.status == 'acknowledged').toList();

  List<Alert> get resolvedAlerts =>
      alerts.where((a) => a.status == 'resolved').toList();
}

/// Alerts service notifier
class AlertsNotifier extends StateNotifier<AlertsState> {
  final Dio _dio;

  AlertsNotifier(this._dio) : super(AlertsState());

  /// Fetch all alerts
  Future<void> fetchAlerts({
    String? status,
    String? severity,
    String? area,
    int limit = 100,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
      };
      if (status != null) queryParams['status'] = status;
      if (severity != null) queryParams['severity'] = severity;
      if (area != null) queryParams['area'] = area;

      final response = await _dio.get(
        '/api/alerts/alerts/',
        queryParameters: queryParams,
      );

      final List<dynamic> data = response.data['results'] ?? response.data;
      final alerts = data.map((json) => Alert.fromJson(json)).toList();

      state = state.copyWith(alerts: alerts, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch alerts',
      );
    }
  }

  /// Fetch active alerts
  Future<void> fetchActiveAlerts({String? area, String? severity}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final queryParams = <String, dynamic>{};
      if (area != null) queryParams['area'] = area;
      if (severity != null) queryParams['severity'] = severity;

      final response = await _dio.get(
        '/api/alerts/alerts/active/',
        queryParameters: queryParams,
      );

      final List<dynamic> data = response.data['alerts'] ?? response.data;
      final alerts = data.map((json) => Alert.fromJson(json)).toList();

      state = state.copyWith(alerts: alerts, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch active alerts',
      );
    }
  }

  /// Fetch alert statistics
  Future<void> fetchStats({int hours = 24}) async {
    try {
      final response = await _dio.get(
        '/api/alerts/stats/',
        queryParameters: {'hours': hours},
      );

      final stats = AlertStats.fromJson(response.data);
      state = state.copyWith(stats: stats);
    } on DioException catch (e) {
      // Silent fail for stats - not critical
      print('Failed to fetch alert stats: ${e.message}');
    }
  }

  /// Acknowledge an alert
  Future<bool> acknowledgeAlert(String alertId) async {
    try {
      await _dio.post('/api/alerts/alerts/$alertId/acknowledge/');

      // Update local state
      final updatedAlerts = state.alerts.map((alert) {
        if (alert.id == alertId) {
          return Alert(
            id: alert.id,
            deviceId: alert.deviceId,
            deviceName: alert.deviceName,
            alertType: alert.alertType,
            severity: alert.severity,
            message: alert.message,
            status: 'acknowledged',
            value: alert.value,
            threshold: alert.threshold,
            unit: alert.unit,
            triggeredAt: alert.triggeredAt,
            acknowledgedAt: DateTime.now(),
            acknowledgedBy: 'current_user',
            resolvedAt: alert.resolvedAt,
            resolvedBy: alert.resolvedBy,
          );
        }
        return alert;
      }).toList();

      state = state.copyWith(alerts: updatedAlerts);
      return true;
    } on DioException catch (e) {
      state = state.copyWith(
        error: e.response?.data?['error'] ?? 'Failed to acknowledge alert',
      );
      return false;
    }
  }

  /// Resolve an alert
  Future<bool> resolveAlert(String alertId, {String? notes}) async {
    try {
      await _dio.post(
        '/api/alerts/alerts/$alertId/resolve/',
        data: notes != null ? {'notes': notes} : null,
      );

      // Update local state
      final updatedAlerts = state.alerts.map((alert) {
        if (alert.id == alertId) {
          return Alert(
            id: alert.id,
            deviceId: alert.deviceId,
            deviceName: alert.deviceName,
            alertType: alert.alertType,
            severity: alert.severity,
            message: alert.message,
            status: 'resolved',
            value: alert.value,
            threshold: alert.threshold,
            unit: alert.unit,
            triggeredAt: alert.triggeredAt,
            acknowledgedAt: alert.acknowledgedAt,
            acknowledgedBy: alert.acknowledgedBy,
            resolvedAt: DateTime.now(),
            resolvedBy: 'current_user',
          );
        }
        return alert;
      }).toList();

      state = state.copyWith(alerts: updatedAlerts);
      return true;
    } on DioException catch (e) {
      state = state.copyWith(
        error: e.response?.data?['error'] ?? 'Failed to resolve alert',
      );
      return false;
    }
  }

  /// Bulk acknowledge alerts
  Future<int> acknowledgeMultiple(List<String> alertIds) async {
    try {
      final response = await _dio.post(
        '/api/alerts/alerts/acknowledge_bulk/',
        data: {'alert_ids': alertIds},
      );

      final acknowledged = response.data['acknowledged'] ?? 0;

      // Refresh alerts
      await fetchAlerts();

      return acknowledged;
    } on DioException {
      return 0;
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Providers
final alertsProvider = StateNotifierProvider<AlertsNotifier, AlertsState>((ref) {
  final dio = ref.watch(apiClientProvider);
  return AlertsNotifier(dio);
});

final activeAlertsProvider = Provider<List<Alert>>((ref) {
  return ref.watch(alertsProvider).activeAlerts;
});

final acknowledgedAlertsProvider = Provider<List<Alert>>((ref) {
  return ref.watch(alertsProvider).acknowledgedAlerts;
});

final resolvedAlertsProvider = Provider<List<Alert>>((ref) {
  return ref.watch(alertsProvider).resolvedAlerts;
});

final alertStatsProvider = Provider<AlertStats>((ref) {
  return ref.watch(alertsProvider).stats;
});
