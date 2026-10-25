import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:desktop_flutter/main.dart';
import 'package:desktop_flutter/services/bridge_client.dart';

void main() {
  group('Remember Me Feature Tests', () {
    final rememberFile = File('test_remembered_user.json');

    setUp(() {
      try {
        if (rememberFile.existsSync()) rememberFile.deleteSync();
      } catch (_) {}
    });

    tearDown(() {
      try {
        if (rememberFile.existsSync()) rememberFile.deleteSync();
      } catch (_) {}
    });

    testWidgets('Remember Me persists credentials to disk and restores on subsequent app launch',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1280, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final client1 = BridgeClient(enableBackgroundPolling: false);
      addTearDown(() => client1.dispose());

      await tester.pumpWidget(UniVisionDesktopApp(client: client1, rememberFile: rememberFile));
      await tester.pump();

      // Enter credentials
      final fields = find.byType(TextField);
      await tester.enterText(fields.at(0), 'admin');
      await tester.enterText(fields.at(1), 'admin123');

      // Check Remember Me
      expect(find.text('Remember Me'), findsOneWidget);
      await tester.tap(find.text('Remember Me'));
      await tester.pump();

      // Submit Login
      await tester.tap(find.text('Sign In to UniVision'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      // Verify file was written
      expect(rememberFile.existsSync(), isTrue);
      final jsonMap = jsonDecode(rememberFile.readAsStringSync());
      expect(jsonMap['remember'], isTrue);
      expect(jsonMap['identifier'], 'admin');
      expect(jsonMap['role'], 'admin');

      // Logout
      await tester.tap(find.text('Log Out'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(ElevatedButton, 'Log Out'));
      await tester.pumpAndSettle();

      // Mount fresh app instance with same rememberFile
      final client2 = BridgeClient(enableBackgroundPolling: false);
      addTearDown(() => client2.dispose());

      await tester.pumpWidget(UniVisionDesktopApp(client: client2, rememberFile: rememberFile));
      await tester.pump();

      // Verify saved credentials are auto-restored
      final restoredFields = find.byType(TextField);
      final idWidget = tester.widget<TextField>(restoredFields.at(0));
      expect(idWidget.controller?.text, 'admin');

      final pwdWidget = tester.widget<TextField>(restoredFields.at(1));
      expect(pwdWidget.controller?.text, 'admin123');

      // Verify checkbox is checked
      final checkbox = tester.widget<Checkbox>(find.byType(Checkbox));
      expect(checkbox.value, isTrue);
    });

    testWidgets('Unchecking Remember Me and logging in clears remembered credentials file',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1280, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      // Pre-create file
      rememberFile.writeAsStringSync(
        jsonEncode({
          'remember': true,
          'role': 'admin',
          'identifier': 'admin',
          'password': 'admin123',
        }),
        flush: true,
      );

      final client = BridgeClient(enableBackgroundPolling: false);
      addTearDown(() => client.dispose());

      await tester.pumpWidget(UniVisionDesktopApp(client: client, rememberFile: rememberFile));
      await tester.pump();

      // Checkbox should initially be true
      expect(tester.widget<Checkbox>(find.byType(Checkbox)).value, isTrue);

      // Uncheck Remember Me
      await tester.tap(find.text('Remember Me'));
      await tester.pump();
      expect(tester.widget<Checkbox>(find.byType(Checkbox)).value, isFalse);

      // Submit Login
      await tester.tap(find.text('Sign In to UniVision'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      // Verify file was removed
      expect(rememberFile.existsSync(), isFalse);
    });
  });
}
