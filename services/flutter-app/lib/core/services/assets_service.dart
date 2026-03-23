import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';

/// Plant model
class Plant {
  final String id;
  final String code;
  final String name;
  final String? description;
  final String timezone;
  final bool isActive;
  final List<Area> areas;

  Plant({
    required this.id,
    required this.code,
    required this.name,
    this.description,
    required this.timezone,
    required this.isActive,
    this.areas = const [],
  });

  factory Plant.fromJson(Map<String, dynamic> json) {
    return Plant(
      id: json['id']?.toString() ?? '',
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      timezone: json['timezone'] ?? 'Africa/Kigali',
      isActive: json['is_active'] ?? true,
      areas: (json['areas'] as List<dynamic>?)
              ?.map((a) => Area.fromJson(a))
              .toList() ??
          [],
    );
  }
}

/// Area model
class Area {
  final String id;
  final String code;
  final String name;
  final String? description;
  final String areaType;
  final int sequence;
  final bool isActive;
  final List<Line> lines;

  Area({
    required this.id,
    required this.code,
    required this.name,
    this.description,
    required this.areaType,
    required this.sequence,
    required this.isActive,
    this.lines = const [],
  });

  factory Area.fromJson(Map<String, dynamic> json) {
    return Area(
      id: json['id']?.toString() ?? '',
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      areaType: json['area_type'] ?? 'primary',
      sequence: json['sequence'] ?? 0,
      isActive: json['is_active'] ?? true,
      lines: (json['lines'] as List<dynamic>?)
              ?.map((l) => Line.fromJson(l))
              .toList() ??
          [],
    );
  }
}

/// Line model
class Line {
  final String id;
  final String code;
  final String name;
  final String? description;
  final bool isActive;
  final List<Cell> cells;

  Line({
    required this.id,
    required this.code,
    required this.name,
    this.description,
    required this.isActive,
    this.cells = const [],
  });

  factory Line.fromJson(Map<String, dynamic> json) {
    return Line(
      id: json['id']?.toString() ?? '',
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      isActive: json['is_active'] ?? true,
      cells: (json['cells'] as List<dynamic>?)
              ?.map((c) => Cell.fromJson(c))
              .toList() ??
          [],
    );
  }
}

/// Cell model
class Cell {
  final String id;
  final String code;
  final String name;
  final String? description;
  final bool isActive;
  final List<Device> devices;

  Cell({
    required this.id,
    required this.code,
    required this.name,
    this.description,
    required this.isActive,
    this.devices = const [],
  });

  factory Cell.fromJson(Map<String, dynamic> json) {
    return Cell(
      id: json['id']?.toString() ?? '',
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      isActive: json['is_active'] ?? true,
      devices: (json['devices'] as List<dynamic>?)
              ?.map((d) => Device.fromJson(d))
              .toList() ??
          [],
    );
  }
}

/// Device model
class Device {
  final String id;
  final String deviceId;
  final String name;
  final String? description;
  final String deviceType;
  final String status;
  final String unit;
  final double? warningLow;
  final double? warningHigh;
  final double? criticalLow;
  final double? criticalHigh;
  final DateTime? lastSeen;
  final bool isActive;

  Device({
    required this.id,
    required this.deviceId,
    required this.name,
    this.description,
    required this.deviceType,
    required this.status,
    required this.unit,
    this.warningLow,
    this.warningHigh,
    this.criticalLow,
    this.criticalHigh,
    this.lastSeen,
    required this.isActive,
  });

  factory Device.fromJson(Map<String, dynamic> json) {
    return Device(
      id: json['id']?.toString() ?? '',
      deviceId: json['device_id'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      deviceType: json['device_type']?['code'] ?? json['device_type'] ?? '',
      status: json['status'] ?? 'offline',
      unit: json['unit'] ?? json['device_type']?['default_unit'] ?? '',
      warningLow: json['warning_low']?.toDouble(),
      warningHigh: json['warning_high']?.toDouble(),
      criticalLow: json['critical_low']?.toDouble(),
      criticalHigh: json['critical_high']?.toDouble(),
      lastSeen: json['last_seen'] != null
          ? DateTime.parse(json['last_seen'])
          : null,
      isActive: json['is_active'] ?? true,
    );
  }

  bool get isOnline => status == 'online';
  bool get isOffline => status == 'offline';
  bool get hasFault => status == 'fault';
}

/// Device status summary
class DeviceStatusSummary {
  final int total;
  final int online;
  final int offline;
  final int fault;
  final int maintenance;

  DeviceStatusSummary({
    required this.total,
    required this.online,
    required this.offline,
    required this.fault,
    required this.maintenance,
  });

  factory DeviceStatusSummary.fromJson(Map<String, dynamic> json) {
    final byStatus = json['by_status'] as Map<String, dynamic>? ?? {};
    return DeviceStatusSummary(
      total: json['total'] ?? 0,
      online: byStatus['online'] ?? 0,
      offline: byStatus['offline'] ?? 0,
      fault: byStatus['fault'] ?? 0,
      maintenance: byStatus['maintenance'] ?? 0,
    );
  }

  factory DeviceStatusSummary.empty() {
    return DeviceStatusSummary(
      total: 0,
      online: 0,
      offline: 0,
      fault: 0,
      maintenance: 0,
    );
  }
}

/// Assets state
class AssetsState {
  final List<Plant> plants;
  final List<Area> areas;
  final List<Device> devices;
  final DeviceStatusSummary statusSummary;
  final bool isLoading;
  final String? error;

  AssetsState({
    this.plants = const [],
    this.areas = const [],
    this.devices = const [],
    DeviceStatusSummary? statusSummary,
    this.isLoading = false,
    this.error,
  }) : statusSummary = statusSummary ?? DeviceStatusSummary.empty();

  AssetsState copyWith({
    List<Plant>? plants,
    List<Area>? areas,
    List<Device>? devices,
    DeviceStatusSummary? statusSummary,
    bool? isLoading,
    String? error,
  }) {
    return AssetsState(
      plants: plants ?? this.plants,
      areas: areas ?? this.areas,
      devices: devices ?? this.devices,
      statusSummary: statusSummary ?? this.statusSummary,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Assets service notifier
class AssetsNotifier extends StateNotifier<AssetsState> {
  final Dio _dio;

  AssetsNotifier(this._dio) : super(AssetsState());

  /// Fetch all plants
  Future<void> fetchPlants() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _dio.get('/api/assets/plants/');
      final List<dynamic> data = response.data['results'] ?? response.data;
      final plants = data.map((json) => Plant.fromJson(json)).toList();

      state = state.copyWith(plants: plants, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch plants',
      );
    }
  }

  /// Fetch plant hierarchy
  Future<void> fetchPlantHierarchy(String plantCode) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _dio.get('/api/assets/plants/$plantCode/hierarchy/');
      final plant = Plant.fromJson(response.data['plant'] ?? response.data);

      state = state.copyWith(
        plants: [plant],
        areas: plant.areas,
        isLoading: false,
      );
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch hierarchy',
      );
    }
  }

  /// Fetch all areas
  Future<void> fetchAreas() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _dio.get('/api/assets/areas/');
      final List<dynamic> data = response.data['results'] ?? response.data;
      final areas = data.map((json) => Area.fromJson(json)).toList();

      state = state.copyWith(areas: areas, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch areas',
      );
    }
  }

  /// Fetch devices by area
  Future<void> fetchDevicesByArea(String areaCode) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _dio.get(
        '/api/assets/devices/by_area/',
        queryParameters: {'area': areaCode},
      );
      final List<dynamic> data = response.data['devices'] ?? response.data;
      final devices = data.map((json) => Device.fromJson(json)).toList();

      state = state.copyWith(devices: devices, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch devices',
      );
    }
  }

  /// Fetch all devices
  Future<void> fetchDevices({String? status, String? deviceType}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final queryParams = <String, dynamic>{};
      if (status != null) queryParams['status'] = status;
      if (deviceType != null) queryParams['device_type'] = deviceType;

      final response = await _dio.get(
        '/api/assets/devices/',
        queryParameters: queryParams,
      );
      final List<dynamic> data = response.data['results'] ?? response.data;
      final devices = data.map((json) => Device.fromJson(json)).toList();

      state = state.copyWith(devices: devices, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Failed to fetch devices',
      );
    }
  }

  /// Fetch device status summary
  Future<void> fetchStatusSummary() async {
    try {
      final response = await _dio.get('/api/assets/devices/status_summary/');
      final summary = DeviceStatusSummary.fromJson(response.data);

      state = state.copyWith(statusSummary: summary);
    } on DioException catch (e) {
      print('Failed to fetch status summary: ${e.message}');
    }
  }

  /// Search devices
  Future<void> searchDevices(String query, {String? area, String? deviceType}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _dio.post(
        '/api/assets/devices/search/',
        data: {
          'query': query,
          if (area != null) 'area': area,
          if (deviceType != null) 'device_type': deviceType,
        },
      );
      final List<dynamic> data = response.data['devices'] ?? response.data;
      final devices = data.map((json) => Device.fromJson(json)).toList();

      state = state.copyWith(devices: devices, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data?['error'] ?? 'Search failed',
      );
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Providers
final assetsProvider = StateNotifierProvider<AssetsNotifier, AssetsState>((ref) {
  final dio = ref.watch(apiClientProvider);
  return AssetsNotifier(dio);
});

final plantsProvider = Provider<List<Plant>>((ref) {
  return ref.watch(assetsProvider).plants;
});

final areasProvider = Provider<List<Area>>((ref) {
  return ref.watch(assetsProvider).areas;
});

final devicesProvider = Provider<List<Device>>((ref) {
  return ref.watch(assetsProvider).devices;
});

final deviceStatusSummaryProvider = Provider<DeviceStatusSummary>((ref) {
  return ref.watch(assetsProvider).statusSummary;
});
