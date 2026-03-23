import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';

/// Telemetry data point
class TelemetryPoint {
  final DateTime timestamp;
  final double value;
  final int? quality;

  TelemetryPoint({
    required this.timestamp,
    required this.value,
    this.quality,
  });

  factory TelemetryPoint.fromJson(Map<String, dynamic> json) {
    return TelemetryPoint(
      timestamp: DateTime.parse(json['timestamp'] ?? json['ts']),
      value: (json['value'] ?? json['val'] ?? 0).toDouble(),
      quality: json['quality'],
    );
  }
}

/// Device latest value
class DeviceLatestValue {
  final String deviceId;
  final double value;
  final DateTime timestamp;
  final String unit;
  final String status;

  DeviceLatestValue({
    required this.deviceId,
    required this.value,
    required this.timestamp,
    required this.unit,
    required this.status,
  });

  factory DeviceLatestValue.fromJson(Map<String, dynamic> json) {
    return DeviceLatestValue(
      deviceId: json['device_id'] ?? '',
      value: (json['value'] ?? 0).toDouble(),
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
      unit: json['unit'] ?? '',
      status: json['status'] ?? 'normal',
    );
  }
}

/// Device statistics
class DeviceStats {
  final String deviceId;
  final double min;
  final double max;
  final double avg;
  final double stddev;
  final int count;
  final DateTime? startTime;
  final DateTime? endTime;

  DeviceStats({
    required this.deviceId,
    required this.min,
    required this.max,
    required this.avg,
    required this.stddev,
    required this.count,
    this.startTime,
    this.endTime,
  });

  factory DeviceStats.fromJson(Map<String, dynamic> json) {
    return DeviceStats(
      deviceId: json['device_id'] ?? '',
      min: (json['min'] ?? 0).toDouble(),
      max: (json['max'] ?? 0).toDouble(),
      avg: (json['avg'] ?? json['mean'] ?? 0).toDouble(),
      stddev: (json['stddev'] ?? json['std'] ?? 0).toDouble(),
      count: json['count'] ?? 0,
      startTime: json['start_time'] != null
          ? DateTime.parse(json['start_time'])
          : null,
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'])
          : null,
    );
  }

  factory DeviceStats.empty(String deviceId) {
    return DeviceStats(
      deviceId: deviceId,
      min: 0,
      max: 0,
      avg: 0,
      stddev: 0,
      count: 0,
    );
  }
}

/// Telemetry state
class TelemetryState {
  final List<TelemetryPoint> history;
  final DeviceLatestValue? latestValue;
  final DeviceStats? stats;
  final bool isLoading;
  final String? error;
  final String? selectedDeviceId;

  TelemetryState({
    this.history = const [],
    this.latestValue,
    this.stats,
    this.isLoading = false,
    this.error,
    this.selectedDeviceId,
  });

  TelemetryState copyWith({
    List<TelemetryPoint>? history,
    DeviceLatestValue? latestValue,
    DeviceStats? stats,
    bool? isLoading,
    String? error,
    String? selectedDeviceId,
  }) {
    return TelemetryState(
      history: history ?? this.history,
      latestValue: latestValue ?? this.latestValue,
      stats: stats ?? this.stats,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      selectedDeviceId: selectedDeviceId ?? this.selectedDeviceId,
    );
  }
}

/// Telemetry service notifier
class TelemetryNotifier extends StateNotifier<TelemetryState> {
  final Dio _dio;

  TelemetryNotifier(this._dio) : super(TelemetryState());

  /// Select a device
  void selectDevice(String deviceId) {
    state = state.copyWith(selectedDeviceId: deviceId);
  }

  /// Fetch device history
  Future<void> fetchHistory(
    String deviceId, {
    String interval = '1m',
    int hours = 24,
  }) async {
    state = state.copyWith(isLoading: true, error: null, selectedDeviceId: deviceId);

    try {
      final response = await _dio.get(
        '/api/telemetry/data/device/$deviceId/history/',
        queryParameters: {
          'interval': interval,
          'hours': hours,
        },
      );

      final List<dynamic> data = response.data['data'] ?? response.data;
      final history = data.map((json) => TelemetryPoint.fromJson(json)).toList();

      state = state.copyWith(history: history, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch history',
      );
    }
  }

  /// Fetch latest value
  Future<void> fetchLatest(String deviceId) async {
    try {
      final response = await _dio.get(
        '/api/telemetry/data/device/$deviceId/latest/',
      );

      final latest = DeviceLatestValue.fromJson(response.data);
      state = state.copyWith(latestValue: latest);
    } on DioException catch (e) {
      debugPrint('Failed to fetch latest: ${e.message}');
    }
  }

  /// Fetch device statistics
  Future<void> fetchStats(String deviceId, {int hours = 24}) async {
    try {
      final response = await _dio.get(
        '/api/telemetry/data/device/$deviceId/stats/',
        queryParameters: {'hours': hours},
      );

      final stats = DeviceStats.fromJson(response.data);
      state = state.copyWith(stats: stats);
    } on DioException catch (e) {
      debugPrint('Failed to fetch stats: ${e.message}');
    }
  }

  /// Fetch all data for a device
  Future<void> fetchDeviceData(String deviceId, {int hours = 24}) async {
    state = state.copyWith(isLoading: true, error: null, selectedDeviceId: deviceId);

    try {
      // Fetch all data in parallel
      await Future.wait([
        fetchHistory(deviceId, hours: hours),
        fetchLatest(deviceId),
        fetchStats(deviceId, hours: hours),
      ]);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to fetch device data',
      );
    }
  }

  /// Fetch latest values for multiple devices
  Future<Map<String, DeviceLatestValue>> fetchMultipleLatest(
    List<String> deviceIds,
  ) async {
    try {
      final response = await _dio.get(
        '/api/telemetry/data/latest/',
        queryParameters: {'device_ids': deviceIds.join(',')},
      );

      final Map<String, dynamic> data = response.data;
      return data.map((key, value) =>
          MapEntry(key, DeviceLatestValue.fromJson(value)));
    } on DioException {
      return {};
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Clear state
  void clear() {
    state = TelemetryState();
  }
}

/// Providers
final telemetryProvider = StateNotifierProvider<TelemetryNotifier, TelemetryState>((ref) {
  final dio = ref.watch(apiClientProvider);
  return TelemetryNotifier(dio);
});

final telemetryHistoryProvider = Provider<List<TelemetryPoint>>((ref) {
  return ref.watch(telemetryProvider).history;
});

final telemetryLatestProvider = Provider<DeviceLatestValue?>((ref) {
  return ref.watch(telemetryProvider).latestValue;
});

final telemetryStatsProvider = Provider<DeviceStats?>((ref) {
  return ref.watch(telemetryProvider).stats;
});

final selectedDeviceIdProvider = Provider<String?>((ref) {
  return ref.watch(telemetryProvider).selectedDeviceId;
});
