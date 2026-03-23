/// ForgeLink App Configuration
class AppConfig {
  AppConfig._();

  // API URLs
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api',
  );

  static const String idpBaseUrl = String.fromEnvironment(
    'IDP_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );

  static const String socketUrl = String.fromEnvironment(
    'SOCKET_URL',
    defaultValue: 'http://localhost:8000',
  );

  // Timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Token refresh threshold (refresh if expires within this time)
  static const Duration tokenRefreshThreshold = Duration(minutes: 5);

  // Socket.IO reconnection
  static const int socketReconnectAttempts = 5;
  static const Duration socketReconnectDelay = Duration(seconds: 2);

  // Cache durations
  static const Duration assetsCacheDuration = Duration(minutes: 5);
  static const Duration telemetryCacheDuration = Duration(seconds: 30);

  // Pagination
  static const int defaultPageSize = 50;

  // Plant info
  static const String defaultPlant = 'steel-plant-kigali';
  static const String defaultTimezone = 'Africa/Kigali';
}
