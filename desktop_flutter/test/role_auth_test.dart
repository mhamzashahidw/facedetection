import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:desktop_flutter/main.dart';
import 'package:desktop_flutter/services/bridge_client.dart';

void main() {
  testWidgets('Role-Based Authentication, Remember Me, Navigation & View Isolation Test', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      try {
        final f = File('remembered_user.json');
        if (f.existsSync()) f.deleteSync();
      } catch (_) {}
    });

    final testClient = BridgeClient(enableBackgroundPolling: false);
    addTearDown(() => testClient.dispose());

    await tester.pumpWidget(UniVisionDesktopApp(client: testClient));
    await tester.pump();

    // 1. Initial State: Login Screen is displayed with professional elements
    expect(find.text('UNIVISION'), findsOneWidget);
    expect(find.text('Biometric Station & Attendance Portal'), findsOneWidget);
    expect(find.text('Remember Me'), findsOneWidget);
    expect(find.text('Sign In to UniVision'), findsOneWidget);
    expect(find.text('Demo Admin'), findsNothing); // Demo buttons must be gone!

    // 2. Login as Admin with Remember Me checked
    await tester.tap(find.text('Admin'));
    await tester.pump();
    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), 'admin');
    await tester.enterText(fields.at(1), 'admin123');
    await tester.tap(find.text('Remember Me'));
    await tester.pump();

    await tester.tap(find.text('Sign In to UniVision'));
    await tester.pumpAndSettle();

    expect(testClient.currentUser?['role'], 'admin');
    expect(find.text('ADMINISTRATOR'), findsOneWidget);
    expect(find.text('Attendance Logs'), findsOneWidget);
    expect(find.text('Biometrics Enroll'), findsOneWidget);
    expect(find.text('Live Monitoring'), findsOneWidget);
    expect(find.text('Cloud & Diagnostics'), findsOneWidget);
    expect(find.text('User & Passwords'), findsOneWidget);

    // 3. Logout
    await tester.tap(find.text('Log Out'));
    await tester.pumpAndSettle();
    expect(find.text('Confirm Logout'), findsOneWidget);
    // Tap confirm in dialog
    await tester.tap(find.widgetWithText(ElevatedButton, 'Log Out'));
    await tester.pumpAndSettle();

    // Verify back at Login Screen
    expect(find.text('Sign In to UniVision'), findsOneWidget);
    expect(testClient.currentUser, isNull);

    // 4. Login as Teacher
    await tester.tap(find.text('Teacher'));
    await tester.pump();
    final teacherFields = find.byType(TextField);
    await tester.enterText(teacherFields.at(0), 'teacher');
    await tester.enterText(teacherFields.at(1), 'teacher123');
    await tester.tap(find.text('Sign In to UniVision'));
    await tester.pumpAndSettle();

    expect(testClient.currentUser?['role'], 'teacher');
    expect(find.text('FACULTY TEACHER'), findsOneWidget);
    expect(find.text('Live Class Session'), findsOneWidget);
    expect(find.text('Student Attendance'), findsOneWidget);
    // Teacher must NOT have access to Biometrics Enroll or User Management
    expect(find.text('Biometrics Enroll'), findsNothing);
    expect(find.text('User & Passwords'), findsNothing);

    // 5. Logout
    await tester.tap(find.text('Log Out'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'Log Out'));
    await tester.pumpAndSettle();

    // 6. Login as Student
    await tester.tap(find.text('Student'));
    await tester.pump();
    final studentFields = find.byType(TextField);
    await tester.enterText(studentFields.at(0), '2025(s)-SE-5');
    await tester.enterText(studentFields.at(1), 'student123');
    await tester.tap(find.text('Sign In to UniVision'));
    await tester.pumpAndSettle();

    expect(testClient.currentUser?['role'], 'student');
    expect(find.textContaining('STUDENT • 2025(s)-SE-5'), findsOneWidget);
    expect(find.text('My Attendance'), findsOneWidget);
    // Student must NOT have live session controls, biometrics enroll, or cloud diagnostics
    expect(find.text('Live Class Session'), findsNothing);
    expect(find.text('Live Monitoring'), findsNothing);
    expect(find.text('Biometrics Enroll'), findsNothing);
    expect(find.text('Cloud & Diagnostics'), findsNothing);
    expect(find.text('User & Passwords'), findsNothing);

    // Verify Student Attendance Screen elements
    expect(find.text('CLASSES ATTENDED'), findsOneWidget);
    expect(find.text('LATEST ATTENDANCE'), findsOneWidget);
  });
}
