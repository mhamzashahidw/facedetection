import React, { useState } from 'react';
import { Box, Grid, Card, CardContent, Typography, Avatar } from '@mui/material';
import { People, VerifiedUser, GppBad, Timeline } from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { name: 'Mon', present: 120, absent: 10 },
  { name: 'Tue', present: 118, absent: 12 },
  { name: 'Wed', present: 125, absent: 5 },
  { name: 'Thu', present: 110, absent: 20 },
  { name: 'Fri', present: 128, absent: 2 },
];

export default function Dashboard() {
  const [stats] = useState({
    totalStudents: 150,
    presentToday: 128,
    absentToday: 22,
    attendanceRate: 85
  });

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar sx={{ bgcolor: 'primary.light', color: 'primary.main', mr: 2, width: 56, height: 56 }}>
                <People />
              </Avatar>
              <Box>
                <Typography color="text.secondary" variant="subtitle2">Total Students</Typography>
                <Typography variant="h5" fontWeight="bold">{stats.totalStudents}</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar sx={{ bgcolor: '#e8f5e9', color: '#2e7d32', mr: 2, width: 56, height: 56 }}>
                <VerifiedUser />
              </Avatar>
              <Box>
                <Typography color="text.secondary" variant="subtitle2">Present Today</Typography>
                <Typography variant="h5" fontWeight="bold">{stats.presentToday}</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar sx={{ bgcolor: '#ffebee', color: '#c62828', mr: 2, width: 56, height: 56 }}>
                <GppBad />
              </Avatar>
              <Box>
                <Typography color="text.secondary" variant="subtitle2">Absent Today</Typography>
                <Typography variant="h5" fontWeight="bold">{stats.absentToday}</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar sx={{ bgcolor: '#f3e5f5', color: '#7b1fa2', mr: 2, width: 56, height: 56 }}>
                <Timeline />
              </Avatar>
              <Box>
                <Typography color="text.secondary" variant="subtitle2">Attendance %</Typography>
                <Typography variant="h5" fontWeight="bold">{stats.attendanceRate}%</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2, height: '100%' }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" mb={2}>Weekly Attendance Trends</Typography>
              <Box sx={{ height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Line type="monotone" dataKey="present" stroke="#0ea5e9" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 8 }} />
                    <Line type="monotone" dataKey="absent" stroke="#f43f5e" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2, height: '100%' }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" mb={2}>Recent Activity</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {[1, 2, 3, 4, 5].map((_, i) => (
                  <Box key={i} sx={{ display: 'flex', alignItems: 'center', p: 1, '&:hover': { bgcolor: 'background.default', borderRadius: 1 } }}>
                    <Avatar sx={{ bgcolor: '#e8f5e9', color: '#2e7d32', width: 40, height: 40, mr: 2 }}>
                      <VerifiedUser fontSize="small" />
                    </Avatar>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">Muhammad Hamza (SE-08)</Typography>
                      <Typography variant="caption" color="text.secondary">Marked Present at 08:31 AM</Typography>
                    </Box>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
