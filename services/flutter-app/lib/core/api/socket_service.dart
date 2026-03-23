import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:socket_io_client/socket_io_client.dart' as io;
import 'package:logger/logger.dart';
import '../config/app_config.dart';
import '../auth/auth_service.dart';

final _logger = Logger(printer: PrettyPrinter(methodCount: 0));

/// Socket connection state
enum SocketStatus { disconnected, connecting, connected, error }

/// Alert event from server
class AlertEvent {
  final String alertId;
  final String deviceId;
  final String? deviceName;
  final String? area;
  final String severity;
  final String status;
  final String message;
  final double? value;
  final double? threshold;
  final String? unit;
  final DateTime? triggeredAt;

  AlertEvent({
    required this.alertId,
    required this.deviceId,
    this.deviceName,
    this.area,
    required this.severity,
    required this.status,
    required this.message,
    this.value,
    this.threshold,
    this.unit,
    this.triggeredAt,
  });

  factory AlertEvent.fromJson(Map<String, dynamic> json) => AlertEvent(
        alertId: json['alert_id'] ?? '',
        deviceId: json['device_id'] ?? '',
        deviceName: json['device_name'],
        area: json['area'],
        severity: json['severity'] ?? 'info',
        status: json['status'] ?? 'active',
        message: json['message'] ?? '',
        value: json['value']?.toDouble(),
        threshold: json['threshold']?.toDouble(),
        unit: json['unit'],
        triggeredAt: json['triggered_at'] != null
            ? DateTime.tryParse(json['triggered_at'])
            : null,
      );
}

/// Socket.IO service for real-time alerts
class SocketService extends StateNotifier<SocketStatus> {
  final Ref _ref;
  io.Socket? _socket;

  final _alertStreamController = StreamController<AlertEvent>.broadcast();
  final _acknowledgedStreamController = StreamController<Map<String, dynamic>>.broadcast();
  final _resolvedStreamController = StreamController<Map<String, dynamic>>.broadcast();
  final _statsStreamController = StreamController<Map<String, dynamic>>.broadcast();

  Stream<AlertEvent> get alertStream => _alertStreamController.stream;
  Stream<Map<String, dynamic>> get acknowledgedStream => _acknowledgedStreamController.stream;
  Stream<Map<String, dynamic>> get resolvedStream => _resolvedStreamController.stream;
  Stream<Map<String, dynamic>> get statsStream => _statsStreamController.stream;

  SocketService(this._ref) : super(SocketStatus.disconnected);

  void connect() {
    if (_socket != null && _socket!.connected) return;

    final token = _ref.read(accessTokenProvider);
    if (token == null) {
      state = SocketStatus.error;
      return;
    }

    state = SocketStatus.connecting;

    _socket = io.io(
      '${AppConfig.socketUrl}/alerts',
      io.OptionBuilder()
          .setTransports(['websocket'])
          .setAuth({'token': 'Bearer $token'})
          .enableAutoConnect()
          .enableReconnection()
          .setReconnectionAttempts(AppConfig.socketReconnectAttempts)
          .setReconnectionDelay(AppConfig.socketReconnectDelay.inMilliseconds)
          .build(),
    );

    _setupListeners();
  }

  void _setupListeners() {
    final socket = _socket;
    if (socket == null) return;

    socket.onConnect((_) {
      _logger.i('Socket connected');
      state = SocketStatus.connected;
    });

    socket.onDisconnect((_) {
      _logger.i('Socket disconnected');
      state = SocketStatus.disconnected;
    });

    socket.onConnectError((error) {
      _logger.e('Socket connect error: $error');
      state = SocketStatus.error;
    });

    socket.onError((error) {
      _logger.e('Socket error: $error');
      state = SocketStatus.error;
    });

    // Auth events
    socket.on('auth:success', (data) {
      _logger.i('Socket authenticated: ${data['user']}');
    });

    socket.on('auth:error', (data) {
      _logger.e('Socket auth error: ${data['message']}');
      state = SocketStatus.error;
    });

    // Alert events
    socket.on('alert:new', (data) {
      _logger.d('New alert: ${data['alert_id']}');
      _alertStreamController.add(AlertEvent.fromJson(data));
    });

    socket.on('alert:acknowledged', (data) {
      _logger.d('Alert acknowledged: ${data['alert_id']}');
      _acknowledgedStreamController.add(Map<String, dynamic>.from(data));
    });

    socket.on('alert:resolved', (data) {
      _logger.d('Alert resolved: ${data['alert_id']}');
      _resolvedStreamController.add(Map<String, dynamic>.from(data));
    });

    socket.on('alert:stats', (data) {
      _statsStreamController.add(Map<String, dynamic>.from(data));
    });

    // Subscription confirmation
    socket.on('subscribed', (data) {
      _logger.d('Subscribed: $data');
    });

    socket.on('error', (data) {
      _logger.e('Server error: ${data['message']}');
    });
  }

  void subscribeToArea(String area) {
    _socket?.emit('subscribe:area', {'area': area});
  }

  void subscribeToAll() {
    _socket?.emit('subscribe:all');
  }

  void unsubscribe({String? area, bool all = false}) {
    if (all) {
      _socket?.emit('unsubscribe', {'all': true});
    } else if (area != null) {
      _socket?.emit('unsubscribe', {'area': area});
    }
  }

  void acknowledgeAlert(String alertId) {
    _socket?.emit('acknowledge', {'alert_id': alertId});
  }

  void disconnect() {
    _socket?.disconnect();
    _socket?.dispose();
    _socket = null;
    state = SocketStatus.disconnected;
  }

  @override
  void dispose() {
    _alertStreamController.close();
    _acknowledgedStreamController.close();
    _resolvedStreamController.close();
    _statsStreamController.close();
    disconnect();
    super.dispose();
  }
}

/// Providers
final socketServiceProvider = StateNotifierProvider<SocketService, SocketStatus>((ref) {
  final service = SocketService(ref);

  // Auto-connect when authenticated
  ref.listen(authServiceProvider, (prev, next) {
    if (next.isAuthenticated && prev?.isAuthenticated != true) {
      service.connect();
      service.subscribeToAll();
    } else if (!next.isAuthenticated) {
      service.disconnect();
    }
  });

  return service;
});

final alertStreamProvider = StreamProvider<AlertEvent>((ref) {
  final service = ref.watch(socketServiceProvider.notifier);
  return service.alertStream;
});

final socketStatusProvider = Provider<SocketStatus>((ref) {
  return ref.watch(socketServiceProvider);
});
