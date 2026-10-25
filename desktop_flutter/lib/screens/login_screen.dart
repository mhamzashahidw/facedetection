import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import '../theme.dart';
import '../services/bridge_client.dart';

class LoginScreen extends StatefulWidget {
  final BridgeClient client;
  final File? rememberFile;

  const LoginScreen({super.key, required this.client, this.rememberFile});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  String _activeRole = 'admin';
  final TextEditingController _idCtrl = TextEditingController();
  final TextEditingController _pwdCtrl = TextEditingController();
  String? _errorMessage;
  bool _isLoading = false;
  bool _rememberMe = false;
  bool _obscurePassword = true;

  File get _rememberFile => widget.rememberFile ?? File('remembered_user.json');

  @override
  void initState() {
    super.initState();
    _loadRememberedCredentials();
  }

  void _loadRememberedCredentials() {
    try {
      final file = _rememberFile;
      if (file.existsSync()) {
        final content = file.readAsStringSync();
        if (content.trim().isNotEmpty) {
          final data = jsonDecode(content);
          if (data is Map<String, dynamic> && data['remember'] == true) {
            _rememberMe = true;
            if (data['role'] != null) _activeRole = data['role'].toString();
            if (data['identifier'] != null) _idCtrl.text = data['identifier'].toString();
            if (data['password'] != null) _pwdCtrl.text = data['password'].toString();
          }
        }
      }
    } catch (_) {}
  }

  @override
  void dispose() {
    _idCtrl.dispose();
    _pwdCtrl.dispose();
    super.dispose();
  }

  void _selectRole(String role) {
    setState(() {
      _activeRole = role;
      _errorMessage = null;
    });
  }

  Future<void> _submitLogin() async {
    final id = _idCtrl.text.trim();
    final pwd = _pwdCtrl.text.trim();

    if (id.isEmpty || pwd.isEmpty) {
      setState(() => _errorMessage = 'Please enter both username/roll number and password.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final success = await widget.client.login(
      identifier: id,
      password: pwd,
      role: _activeRole,
    );

    if (success) {
      // Handle Remember Me persistence synchronously and atomically
      try {
        final file = _rememberFile;
        if (_rememberMe) {
          file.writeAsStringSync(
            jsonEncode({
              'remember': true,
              'role': _activeRole,
              'identifier': id,
              'password': pwd,
            }),
            flush: true,
          );
        } else {
          if (file.existsSync()) {
            file.deleteSync();
          }
        }
      } catch (_) {}
    }

    if (!mounted) return;

    setState(() {
      _isLoading = false;
      if (!success) {
        _errorMessage =
            'Invalid credentials for ${_activeRole[0].toUpperCase()}${_activeRole.substring(1)}. Please check your details.';
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Container(
            width: 460,
            padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 32),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.border, width: 1),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.35),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header Logo & Branding
                Center(
                  child: Container(
                    width: 54,
                    height: 54,
                    decoration: BoxDecoration(
                      color: _getRoleColor().withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: _getRoleColor().withValues(alpha: 0.35), width: 1.5),
                    ),
                    child: Icon(_getRoleIcon(), color: _getRoleColor(), size: 28),
                  ),
                ),
                const SizedBox(height: 12),
                const Center(
                  child: Text(
                    'UNIVISION',
                    style: TextStyle(
                      color: AppTheme.primary,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 2,
                    ),
                  ),
                ),
                const Center(
                  child: Text(
                    'Biometric Station & Attendance Portal',
                    style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Role Selector Tabs
                const Text(
                  'Select Account Type:',
                  style: TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _buildRoleBtn('admin', 'Admin', Icons.security_rounded),
                    const SizedBox(width: 8),
                    _buildRoleBtn('teacher', 'Teacher', Icons.school_rounded),
                    const SizedBox(width: 8),
                    _buildRoleBtn('student', 'Student', Icons.person_rounded),
                  ],
                ),
                const SizedBox(height: 8),

                // Dynamic Role Description
                Text(
                  _getRoleDescription(),
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 11,
                    fontStyle: FontStyle.italic,
                  ),
                ),
                const SizedBox(height: 18),

                // Identifier Input
                Text(
                  _getIdLabel(),
                  style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 6),
                TextField(
                  controller: _idCtrl,
                  decoration: InputDecoration(
                    hintText: _getIdPlaceholder(),
                    prefixIcon: const Icon(Icons.badge_outlined, color: AppTheme.textMuted, size: 18),
                  ),
                  onSubmitted: (_) => _submitLogin(),
                ),
                const SizedBox(height: 14),

                // Password Input
                const Text(
                  'Password:',
                  style: TextStyle(color: AppTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 6),
                TextField(
                  controller: _pwdCtrl,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    hintText: 'Enter account password',
                    prefixIcon: const Icon(Icons.lock_outline_rounded, color: AppTheme.textMuted, size: 18),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                        color: AppTheme.textMuted,
                        size: 18,
                      ),
                      onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                    ),
                  ),
                  onSubmitted: (_) => _submitLogin(),
                ),
                const SizedBox(height: 10),

                // Remember Me Checkbox
                Row(
                  children: [
                    SizedBox(
                      width: 24,
                      height: 24,
                      child: Checkbox(
                        value: _rememberMe,
                        activeColor: _getRoleColor(),
                        checkColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                        side: const BorderSide(color: AppTheme.border, width: 1.5),
                        onChanged: (val) {
                          setState(() => _rememberMe = val ?? false);
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: () => setState(() => _rememberMe = !_rememberMe),
                      child: const Text(
                        'Remember Me',
                        style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const Spacer(),
                    Text(
                      'Station Secured',
                      style: TextStyle(
                        color: AppTheme.textMuted.withValues(alpha: 0.7),
                        fontSize: 11,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ),

                // Error Message Banner
                if (_errorMessage != null) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: AppTheme.error.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
                    ),
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: AppTheme.error, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],

                const SizedBox(height: 20),

                // Sign In Button
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _getRoleColor(),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: _isLoading ? null : _submitLogin,
                  child: _isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.login_rounded, size: 18),
                            SizedBox(width: 8),
                            Text('Sign In to UniVision', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                          ],
                        ),
                ),

                const SizedBox(height: 16),

                // Helpful Security / System Hint
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceSunken,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.shield_outlined, size: 15, color: AppTheme.textMuted),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _getSystemHelperHint(),
                          style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRoleBtn(String role, String label, IconData icon) {
    final bool isSelected = _activeRole == role;
    final color = isSelected ? _getRoleColor() : AppTheme.textSecondary;

    return Expanded(
      child: InkWell(
        onTap: () => _selectRole(role),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? _getRoleColor().withValues(alpha: 0.15) : AppTheme.surfaceSunken,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected ? _getRoleColor() : AppTheme.border,
              width: isSelected ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: color,
                  fontSize: 12,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getRoleColor() {
    switch (_activeRole) {
      case 'admin':
        return AppTheme.primary;
      case 'teacher':
        return AppTheme.success;
      case 'student':
        return const Color(0xFFA855F7); // Purple
      default:
        return AppTheme.primary;
    }
  }

  IconData _getRoleIcon() {
    switch (_activeRole) {
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

  String _getRoleDescription() {
    switch (_activeRole) {
      case 'admin':
        return 'Admin Console: Manage users, edit passwords, view logs, and configure biometrics.';
      case 'teacher':
        return 'Teacher Station: Start class sessions, live AI face HUD, and view student attendance.';
      case 'student':
        return 'Student Portal: Check your personal attendance records and verification status.';
      default:
        return '';
    }
  }

  String _getIdLabel() {
    switch (_activeRole) {
      case 'admin':
        return 'Admin Username or Email:';
      case 'teacher':
        return 'Teacher Email or Username:';
      case 'student':
        return 'Student Roll Number or Email:';
      default:
        return 'Username or Email:';
    }
  }

  String _getIdPlaceholder() {
    switch (_activeRole) {
      case 'admin':
        return 'e.g. admin or admin@univision.edu';
      case 'teacher':
        return 'e.g. teacher@school.edu or teacher';
      case 'student':
        return 'e.g. 2025(s)-SE-5 or 2024-CS-001';
      default:
        return 'Enter identifier';
    }
  }

  String _getSystemHelperHint() {
    switch (_activeRole) {
      case 'admin':
        return 'Default admin credentials: admin / admin123';
      case 'teacher':
        return 'Faculty accounts: teacher / teacher123';
      case 'student':
        return 'Student accounts: 2024-CS-001 / student123';
      default:
        return 'Use your institution credentials to sign in.';
    }
  }
}
