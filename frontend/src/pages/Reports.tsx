import React, { useState } from 'react';
import { 
  Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Chip, TextField, MenuItem, Button
} from '@mui/material';
import { Download, FilterList } from '@mui/icons-material';

interface AttendanceRecord {
  id: number;
  studentName: string;
  studentId: string;
  course: string;
  date: string;
  time: string;
  status: 'PRESENT' | 'ABSENT' | 'MANUAL';
}

export default function Reports() {
  const [filter, setFilter] = useState('Today');
  
  // Mock data
  const records: AttendanceRecord[] = [
    { id: 1, studentName: 'Muhammad Hamza', studentId: 'SE-08', course: 'Software Architecture', date: '2023-10-05', time: '08:31 AM', status: 'PRESENT' },
    { id: 2, studentName: 'Ali Khan', studentId: 'CS-12', course: 'Data Structures', date: '2023-10-05', time: '09:05 AM', status: 'PRESENT' },
    { id: 3, studentName: 'Sara Ahmed', studentId: 'SE-15', course: 'Software Architecture', date: '2023-10-05', time: '-', status: 'ABSENT' },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight="bold">Attendance Reports</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField 
            select 
            size="small" 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            sx={{ width: 150, bgcolor: 'white' }}
          >
            <MenuItem value="Today">Today</MenuItem>
            <MenuItem value="This Week">This Week</MenuItem>
            <MenuItem value="This Month">This Month</MenuItem>
          </TextField>
          <Button variant="outlined" startIcon={<FilterList />}>Filter</Button>
          <Button variant="contained" startIcon={<Download />}>Export CSV</Button>
        </Box>
      </Box>

      <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <Table>
          <TableHead sx={{ bgcolor: 'background.default' }}>
            <TableRow>
              <TableCell fontWeight="bold">Date</TableCell>
              <TableCell fontWeight="bold">Time</TableCell>
              <TableCell fontWeight="bold">Student Name</TableCell>
              <TableCell fontWeight="bold">Student ID</TableCell>
              <TableCell fontWeight="bold">Course</TableCell>
              <TableCell fontWeight="bold">Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {records.map((record) => (
              <TableRow key={record.id} hover>
                <TableCell>{record.date}</TableCell>
                <TableCell>{record.time}</TableCell>
                <TableCell fontWeight="medium">{record.studentName}</TableCell>
                <TableCell>{record.studentId}</TableCell>
                <TableCell>{record.course}</TableCell>
                <TableCell>
                  <Chip 
                    label={record.status} 
                    size="small"
                    color={
                      record.status === 'PRESENT' ? 'success' : 
                      record.status === 'ABSENT' ? 'error' : 'warning'
                    }
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
