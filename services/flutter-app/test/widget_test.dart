// ForgeLink Flutter widget tests
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:forgelink_mobile/main.dart';

void main() {
  testWidgets('App renders without errors', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(
      const ProviderScope(child: ForgeLinkApp()),
    );

    // Wait for async operations
    await tester.pumpAndSettle();

    // Verify that the app renders (login screen should be shown)
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
