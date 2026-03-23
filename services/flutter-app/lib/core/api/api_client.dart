import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import '../config/app_config.dart';
import '../auth/auth_service.dart';

final logger = Logger(
  printer: PrettyPrinter(methodCount: 0, errorMethodCount: 5),
);

/// Auth interceptor - adds JWT to requests and handles refresh
class AuthInterceptor extends Interceptor {
  final Ref _ref;

  AuthInterceptor(this._ref);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _ref.read(accessTokenProvider);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Try to refresh token
      final authService = _ref.read(authServiceProvider.notifier);
      final refreshed = await authService.refresh();

      if (refreshed) {
        // Retry request with new token
        final token = _ref.read(accessTokenProvider);
        err.requestOptions.headers['Authorization'] = 'Bearer $token';

        try {
          final response = await Dio().fetch(err.requestOptions);
          return handler.resolve(response);
        } catch (e) {
          return handler.next(err);
        }
      }
    }
    handler.next(err);
  }
}

/// Logging interceptor
class LoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    logger.d('→ ${options.method} ${options.path}');
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    logger.d('← ${response.statusCode} ${response.requestOptions.path}');
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    logger.e('✗ ${err.response?.statusCode} ${err.requestOptions.path}: ${err.message}');
    handler.next(err);
  }
}

/// Main API client provider
final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: AppConfig.apiBaseUrl,
    connectTimeout: AppConfig.connectTimeout,
    receiveTimeout: AppConfig.receiveTimeout,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  ));

  dio.interceptors.addAll([
    AuthInterceptor(ref),
    LoggingInterceptor(),
  ]);

  return dio;
});

/// API Exception wrapper
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic data;

  ApiException(this.message, {this.statusCode, this.data});

  factory ApiException.fromDioException(DioException e) {
    final response = e.response;
    String message = 'Request failed';

    if (response != null) {
      if (response.data is Map && response.data['error'] != null) {
        message = response.data['error'];
      } else if (response.data is Map && response.data['message'] != null) {
        message = response.data['message'];
      } else {
        message = 'Error ${response.statusCode}';
      }
    } else if (e.type == DioExceptionType.connectionTimeout) {
      message = 'Connection timeout';
    } else if (e.type == DioExceptionType.receiveTimeout) {
      message = 'Server not responding';
    } else if (e.type == DioExceptionType.connectionError) {
      message = 'No internet connection';
    }

    return ApiException(message, statusCode: response?.statusCode, data: response?.data);
  }

  @override
  String toString() => message;
}

/// Extension for handling API responses
extension DioResponseExtension on Future<Response> {
  Future<T> then<T>(T Function(Response) onSuccess) async {
    try {
      final response = await this;
      return onSuccess(response);
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    }
  }
}
