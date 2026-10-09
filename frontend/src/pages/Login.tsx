import React, { useState } from 'react';
import { Box, Paper, Typography, TextField, Button, CircularProgress } from '@mui/material';
import { CameraAlt } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

import axios from 'axios';

export default function Login() {
  const [email, setEmail] = useState('admin@faceattend.ai');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      const res = await axios.post('http://localhost:8000/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      // Get user details
      const token = res.data.access_token;
      const userRes = await axios.get('http://localhost:8000/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      login(token, userRes.data);
      navigate('/dashboard');
    } catch (err: any) {
      setErrorMsg('Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box 
      sx={{ 
        display: 'flex', 
        height: '100vh', 
        alignItems: 'center', 
        justifyContent: 'center', 
        bgcolor: '#f0f9ff' 
      }}
    >
      <Paper 
        elevation={0} 
        sx={{ 
          p: 5, 
          borderRadius: 4, 
          width: '100%', 
          maxWidth: 400,
          border: '1px solid #e0e0e0',
          boxShadow: '0 10px 25px -5px rgb(0 0 0 / 0.1)'
        }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 4 }}>
          <Box sx={{ bgcolor: 'primary.main', p: 2, borderRadius: '50%', mb: 2 }}>
            <CameraAlt sx={{ color: 'white', fontSize: 32 }} />
          </Box>
          <Typography variant="h5" fontWeight="bold">
            FaceAttend<Typography component="span" color="primary" variant="h5" fontWeight="bold">AI</Typography>
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={1}>
            Sign in to the administration portal
          </Typography>
        </Box>

        <form onSubmit={handleLogin}>
          <TextField
            label="Email Address"
            variant="outlined"
            fullWidth
            margin="normal"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            variant="outlined"
            fullWidth
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          
          <Button
            type="submit"
            variant="contained"
            color="primary"
            fullWidth
            size="large"
            disabled={loading}
            sx={{ mt: 3, py: 1.5, fontWeight: 'bold' }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign In (Demo Mode)'}
          </Button>
        </form>
      </Paper>
    </Box>
  );
}
