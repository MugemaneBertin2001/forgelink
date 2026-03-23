import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../auth/auth_service.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/dashboard/presentation/screens/dashboard_screen.dart';
import '../../features/alerts/presentation/screens/alerts_screen.dart';
import '../../features/assets/presentation/screens/assets_screen.dart';
import '../../features/telemetry/presentation/screens/telemetry_screen.dart';
import '../../features/settings/presentation/screens/settings_screen.dart';
import '../widgets/main_scaffold.dart';

/// Route names
class AppRoutes {
  AppRoutes._();

  static const login = '/login';
  static const dashboard = '/';
  static const alerts = '/alerts';
  static const alertDetail = '/alerts/:id';
  static const assets = '/assets';
  static const assetDetail = '/assets/:id';
  static const telemetry = '/telemetry';
  static const deviceTelemetry = '/telemetry/:deviceId';
  static const settings = '/settings';
}

/// Navigation shell key
final _shellNavigatorKey = GlobalKey<NavigatorState>();

/// Router provider
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authServiceProvider);

  return GoRouter(
    initialLocation: AppRoutes.dashboard,
    debugLogDiagnostics: true,
    redirect: (context, state) {
      final isAuthenticated = authState.isAuthenticated;
      final isLoggingIn = state.matchedLocation == AppRoutes.login;
      final isLoading = authState.status == AuthStatus.unknown;

      // Still loading auth state
      if (isLoading) return null;

      // Not authenticated and not on login page
      if (!isAuthenticated && !isLoggingIn) {
        return AppRoutes.login;
      }

      // Authenticated and on login page
      if (isAuthenticated && isLoggingIn) {
        return AppRoutes.dashboard;
      }

      return null;
    },
    routes: [
      // Login (no shell)
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => const LoginScreen(),
      ),

      // Main shell with bottom navigation
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) => MainScaffold(child: child),
        routes: [
          GoRoute(
            path: AppRoutes.dashboard,
            pageBuilder: (context, state) => const NoTransitionPage(
              child: DashboardScreen(),
            ),
          ),
          GoRoute(
            path: AppRoutes.alerts,
            pageBuilder: (context, state) => const NoTransitionPage(
              child: AlertsScreen(),
            ),
            routes: [
              GoRoute(
                path: ':id',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return AlertDetailScreen(alertId: id);
                },
              ),
            ],
          ),
          GoRoute(
            path: AppRoutes.assets,
            pageBuilder: (context, state) => const NoTransitionPage(
              child: AssetsScreen(),
            ),
            routes: [
              GoRoute(
                path: ':id',
                builder: (context, state) {
                  final id = state.pathParameters['id']!;
                  return AssetDetailScreen(assetId: id);
                },
              ),
            ],
          ),
          GoRoute(
            path: AppRoutes.telemetry,
            pageBuilder: (context, state) => const NoTransitionPage(
              child: TelemetryScreen(),
            ),
            routes: [
              GoRoute(
                path: ':deviceId',
                builder: (context, state) {
                  final deviceId = state.pathParameters['deviceId']!;
                  return DeviceTelemetryScreen(deviceId: deviceId);
                },
              ),
            ],
          ),
          GoRoute(
            path: AppRoutes.settings,
            pageBuilder: (context, state) => const NoTransitionPage(
              child: SettingsScreen(),
            ),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Text('Page not found: ${state.uri}'),
      ),
    ),
  );
});

/// Placeholder screens (will be implemented)
class AlertDetailScreen extends StatelessWidget {
  final String alertId;
  const AlertDetailScreen({super.key, required this.alertId});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Alert $alertId')),
        body: const Center(child: Text('Alert Detail')),
      );
}

class AssetDetailScreen extends StatelessWidget {
  final String assetId;
  const AssetDetailScreen({super.key, required this.assetId});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Asset $assetId')),
        body: const Center(child: Text('Asset Detail')),
      );
}

class DeviceTelemetryScreen extends StatelessWidget {
  final String deviceId;
  const DeviceTelemetryScreen({super.key, required this.deviceId});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Device $deviceId')),
        body: const Center(child: Text('Device Telemetry')),
      );
}
