# ForgeLink Mobile App

Cross-platform mobile application for the ForgeLink steel factory IoT platform.

## Overview

The ForgeLink mobile app provides:

- Real-time monitoring of steel plant equipment
- Alert management and acknowledgment
- Asset hierarchy navigation
- Live telemetry visualization
- Push notifications for critical events

## Screens

1. **Login** — Authenticate via Spring IDP
2. **Dashboard** — Active alerts, key metrics, device online count
3. **Asset Tree** — Navigate Plant → Area → Line → Cell → Device
4. **Device Detail** — Live telemetry chart, status, recent events
5. **Alerts** — Filter by severity/area/status, swipe to acknowledge
6. **Profile** — User info, preferences, logout

## Technical Stack

| Component | Technology |
|-----------|------------|
| State Management | Riverpod |
| HTTP Client | Dio |
| Charts | fl_chart |
| Push Notifications | Firebase Cloud Messaging |
| Local Storage | SQLite (sqflite) |
| Certificate Pinning | dio_http2_adapter |

## Requirements

- Flutter 3.19+
- Android: API 26+ (Android 8.0)
- iOS: 14.0+

## Getting Started

```bash
cd mobile/flutter-app

# Get dependencies
flutter pub get

# Run on device/emulator
flutter run

# Run tests
flutter test
```

## Offline Support

The app caches:
- Last 2 hours of telemetry for up to 20 devices
- Asset hierarchy structure
- User preferences

Data is synced when connectivity is restored.

## Configuration

Update `lib/config/app_config.dart`:

```dart
class AppConfig {
  static const String apiBaseUrl = 'https://api.forgelink.app';
  static const String idpBaseUrl = 'https://idp.forgelink.app';
}
```
