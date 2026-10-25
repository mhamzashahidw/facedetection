import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:desktop_flutter/main.dart';
import 'package:desktop_flutter/services/bridge_client.dart';
import 'package:desktop_flutter/screens/user_management_screen.dart';

void main() {
  group('Admin User & Password Management Tests', () {
    testWidgets('Admin can navigate to User Management screen and view users', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1280, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final testClient = BridgeClient(
        enableBackgroundPolling: false,
        initialUser: const {
          'id': 1,
          'username': 'admin',
          'role': 'admin',
          'full_name': 'System Administrator',
        },
      );
      addTearDown(() => testClient.dispose());

      await tester.pumpWidget(UniVisionDesktopApp(client: testClient));
      await tester.pump();

      // 1. Verify User & Passwords navigation tab exists in Sidebar
      expect(find.text('User & Passwords'), findsOneWidget);
      await tester.tap(find.text('User & Passwords'));
      await tester.pumpAndSettle();

      // 2. Verify User Management Screen elements
      expect(find.text('User & Password Management'), findsOneWidget);
      expect(find.text('Create User'), findsOneWidget);
      expect(find.text('TOTAL ACCOUNTS'), findsOneWidget);
      expect(find.text('STUDENTS'), findsOneWidget);
      expect(find.text('FACULTY TEACHERS'), findsOneWidget);
      expect(find.text('ADMINISTRATORS'), findsOneWidget);

      // Verify default users table content
      expect(find.text('System Administrator'), findsWidgets);
      expect(find.text('Prof. Alan Turing'), findsOneWidget);
      expect(find.text('Alice Johnson'), findsOneWidget);
    });

    testWidgets('Admin can create user, edit password, and login with new password', (WidgetTester tester) async {
      final client = BridgeClient(baseUrl: 'http://127.0.0.1:9999', enableBackgroundPolling: false);
      addTearDown(() => client.dispose());

      // 1. Create a new student user
      final created = await client.createUser(
        username: '2026-SE-999',
        email: 'ada@student.edu',
        password: 'initial_secret_123',
        role: 'student',
        fullName: 'Ada Lovelace',
        rollNo: '2026-SE-999',
      );
      expect(created, isTrue);
      expect(client.users.any((u) => u['username'] == '2026-SE-999'), isTrue);

      final user = client.users.firstWhere((u) => u['username'] == '2026-SE-999');
      final userId = user['id'] as int;

      // 2. Login with initial password succeeds
      final initialLoginOk = await client.login(
        identifier: '2026-SE-999',
        password: 'initial_secret_123',
        role: 'student',
      );
      expect(initialLoginOk, isTrue);
      expect(client.currentUser?['full_name'], 'Ada Lovelace');
      client.logout();

      // 3. Admin edits/resets the student password
      final pwdUpdated = await client.updateUserPassword(
        userId: userId,
        newPassword: 'updated_brand_new_pwd_456',
      );
      expect(pwdUpdated, isTrue);

      // 4. Old password must now fail
      final oldLoginFail = await client.login(
        identifier: '2026-SE-999',
        password: 'initial_secret_123',
        role: 'student',
      );
      expect(oldLoginFail, isFalse);

      // 5. New password succeeds
      final newLoginOk = await client.login(
        identifier: '2026-SE-999',
        password: 'updated_brand_new_pwd_456',
        role: 'student',
      );
      expect(newLoginOk, isTrue);
      expect(client.currentUser?['username'], '2026-SE-999');
      client.logout();

      // 6. Admin can edit user details
      final edited = await client.updateUser(
        userId: userId,
        fullName: 'Lady Ada Lovelace',
      );
      expect(edited, isTrue);
      expect(client.users.firstWhere((u) => u['id'] == userId)['full_name'], 'Lady Ada Lovelace');

      // 7. Admin deletes user
      final deleted = await client.deleteUser(userId);
      expect(deleted, isTrue);
      expect(client.users.any((u) => u['id'] == userId), isFalse);
    });

    testWidgets('Teacher and Student roles do not have access to User & Password Management', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1280, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      // 1. Teacher
      final teacherClient = BridgeClient(
        enableBackgroundPolling: false,
        initialUser: const {
          'id': 2,
          'username': 'teacher',
          'role': 'teacher',
          'full_name': 'Prof. Alan Turing',
        },
      );
      addTearDown(() => teacherClient.dispose());

      await tester.pumpWidget(UniVisionDesktopApp(client: teacherClient));
      await tester.pump();
      expect(find.text('User & Passwords'), findsNothing);

      // 2. Student
      final studentClient = BridgeClient(
        enableBackgroundPolling: false,
        initialUser: const {
          'id': 3,
          'username': '2024-CS-001',
          'role': 'student',
          'full_name': 'Alice Johnson',
        },
      );
      addTearDown(() => studentClient.dispose());

      await tester.pumpWidget(UniVisionDesktopApp(client: studentClient));
      await tester.pump();
      expect(find.text('User & Passwords'), findsNothing);
    });
  });
}
