import 'package:flutter/material.dart';
import '../theme.dart';
import '../services/bridge_client.dart';

class UserManagementScreen extends StatefulWidget {
  final BridgeClient client;

  const UserManagementScreen({super.key, required this.client});

  @override
  State<UserManagementScreen> createState() => _UserManagementScreenState();
}

class _UserManagementScreenState extends State<UserManagementScreen> {
  final TextEditingController _searchCtrl = TextEditingController();
  String _selectedRoleFilter = 'ALL';
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    widget.client.addListener(_onClientUpdated);
    widget.client.loadUsers();
  }

  @override
  void dispose() {
    widget.client.removeListener(_onClientUpdated);
    _searchCtrl.dispose();
    super.dispose();
  }

  void _onClientUpdated() {
    if (mounted) setState(() {});
  }

  void _showCreateUserDialog() {
    final nameCtrl = TextEditingController();
    final userCtrl = TextEditingController();
    final emailCtrl = TextEditingController();
    final rollCtrl = TextEditingController();
    final pwdCtrl = TextEditingController();
    final confirmPwdCtrl = TextEditingController();

    String selectedRole = 'student';
    bool obscurePwd = true;
    bool obscureConfirm = true;
    String? dialogError;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          final isStudent = selectedRole == 'student';

          return AlertDialog(
            backgroundColor: AppTheme.surfaceElevated,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.person_add_rounded, color: AppTheme.primary, size: 20),
                ),
                const SizedBox(width: 12),
                const Text(
                  'Create New User Account',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
              ],
            ),
            content: SizedBox(
              width: 480,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (dialogError != null)
                      Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppTheme.error.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.error.withValues(alpha: 0.4)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.error_outline, size: 16, color: AppTheme.error),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(dialogError!, style: const TextStyle(color: AppTheme.error, fontSize: 12)),
                            ),
                          ],
                        ),
                      ),

                    // Role selection
                    const Text('ACCOUNT ROLE',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                    const SizedBox(height: 6),
                    DropdownButtonFormField<String>(
                      value: selectedRole,
                      dropdownColor: AppTheme.surfaceElevated,
                      decoration: const InputDecoration(isDense: true),
                      items: const [
                        DropdownMenuItem(value: 'student', child: Text('Student (Enrolled)')),
                        DropdownMenuItem(value: 'teacher', child: Text('Teacher (Faculty)')),
                        DropdownMenuItem(value: 'admin', child: Text('Administrator (System)')),
                      ],
                      onChanged: (val) {
                        if (val != null) {
                          setDialogState(() {
                            selectedRole = val;
                            if (val == 'student' && userCtrl.text.isNotEmpty && rollCtrl.text.isEmpty) {
                              rollCtrl.text = userCtrl.text;
                            }
                          });
                        }
                      },
                    ),
                    const SizedBox(height: 14),

                    // Full Name
                    const Text('FULL NAME',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: nameCtrl,
                      decoration: const InputDecoration(
                        hintText: 'e.g. John Doe',
                        prefixIcon: Icon(Icons.badge_outlined, size: 18),
                        isDense: true,
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Username / Roll No
                    Text(isStudent ? 'ROLL NUMBER / USERNAME' : 'USERNAME',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: userCtrl,
                      decoration: InputDecoration(
                        hintText: isStudent ? 'e.g. 2026-CS-042' : 'e.g. jdoe',
                        prefixIcon: const Icon(Icons.account_circle_outlined, size: 18),
                        isDense: true,
                      ),
                      onChanged: (val) {
                        if (isStudent && rollCtrl.text.isEmpty) {
                          setDialogState(() => rollCtrl.text = val);
                        }
                      },
                    ),
                    const SizedBox(height: 14),

                    // Email Address
                    const Text('EMAIL ADDRESS',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: emailCtrl,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(
                        hintText: 'e.g. user@univision.edu',
                        prefixIcon: Icon(Icons.email_outlined, size: 18),
                        isDense: true,
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Password
                    const Text('PASSWORD',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: pwdCtrl,
                      obscureText: obscurePwd,
                      decoration: InputDecoration(
                        hintText: 'Minimum 4 characters',
                        prefixIcon: const Icon(Icons.lock_outline_rounded, size: 18),
                        suffixIcon: IconButton(
                          icon: Icon(obscurePwd ? Icons.visibility_off : Icons.visibility, size: 18),
                          onPressed: () => setDialogState(() => obscurePwd = !obscurePwd),
                        ),
                        isDense: true,
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Confirm Password
                    const Text('CONFIRM PASSWORD',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: confirmPwdCtrl,
                      obscureText: obscureConfirm,
                      decoration: InputDecoration(
                        hintText: 'Re-enter password',
                        prefixIcon: const Icon(Icons.lock_outline_rounded, size: 18),
                        suffixIcon: IconButton(
                          icon: Icon(obscureConfirm ? Icons.visibility_off : Icons.visibility, size: 18),
                          onPressed: () => setDialogState(() => obscureConfirm = !obscureConfirm),
                        ),
                        isDense: true,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Cancel'),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
                icon: const Icon(Icons.check_rounded, size: 18),
                label: const Text('Create User'),
                onPressed: () async {
                  final name = nameCtrl.text.trim();
                  final user = userCtrl.text.trim();
                  final email = emailCtrl.text.trim();
                  final pwd = pwdCtrl.text.trim();
                  final confirm = confirmPwdCtrl.text.trim();

                  if (name.isEmpty || user.isEmpty) {
                    setDialogState(() => dialogError = 'Please provide full name and username.');
                    return;
                  }
                  if (pwd.length < 4) {
                    setDialogState(() => dialogError = 'Password must be at least 4 characters long.');
                    return;
                  }
                  if (pwd != confirm) {
                    setDialogState(() => dialogError = 'Passwords do not match.');
                    return;
                  }

                  final success = await widget.client.createUser(
                    username: user,
                    email: email.isNotEmpty ? email : '$user@univision.edu',
                    password: pwd,
                    role: selectedRole,
                    fullName: name,
                    rollNo: isStudent ? (rollCtrl.text.trim().isNotEmpty ? rollCtrl.text.trim() : user) : null,
                  );

                  if (ctx.mounted) {
                    if (success) {
                      Navigator.pop(ctx);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          backgroundColor: AppTheme.success,
                          content: Text('User $name ($user) created successfully!'),
                        ),
                      );
                    } else {
                      setDialogState(() => dialogError = 'Could not create user. Username or email may already exist.');
                    }
                  }
                },
              ),
            ],
          );
        },
      ),
    );
  }

  void _showEditPasswordDialog(Map<String, dynamic> user) {
    final pwdCtrl = TextEditingController();
    final confirmCtrl = TextEditingController();
    bool obscurePwd = true;
    bool obscureConfirm = true;
    String? dialogError;

    final int userId = user['id'];
    final String fullName = user['full_name'] ?? 'User';
    final String username = user['username'] ?? '';
    final String role = (user['role'] ?? 'student').toString().toUpperCase();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: AppTheme.surfaceElevated,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.warning.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.key_rounded, color: AppTheme.warning, size: 20),
              ),
              const SizedBox(width: 12),
              const Text(
                'Change User Password',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
              ),
            ],
          ),
          content: SizedBox(
            width: 420,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // User info header
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceSunken,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 18,
                        backgroundColor: _getRoleColor(role.toLowerCase()).withValues(alpha: 0.2),
                        child: Text(
                          fullName.isNotEmpty ? fullName[0].toUpperCase() : 'U',
                          style: TextStyle(fontWeight: FontWeight.bold, color: _getRoleColor(role.toLowerCase())),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              fullName,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.textPrimary),
                            ),
                            Text(
                              '$username • $role',
                              style: TextStyle(fontSize: 11, color: _getRoleColor(role.toLowerCase()), fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                if (dialogError != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.error.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.error.withValues(alpha: 0.4)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, size: 16, color: AppTheme.error),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(dialogError!, style: const TextStyle(color: AppTheme.error, fontSize: 12)),
                        ),
                      ],
                    ),
                  ),

                const Text('NEW PASSWORD',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                const SizedBox(height: 6),
                TextField(
                  controller: pwdCtrl,
                  obscureText: obscurePwd,
                  autofocus: true,
                  decoration: InputDecoration(
                    hintText: 'Enter new password (min 4 chars)',
                    prefixIcon: const Icon(Icons.lock_rounded, size: 18),
                    suffixIcon: IconButton(
                      icon: Icon(obscurePwd ? Icons.visibility_off : Icons.visibility, size: 18),
                      onPressed: () => setDialogState(() => obscurePwd = !obscurePwd),
                    ),
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 14),

                const Text('CONFIRM NEW PASSWORD',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                const SizedBox(height: 6),
                TextField(
                  controller: confirmCtrl,
                  obscureText: obscureConfirm,
                  decoration: InputDecoration(
                    hintText: 'Re-enter new password',
                    prefixIcon: const Icon(Icons.lock_rounded, size: 18),
                    suffixIcon: IconButton(
                      icon: Icon(obscureConfirm ? Icons.visibility_off : Icons.visibility, size: 18),
                      onPressed: () => setDialogState(() => obscureConfirm = !obscureConfirm),
                    ),
                    isDense: true,
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
              icon: const Icon(Icons.save_rounded, size: 16),
              label: const Text('Update Password'),
              onPressed: () async {
                final newPwd = pwdCtrl.text.trim();
                final confirm = confirmCtrl.text.trim();

                if (newPwd.length < 4) {
                  setDialogState(() => dialogError = 'Password must be at least 4 characters long.');
                  return;
                }
                if (newPwd != confirm) {
                  setDialogState(() => dialogError = 'Passwords do not match.');
                  return;
                }

                final success = await widget.client.updateUserPassword(
                  userId: userId,
                  newPassword: newPwd,
                );

                if (ctx.mounted) {
                  if (success) {
                    Navigator.pop(ctx);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        backgroundColor: AppTheme.success,
                        content: Text('Password updated successfully for $fullName!'),
                      ),
                    );
                  } else {
                    setDialogState(() => dialogError = 'Failed to update password. Please check network.');
                  }
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showEditUserDialog(Map<String, dynamic> user) {
    final nameCtrl = TextEditingController(text: user['full_name'] ?? '');
    final emailCtrl = TextEditingController(text: user['email'] ?? '');
    final rollCtrl = TextEditingController(text: user['roll_no'] ?? user['username'] ?? '');
    final int userId = user['id'];
    final bool isStudent = (user['role'] ?? '').toString().toLowerCase() == 'student';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceElevated,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Edit User Profile', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        content: SizedBox(
          width: 400,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('FULL NAME', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
              const SizedBox(height: 6),
              TextField(controller: nameCtrl, decoration: const InputDecoration(isDense: true)),
              const SizedBox(height: 14),
              const Text('EMAIL', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
              const SizedBox(height: 6),
              TextField(controller: emailCtrl, decoration: const InputDecoration(isDense: true)),
              if (isStudent) ...[
                const SizedBox(height: 14),
                const Text('ROLL NUMBER', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
                const SizedBox(height: 6),
                TextField(controller: rollCtrl, decoration: const InputDecoration(isDense: true)),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
            onPressed: () async {
              Navigator.pop(ctx);
              await widget.client.updateUser(
                userId: userId,
                fullName: nameCtrl.text.trim(),
                email: emailCtrl.text.trim(),
                rollNo: isStudent ? rollCtrl.text.trim() : null,
              );
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('User profile updated successfully!')),
                );
              }
            },
            child: const Text('Save Changes'),
          ),
        ],
      ),
    );
  }

  void _confirmDeleteUser(Map<String, dynamic> user) {
    final int userId = user['id'];
    final String name = user['full_name'] ?? 'User';
    final currentAdminId = widget.client.currentUser?['id'];

    if (userId == currentAdminId) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: AppTheme.error,
          content: Text('Cannot delete your own currently logged in administrator account.'),
        ),
      );
      return;
    }

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceElevated,
        title: const Text('Delete User Account', style: TextStyle(fontSize: 16)),
        content: Text('Are you sure you want to delete account for $name? This action cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
            onPressed: () async {
              Navigator.pop(ctx);
              final ok = await widget.client.deleteUser(userId);
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(ok ? 'Account deleted.' : 'Failed to delete user.')),
                );
              }
            },
            child: const Text('Delete Account'),
          ),
        ],
      ),
    );
  }

  Color _getRoleColor(String role) {
    switch (role.toLowerCase()) {
      case 'admin':
        return AppTheme.primary;
      case 'teacher':
        return const Color(0xFFF59E0B);
      case 'student':
        return AppTheme.success;
      default:
        return AppTheme.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    final String query = _searchCtrl.text.trim().toLowerCase();
    final users = widget.client.users.where((u) {
      final role = (u['role'] ?? '').toString().toLowerCase();
      if (_selectedRoleFilter != 'ALL' && role != _selectedRoleFilter.toLowerCase()) {
        return false;
      }
      if (query.isEmpty) return true;
      final name = (u['full_name'] ?? '').toString().toLowerCase();
      final username = (u['username'] ?? '').toString().toLowerCase();
      final roll = (u['roll_no'] ?? '').toString().toLowerCase();
      final email = (u['email'] ?? '').toString().toLowerCase();
      return name.contains(query) || username.contains(query) || roll.contains(query) || email.contains(query);
    }).toList();

    final totalCount = widget.client.users.length;
    final studentCount = widget.client.users.where((u) => u['role'] == 'student').length;
    final teacherCount = widget.client.users.where((u) => u['role'] == 'teacher').length;
    final adminCount = widget.client.users.where((u) => u['role'] == 'admin').length;

    return Column(
      children: [
        // 1. Top KPI Summary Cards
        Row(
          children: [
            _buildStatCard('TOTAL ACCOUNTS', '$totalCount Users', Icons.people_alt_rounded, AppTheme.primary),
            const SizedBox(width: 14),
            _buildStatCard('STUDENTS', '$studentCount Enrolled', Icons.school_rounded, AppTheme.success),
            const SizedBox(width: 14),
            _buildStatCard('FACULTY TEACHERS', '$teacherCount Faculty', Icons.co_present_rounded, const Color(0xFFF59E0B)),
            const SizedBox(width: 14),
            _buildStatCard('ADMINISTRATORS', '$adminCount Admins', Icons.shield_rounded, const Color(0xFFA855F7)),
          ],
        ),
        const SizedBox(height: 16),

        // 2. Main Container
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header & Action Bar
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      const Icon(Icons.admin_panel_settings_rounded, color: AppTheme.primary, size: 22),
                      const SizedBox(width: 10),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'User & Password Management',
                            style: TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          SizedBox(height: 2),
                          Text(
                            'Create student & faculty accounts and edit passwords on station and cloud.',
                            style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                          ),
                        ],
                      ),
                      const SizedBox(width: 24),

                      // Role Filter Chips
                      Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceSunken,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.border),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            _buildFilterTab('ALL', 'All'),
                            _buildFilterTab('STUDENT', 'Students'),
                            _buildFilterTab('TEACHER', 'Teachers'),
                            _buildFilterTab('ADMIN', 'Admins'),
                          ],
                        ),
                      ),
                      const SizedBox(width: 14),

                      // Search Field
                      SizedBox(
                        width: 180,
                        height: 36,
                        child: TextField(
                          controller: _searchCtrl,
                          onChanged: (_) => setState(() {}),
                          style: const TextStyle(fontSize: 12),
                          decoration: InputDecoration(
                            hintText: 'Search user...',
                            prefixIcon: const Icon(Icons.search, size: 16, color: AppTheme.textMuted),
                            suffixIcon: _searchCtrl.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.clear, size: 14),
                                    onPressed: () {
                                      _searchCtrl.clear();
                                      setState(() {});
                                    },
                                  )
                                : null,
                            contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 10),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),

                      // Refresh Button
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        ),
                        onPressed: () => widget.client.loadUsers(),
                        icon: const Icon(Icons.refresh, size: 15, color: AppTheme.textPrimary),
                        label: const Text('Refresh', style: TextStyle(fontSize: 11)),
                      ),
                      const SizedBox(width: 10),

                      // Create User Button
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.primary,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        ),
                        onPressed: _showCreateUserDialog,
                        icon: const Icon(Icons.person_add_rounded, size: 16),
                        label: const Text('Create User', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Table Header
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceSunken,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: const Row(
                    children: [
                      SizedBox(width: 50, child: Text('#', style: _headerStyle)),
                      Expanded(flex: 3, child: Text('Full Name', style: _headerStyle)),
                      Expanded(flex: 2, child: Text('Username / Roll No', style: _headerStyle)),
                      Expanded(flex: 3, child: Text('Email Address', style: _headerStyle)),
                      SizedBox(width: 110, child: Text('Role', style: _headerStyle)),
                      SizedBox(width: 120, child: Text('Actions', textAlign: TextAlign.end, style: _headerStyle)),
                    ],
                  ),
                ),
                const SizedBox(height: 8),

                // Table Content
                Expanded(
                  child: users.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.manage_accounts_outlined, size: 48, color: AppTheme.textMuted.withValues(alpha: 0.5)),
                              const SizedBox(height: 12),
                              const Text('No users match the search filter.',
                                  style: TextStyle(color: AppTheme.textMuted, fontSize: 13)),
                            ],
                          ),
                        )
                      : ListView.separated(
                          itemCount: users.length,
                          separatorBuilder: (_, __) => const Divider(height: 1, color: AppTheme.border),
                          itemBuilder: (context, index) {
                            final u = users[index];
                            final role = (u['role'] ?? 'student').toString().toLowerCase();
                            final roleColor = _getRoleColor(role);
                            final identifier = u['roll_no'] ?? u['username'] ?? '—';

                            return Container(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                              child: Row(
                                children: [
                                  SizedBox(
                                    width: 50,
                                    child: Text(
                                      '#${u['id'] ?? (index + 1)}',
                                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 12, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                  Expanded(
                                    flex: 3,
                                    child: Row(
                                      children: [
                                        CircleAvatar(
                                          radius: 14,
                                          backgroundColor: roleColor.withValues(alpha: 0.15),
                                          child: Text(
                                            (u['full_name'] ?? 'U')[0].toUpperCase(),
                                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: roleColor),
                                          ),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Text(
                                            u['full_name'] ?? 'Unknown User',
                                            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12, fontWeight: FontWeight.w600),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Expanded(
                                    flex: 2,
                                    child: Text(
                                      identifier,
                                      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12, fontWeight: FontWeight.w500),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  Expanded(
                                    flex: 3,
                                    child: Text(
                                      u['email'] ?? '—',
                                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  SizedBox(
                                    width: 110,
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                      decoration: BoxDecoration(
                                        color: roleColor.withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(color: roleColor.withValues(alpha: 0.3)),
                                      ),
                                      child: Text(
                                        role.toUpperCase(),
                                        textAlign: TextAlign.center,
                                        style: TextStyle(color: roleColor, fontSize: 10, fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                  ),
                                  SizedBox(
                                    width: 120,
                                    child: Row(
                                      mainAxisAlignment: MainAxisAlignment.end,
                                      children: [
                                        // Edit Password button
                                        IconButton(
                                          visualDensity: VisualDensity.compact,
                                          padding: EdgeInsets.zero,
                                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                                          tooltip: 'Edit / Reset Password',
                                          icon: const Icon(Icons.key_rounded, size: 16, color: AppTheme.warning),
                                          onPressed: () => _showEditPasswordDialog(u),
                                        ),
                                        // Edit Details button
                                        IconButton(
                                          visualDensity: VisualDensity.compact,
                                          padding: EdgeInsets.zero,
                                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                                          tooltip: 'Edit Profile Details',
                                          icon: const Icon(Icons.edit_rounded, size: 16, color: AppTheme.primary),
                                          onPressed: () => _showEditUserDialog(u),
                                        ),
                                        // Delete user button
                                        IconButton(
                                          visualDensity: VisualDensity.compact,
                                          padding: EdgeInsets.zero,
                                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                                          tooltip: 'Delete User Account',
                                          icon: const Icon(Icons.delete_outline_rounded, size: 16, color: AppTheme.error),
                                          onPressed: () => _confirmDeleteUser(u),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFilterTab(String roleKey, String label) {
    final bool isSelected = _selectedRoleFilter == roleKey;
    return InkWell(
      onTap: () => setState(() => _selectedRoleFilter = roleKey),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primary.withValues(alpha: 0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            color: isSelected ? AppTheme.primary : AppTheme.textMuted,
          ),
        ),
      ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.border),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      color: AppTheme.textMuted,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    style: TextStyle(
                      color: color,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static const TextStyle _headerStyle = TextStyle(
    color: AppTheme.textMuted,
    fontSize: 11,
    fontWeight: FontWeight.bold,
    letterSpacing: 0.5,
  );
}
