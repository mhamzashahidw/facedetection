import 'dart:io';
import 'package:flutter/material.dart';
import 'theme.dart';
import 'services/bridge_client.dart';
import 'widgets/sidebar.dart';
import 'widgets/top_bar.dart';
import 'screens/live_monitoring_screen.dart';
import 'screens/enrollment_screen.dart';
import 'screens/attendance_logs_screen.dart';
import 'screens/cloud_diagnostics_screen.dart';
import 'screens/student_attendance_screen.dart';
import 'screens/user_management_screen.dart';
import 'screens/login_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const UniVisionDesktopApp());
}

class UniVisionDesktopApp extends StatelessWidget {
  final BridgeClient? client;
  final File? rememberFile;

  const UniVisionDesktopApp({super.key, this.client, this.rememberFile});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'UniVision — Biometric Classroom Station',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: MainWorkstationView(client: client, rememberFile: rememberFile),
    );
  }
}

class MainWorkstationView extends StatefulWidget {
  final BridgeClient? client;
  final File? rememberFile;

  const MainWorkstationView({super.key, this.client, this.rememberFile});

  @override
  State<MainWorkstationView> createState() => _MainWorkstationViewState();
}

class _MainWorkstationViewState extends State<MainWorkstationView> {
  late final BridgeClient _client;
  bool _ownsClient = false;
  int _selectedTab = 0;
  String? _lastRole;

  @override
  void initState() {
    super.initState();
    if (widget.client != null) {
      _client = widget.client!;
      _ownsClient = false;
    } else {
      _client = BridgeClient();
      _ownsClient = true;
    }
  }

  @override
  void dispose() {
    if (_ownsClient) {
      _client.dispose();
    }
    super.dispose();
  }

  void _syncDefaultTabForRole(String role) {
    if (_lastRole != role) {
      _lastRole = role;
      if (role == 'student') {
        _selectedTab = 4; // Default to My Attendance
      } else {
        _selectedTab = 0; // Default to Live Class / Live Monitoring
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _client,
      builder: (context, _) {
        final user = _client.currentUser;

        // If not logged in, show the LoginScreen
        if (user == null) {
          _lastRole = null;
          return LoginScreen(client: _client, rememberFile: widget.rememberFile);
        }

        final role = (user['role'] ?? 'admin').toString().toLowerCase();
        _syncDefaultTabForRole(role);

        return Scaffold(
          body: Row(
            children: [
              // Sidebar Navigation
              Sidebar(
                selectedIndex: _selectedTab,
                client: _client,
                onItemSelected: (index) {
                  setState(() => _selectedTab = index);
                },
              ),

              // Main Workstation Content Area
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      // Top KPI Bar
                      TopBar(client: _client),
                      const SizedBox(height: 16),

                      // Stacked Page Views
                      Expanded(
                        child: IndexedStack(
                          index: _selectedTab,
                          children: [
                            LiveMonitoringScreen(client: _client),     // 0
                            EnrollmentScreen(client: _client),         // 1
                            AttendanceLogsScreen(client: _client),     // 2
                            CloudDiagnosticsScreen(client: _client),   // 3
                            StudentAttendanceScreen(client: _client),  // 4
                            UserManagementScreen(client: _client),     // 5
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
