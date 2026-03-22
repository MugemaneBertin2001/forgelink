// ForgeLink Flutter widget tests
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Basic widget test', (WidgetTester tester) async {
    // Build a simple widget to verify test framework works
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: Text('ForgeLink'),
          ),
        ),
      ),
    );

    // Verify the text appears
    expect(find.text('ForgeLink'), findsOneWidget);
  });
}
