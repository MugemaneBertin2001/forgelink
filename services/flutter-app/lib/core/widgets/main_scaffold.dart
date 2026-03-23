import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../config/router.dart';
import '../theme/app_theme.dart';
import '../api/socket_service.dart';
import '../auth/auth_service.dart';

/// Main scaffold with bottom navigation
class MainScaffold extends ConsumerWidget {
  final Widget child;

  const MainScaffold({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).matchedLocation;
    final socketStatus = ref.watch(socketStatusProvider);
    final user = ref.watch(currentUserProvider);

    return Scaffold(
      body: Stack(
        children: [
          child,
          // Connection status indicator
          if (socketStatus != SocketStatus.connected)
            Positioned(
              top: MediaQuery.of(context).padding.top,
              left: 0,
              right: 0,
              child: _ConnectionBanner(status: socketStatus),
            ),
        ],
      ),
      bottomNavigationBar: _BottomNav(
        currentLocation: location,
        user: user,
      ),
    );
  }
}

class _ConnectionBanner extends StatelessWidget {
  final SocketStatus status;

  const _ConnectionBanner({required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, text, icon) = switch (status) {
      SocketStatus.connecting => (
          AppColors.warning,
          'Connecting...',
          Icons.sync,
        ),
      SocketStatus.disconnected => (
          AppColors.textSecondary,
          'Disconnected',
          Icons.cloud_off,
        ),
      SocketStatus.error => (
          AppColors.error,
          'Connection error',
          Icons.error_outline,
        ),
      _ => (Colors.transparent, '', Icons.check),
    };

    if (status == SocketStatus.connected) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 16),
      color: color,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 16, color: Colors.white),
          const SizedBox(width: 8),
          Text(
            text,
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _BottomNav extends StatelessWidget {
  final String currentLocation;
  final AuthUser? user;

  const _BottomNav({required this.currentLocation, this.user});

  int get _currentIndex {
    if (currentLocation.startsWith(AppRoutes.alerts)) return 1;
    if (currentLocation.startsWith(AppRoutes.assets)) return 2;
    if (currentLocation.startsWith(AppRoutes.telemetry)) return 3;
    if (currentLocation.startsWith(AppRoutes.settings)) return 4;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    return BottomNavigationBar(
      currentIndex: _currentIndex,
      onTap: (index) => _onTap(context, index),
      items: [
        const BottomNavigationBarItem(
          icon: Icon(Icons.dashboard_outlined),
          activeIcon: Icon(Icons.dashboard),
          label: 'Dashboard',
        ),
        const BottomNavigationBarItem(
          icon: Badge(
            // TODO: Show active alert count
            child: Icon(Icons.notifications_outlined),
          ),
          activeIcon: Icon(Icons.notifications),
          label: 'Alerts',
        ),
        const BottomNavigationBarItem(
          icon: Icon(Icons.precision_manufacturing_outlined),
          activeIcon: Icon(Icons.precision_manufacturing),
          label: 'Assets',
        ),
        if (user?.hasPermission('telemetry.view') ?? false)
          const BottomNavigationBarItem(
            icon: Icon(Icons.show_chart_outlined),
            activeIcon: Icon(Icons.show_chart),
            label: 'Telemetry',
          ),
        const BottomNavigationBarItem(
          icon: Icon(Icons.settings_outlined),
          activeIcon: Icon(Icons.settings),
          label: 'Settings',
        ),
      ],
    );
  }

  void _onTap(BuildContext context, int index) {
    final route = switch (index) {
      0 => AppRoutes.dashboard,
      1 => AppRoutes.alerts,
      2 => AppRoutes.assets,
      3 => AppRoutes.telemetry,
      4 => AppRoutes.settings,
      _ => AppRoutes.dashboard,
    };
    context.go(route);
  }
}
