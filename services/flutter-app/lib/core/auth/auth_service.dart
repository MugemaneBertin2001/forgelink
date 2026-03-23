import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/app_config.dart';

/// Authentication token data
class AuthTokens {
  final String accessToken;
  final String refreshToken;
  final DateTime expiresAt;

  AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresAt,
  });

  bool get isExpired => DateTime.now().isAfter(expiresAt);

  bool get needsRefresh =>
      DateTime.now().isAfter(expiresAt.subtract(AppConfig.tokenRefreshThreshold));

  Map<String, dynamic> toJson() => {
        'accessToken': accessToken,
        'refreshToken': refreshToken,
        'expiresAt': expiresAt.toIso8601String(),
      };

  factory AuthTokens.fromJson(Map<String, dynamic> json) => AuthTokens(
        accessToken: json['accessToken'],
        refreshToken: json['refreshToken'],
        expiresAt: DateTime.parse(json['expiresAt']),
      );
}

/// User data from JWT
class AuthUser {
  final String id;
  final String email;
  final String role;
  final Set<String> permissions;
  final String? plantId;
  final String? areaCode;

  AuthUser({
    required this.id,
    required this.email,
    required this.role,
    required this.permissions,
    this.plantId,
    this.areaCode,
  });

  bool hasPermission(String permission) =>
      role == 'FACTORY_ADMIN' || permissions.contains(permission);

  bool hasAnyPermission(List<String> perms) =>
      role == 'FACTORY_ADMIN' || perms.any((p) => permissions.contains(p));

  bool canAccessArea(String area) =>
      role == 'FACTORY_ADMIN' || areaCode == null || areaCode == area;

  factory AuthUser.fromJwt(String token) {
    final parts = token.split('.');
    if (parts.length != 3) throw Exception('Invalid JWT');

    final payload = json.decode(
      utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
    );

    return AuthUser(
      id: payload['sub'] ?? '',
      email: payload['email'] ?? '',
      role: payload['role'] ?? '',
      permissions: Set<String>.from(payload['permissions'] ?? []),
      plantId: payload['plant_id'],
      areaCode: payload['area'],
    );
  }
}

/// Authentication state
enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthState {
  final AuthStatus status;
  final AuthUser? user;
  final AuthTokens? tokens;
  final String? error;

  const AuthState({
    this.status = AuthStatus.unknown,
    this.user,
    this.tokens,
    this.error,
  });

  AuthState copyWith({
    AuthStatus? status,
    AuthUser? user,
    AuthTokens? tokens,
    String? error,
  }) =>
      AuthState(
        status: status ?? this.status,
        user: user ?? this.user,
        tokens: tokens ?? this.tokens,
        error: error,
      );

  bool get isAuthenticated => status == AuthStatus.authenticated;
}

/// Authentication service
class AuthService extends StateNotifier<AuthState> {
  final FlutterSecureStorage _storage;
  final Dio _dio;

  static const _tokenKey = 'auth_tokens';

  AuthService(this._storage, this._dio) : super(const AuthState()) {
    _init();
  }

  Future<void> _init() async {
    try {
      final stored = await _storage.read(key: _tokenKey);
      if (stored != null) {
        final tokens = AuthTokens.fromJson(json.decode(stored));
        if (!tokens.isExpired) {
          final user = AuthUser.fromJwt(tokens.accessToken);
          state = AuthState(
            status: AuthStatus.authenticated,
            user: user,
            tokens: tokens,
          );

          // Refresh if needed
          if (tokens.needsRefresh) {
            await refresh();
          }
          return;
        }
      }
    } catch (e) {
      // Invalid stored data
    }
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  Future<bool> login(String email, String password) async {
    try {
      final response = await _dio.post(
        '${AppConfig.idpBaseUrl}/auth/login',
        data: {'email': email, 'password': password},
      );

      final data = response.data;
      final tokens = AuthTokens(
        accessToken: data['accessToken'],
        refreshToken: data['refreshToken'],
        expiresAt: DateTime.now().add(Duration(seconds: data['expiresIn'] ?? 86400)),
      );

      await _storage.write(key: _tokenKey, value: json.encode(tokens.toJson()));

      final user = AuthUser.fromJwt(tokens.accessToken);
      state = AuthState(
        status: AuthStatus.authenticated,
        user: user,
        tokens: tokens,
      );

      return true;
    } on DioException catch (e) {
      final message = e.response?.data?['error'] ?? 'Login failed';
      state = AuthState(status: AuthStatus.unauthenticated, error: message);
      return false;
    } catch (e) {
      state = AuthState(status: AuthStatus.unauthenticated, error: e.toString());
      return false;
    }
  }

  Future<bool> refresh() async {
    final currentTokens = state.tokens;
    if (currentTokens == null) return false;

    try {
      final response = await _dio.post(
        '${AppConfig.idpBaseUrl}/auth/refresh',
        data: {'refreshToken': currentTokens.refreshToken},
      );

      final data = response.data;
      final tokens = AuthTokens(
        accessToken: data['accessToken'],
        refreshToken: data['refreshToken'] ?? currentTokens.refreshToken,
        expiresAt: DateTime.now().add(Duration(seconds: data['expiresIn'] ?? 86400)),
      );

      await _storage.write(key: _tokenKey, value: json.encode(tokens.toJson()));

      final user = AuthUser.fromJwt(tokens.accessToken);
      state = state.copyWith(tokens: tokens, user: user);

      return true;
    } catch (e) {
      await logout();
      return false;
    }
  }

  Future<void> logout() async {
    final tokens = state.tokens;
    if (tokens != null) {
      try {
        await _dio.post(
          '${AppConfig.idpBaseUrl}/auth/logout',
          data: {'refreshToken': tokens.refreshToken},
        );
      } catch (_) {}
    }

    await _storage.delete(key: _tokenKey);
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  String? get accessToken => state.tokens?.accessToken;
}

/// Providers
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );
});

final authDioProvider = Provider<Dio>((ref) {
  return Dio(BaseOptions(
    connectTimeout: AppConfig.connectTimeout,
    receiveTimeout: AppConfig.receiveTimeout,
    headers: {'Content-Type': 'application/json'},
  ));
});

final authServiceProvider = StateNotifierProvider<AuthService, AuthState>((ref) {
  return AuthService(
    ref.watch(secureStorageProvider),
    ref.watch(authDioProvider),
  );
});

/// Convenience accessors
final isAuthenticatedProvider = Provider<bool>((ref) {
  return ref.watch(authServiceProvider).isAuthenticated;
});

final currentUserProvider = Provider<AuthUser?>((ref) {
  return ref.watch(authServiceProvider).user;
});

final accessTokenProvider = Provider<String?>((ref) {
  return ref.watch(authServiceProvider).tokens?.accessToken;
});
