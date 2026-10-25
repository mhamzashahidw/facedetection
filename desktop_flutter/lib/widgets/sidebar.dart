import 'package:flutter/material.dart';
import '../theme.dart';
import '../services/bridge_client.dart';

class Sidebar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onItemSelected;
  final BridgeClient client;

  const Sidebar({
    super.key,
    required this.selectedIndex,
    required this.onItemSelected,
    required this.client,
  });

  @override
  Widget build(BuildContext context) {
    final user = client.currentUser;
    final role = (user?['role'] ?? 'admin').toString().toLowerCase();
    final fullName = user?['full_name'] ?? 'System Administrator';
    final rollNo = user?['roll_no'] ?? user?['username'] ?? '';

    return Container(
      width: 250,
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(right: BorderSide(color: AppTheme.border, width: 1)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // App Logo & Header
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                ),
                child: const Icon(Icons.remove_red_eye_rounded, color: AppTheme.primary, size: 20),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'UNIVISION',
                      style: TextStyle(
                        color: AppTheme.primary,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.5,
                      ),
                    ),
                    Text(
                      'Biometric Station',
                      style: TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // User Profile Card
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: AppTheme.surfaceSunken,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              children: [
                Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    color: _getRoleColor(role).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(_getRoleIcon(role), size: 16, color: _getRoleColor(role)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        fullName,
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 1),
                      Text(
                        _getRoleBadge(role, rollNo),
                        style: TextStyle(
                          color: _getRoleColor(role),
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),

          // Dynamic Role-Based Nav Items
          ..._buildNavItemsForRole(role),

          const Spacer(),

          // Offline-First Local Storage Info Box
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.surfaceSunken,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: AppTheme.success,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text(
                      'LOCAL STORAGE',
                      style: TextStyle(
                        color: AppTheme.textMuted,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  'SQLite Offline-First',
                  style: TextStyle(
                    color: AppTheme.success,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),

          // Log Out Button
          InkWell(
            onTap: () => _confirmLogout(context),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppTheme.error.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.logout_rounded, size: 16, color: AppTheme.error),
                  SizedBox(width: 8),
                  Text(
                    'Log Out',
                    style: TextStyle(
                      color: AppTheme.error,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildNavItemsForRole(String role) {
    if (role == 'admin') {
      return [
        _buildNavItem(2, 'Attendance Logs', Icons.format_list_bulleted_rounded),
        const SizedBox(height: 6),
        _buildNavItem(1, 'Biometrics Enroll', Icons.fingerprint_rounded),
        const SizedBox(height: 6),
        _buildNavItem(0, 'Live Monitoring', Icons.videocam_rounded),
        const SizedBox(height: 6),
        _buildNavItem(3, 'Cloud & Diagnostics', Icons.cloud_sync_rounded),
        const SizedBox(height: 6),
        _buildNavItem(5, 'User & Passwords', Icons.admin_panel_settings_rounded),
      ];
    } else if (role == 'teacher') {
      return [
        _buildNavItem(0, 'Live Class Session', Icons.videocam_rounded),
        const SizedBox(height: 6),
        _buildNavItem(2, 'Student Attendance', Icons.format_list_bulleted_rounded),
      ];
    } else if (role == 'student') {
      return [
        _buildNavItem(4, 'My Attendance', Icons.history_rounded),
      ];
    }

    return [
      _buildNavItem(0, 'Live Monitoring', Icons.videocam_rounded),
      const SizedBox(height: 6),
      _buildNavItem(1, 'Biometrics Enroll', Icons.fingerprint_rounded),
      const SizedBox(height: 6),
      _buildNavItem(2, 'Attendance Logs', Icons.format_list_bulleted_rounded),
      const SizedBox(height: 6),
      _buildNavItem(3, 'Cloud & Diagnostics', Icons.cloud_sync_rounded),
      const SizedBox(height: 6),
      _buildNavItem(5, 'User & Passwords', Icons.admin_panel_settings_rounded),
    ];
  }

  Widget _buildNavItem(int index, String title, IconData icon) {
    final bool isSelected = selectedIndex == index;
    return InkWell(
      onTap: () => onItemSelected(index),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primary.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          border: isSelected
              ? Border.all(color: AppTheme.primary.withValues(alpha: 0.35))
              : null,
        ),
        child: Row(
          children: [
            Icon(
              icon,
              size: 18,
              color: isSelected ? AppTheme.primary : AppTheme.textSecondary,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  color: isSelected ? AppTheme.primary : AppTheme.textPrimary,
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmLogout(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceElevated,
        title: const Text('Confirm Logout', style: TextStyle(fontSize: 16)),
        content: const Text('Are you sure you want to log out of UniVision?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
            onPressed: () {
              Navigator.pop(ctx);
              client.logout();
            },
            child: const Text('Log Out'),
          ),
        ],
      ),
    );
  }

  Color _getRoleColor(String role) {
    switch (role) {
      case 'admin':
        return AppTheme.primary;
      case 'teacher':
        return AppTheme.success;
      case 'student':
        return const Color(0xFFA855F7);
      default:
        return AppTheme.primary;
    }
  }

  IconData _getRoleIcon(String role) {
    switch (role) {
      case 'admin':
        return Icons.security_rounded;
      case 'teacher':
        return Icons.school_rounded;
      case 'student':
        return Icons.person_rounded;
      default:
        return Icons.security_rounded;
    }
  }

  String _getRoleBadge(String role, String rollNo) {
    switch (role) {
      case 'admin':
        return 'ADMINISTRATOR';
      case 'teacher':
        return 'FACULTY TEACHER';
      case 'student':
        return rollNo.isNotEmpty ? 'STUDENT • $rollNo' : 'STUDENT';
      default:
        return 'GUEST';
    }
  }
}
