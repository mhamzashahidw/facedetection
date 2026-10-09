import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Box, Drawer, List, ListItem, ListItemIcon, ListItemText, Typography, AppBar, Toolbar, IconButton, Avatar } from '@mui/material';
import { CameraAlt, Dashboard as DashboardIcon, People, Assessment, Logout, Settings } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

const drawerWidth = 240;

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Live Scanner', icon: <CameraAlt />, path: '/attendance/live' },
    { text: 'Students', icon: <People />, path: '/students' },
    { text: 'Reports', icon: <Assessment />, path: '/reports' },
  ];

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <AppBar position="fixed" sx={{ width: `calc(100% - ${drawerWidth}px)`, ml: `${drawerWidth}px`, bgcolor: 'white', color: 'text.primary', boxShadow: 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Overview
          </Typography>
          <IconButton>
            <Settings />
          </IconButton>
        </Toolbar>
      </AppBar>
      
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant="permanent"
        anchor="left"
      >
        <Toolbar sx={{ display: 'flex', alignItems: 'center', px: 2 }}>
          <CameraAlt color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6" fontWeight="bold">
            FaceAttend<Typography component="span" color="primary" variant="h6" fontWeight="bold">AI</Typography>
          </Typography>
        </Toolbar>
        
        <List sx={{ flexGrow: 1, pt: 2 }}>
          {menuItems.map((item) => (
            <ListItem button key={item.text} onClick={() => navigate(item.path)}>
              <ListItemIcon sx={{ color: 'primary.main' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
        
        <Box sx={{ p: 2, borderTop: '1px solid #e0e0e0' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar sx={{ bgcolor: 'primary.light', mr: 2 }}>
              {user?.full_name?.charAt(0) || 'U'}
            </Avatar>
            <Box>
              <Typography variant="subtitle2">{user?.full_name || 'User'}</Typography>
              <Typography variant="caption" color="text.secondary">{user?.role || 'Role'}</Typography>
            </Box>
          </Box>
          <ListItem button onClick={handleLogout} sx={{ borderRadius: 1, color: 'error.main', '&:hover': { bgcolor: 'error.light', color: 'white' } }}>
            <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
              <Logout />
            </ListItemIcon>
            <ListItemText primary="Sign Out" />
          </ListItem>
        </Box>
      </Drawer>
      
      <Box component="main" sx={{ flexGrow: 1, bgcolor: 'background.default', p: 3, mt: 8, overflowY: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  );
}
