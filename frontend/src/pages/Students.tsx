import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Webcam from 'react-webcam';
import { 
  Box, Typography, Paper, Button, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Dialog, DialogTitle, DialogContent, DialogActions, 
  TextField, Chip, IconButton, CircularProgress, Alert, Snackbar
} from '@mui/material';
import { Add, CameraAlt, Delete } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

interface Student {
  id: number;
  student_id_number: string;
  department: string;
  program: string;
  semester: number;
  section: string;
}

export default function Students() {
  const [students, setStudents] = useState<Student[]>([]);
  const [openModal, setOpenModal] = useState(false);
  const [enrollModal, setEnrollModal] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [newStudent, setNewStudent] = useState({
    student_id_number: '', department: '', program: '', semester: 1, section: ''
  });
  
  const [enrollStatus, setEnrollStatus] = useState<'idle' | 'capturing' | 'enrolling'>('idle');
  const [images, setImages] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const webcamRef = useRef<Webcam>(null);
  const { token } = useAuth();

  // Fetch real students
  const fetchStudents = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/students', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStudents(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleSave = async () => {
    try {
      await axios.post('http://localhost:8000/api/students', newStudent, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOpenModal(false);
      setSuccessMsg('Student added successfully!');
      fetchStudents();
      setNewStudent({ student_id_number: '', department: '', program: '', semester: 1, section: '' });
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to add student');
    }
  };

  const handleEnrollClick = (student: Student) => {
    setSelectedStudent(student);
    setImages([]);
    setEnrollStatus('idle');
    setEnrollModal(true);
  };

  const captureImagesForEnrollment = async () => {
    if (!webcamRef.current) return;
    setEnrollStatus('capturing');
    
    const tempImages: string[] = [];
    
    // Async recursive function to validate frame by frame
    const captureNextFrame = async (currentStep: number) => {
      if (currentStep >= 5) {
        submitEnrollment(tempImages);
        return;
      }

      const imageSrc = webcamRef.current?.getScreenshot();
      if (!imageSrc) {
        setTimeout(() => captureNextFrame(currentStep), 500);
        return;
      }

      const b64 = imageSrc.split(',')[1];
      
      try {
        const res = await axios.post('http://localhost:8000/api/face/validate_frame', {
          image_base64: b64
        });
        
        if (res.data.status === 'SUCCESS') {
          // Face detected! Add it, and advance to next step.
          tempImages.push(b64);
          setImages([...tempImages]);
          
          // Wait 1.5 seconds to give user time to read the NEXT instruction before snapping
          setTimeout(() => captureNextFrame(currentStep + 1), 1500);
        } else {
          // No face detected (camera covered or bad angle). Try again in 500ms without advancing.
          setTimeout(() => captureNextFrame(currentStep), 500);
        }
      } catch (err) {
        setTimeout(() => captureNextFrame(currentStep), 500);
      }
    };

    captureNextFrame(0);
  };

  const submitEnrollment = async (b64Images: string[]) => {
    if (!selectedStudent) return;
    
    setEnrollStatus('enrolling');
    try {
      await axios.post('http://localhost:8000/api/face/enroll', {
        student_id: selectedStudent.id,
        images_base64: b64Images
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccessMsg(`Face enrolled successfully for ${selectedStudent.student_id_number}!`);
      setEnrollModal(false);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Enrollment failed');
      setEnrollStatus('idle');
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight="bold">Students Management</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setOpenModal(true)}>
          Add Student
        </Button>
      </Box>

      <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <Table>
          <TableHead sx={{ bgcolor: 'background.default' }}>
            <TableRow>
              <TableCell fontWeight="bold">Student ID</TableCell>
              <TableCell fontWeight="bold">Department</TableCell>
              <TableCell fontWeight="bold">Program</TableCell>
              <TableCell fontWeight="bold">Semester</TableCell>
              <TableCell fontWeight="bold">Section</TableCell>
              <TableCell align="right" fontWeight="bold">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {students.map((student) => (
              <TableRow key={student.id} hover>
                <TableCell><Chip label={student.student_id_number} color="primary" variant="outlined" size="small" /></TableCell>
                <TableCell>{student.department}</TableCell>
                <TableCell>{student.program}</TableCell>
                <TableCell>{student.semester}</TableCell>
                <TableCell>{student.section}</TableCell>
                <TableCell align="right">
                  <Button size="small" startIcon={<CameraAlt />} color="secondary" sx={{ mr: 1 }} onClick={() => handleEnrollClick(student)}>
                    Enroll Face
                  </Button>
                  <IconButton size="small" color="error">
                    <Delete fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {students.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  No students registered yet. Click "Add Student".
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add Student Dialog */}
      <Dialog open={openModal} onClose={() => setOpenModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Register New Student</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mt: 1 }}>
            <TextField label="Student ID (e.g. SE-08)" fullWidth value={newStudent.student_id_number} onChange={(e) => setNewStudent({...newStudent, student_id_number: e.target.value})} />
            <TextField label="Department" fullWidth value={newStudent.department} onChange={(e) => setNewStudent({...newStudent, department: e.target.value})} />
            <TextField label="Program" fullWidth value={newStudent.program} onChange={(e) => setNewStudent({...newStudent, program: e.target.value})} />
            <TextField label="Semester" type="number" fullWidth value={newStudent.semester} onChange={(e) => setNewStudent({...newStudent, semester: parseInt(e.target.value)})} />
            <TextField label="Section" fullWidth value={newStudent.section} onChange={(e) => setNewStudent({...newStudent, section: e.target.value})} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenModal(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Face Enrollment Dialog */}
      <Dialog open={enrollModal} onClose={() => enrollStatus === 'idle' && setEnrollModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ textAlign: 'center', fontWeight: 'bold' }}>
          Biometric Enrollment
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', pb: 4 }}>
          {enrollStatus === 'idle' && (
            <Typography variant="body1" color="text.secondary" mb={3} textAlign="center">
              We need to capture a 3D structural map of your face. <br/>Follow the on-screen instructions carefully.
            </Typography>
          )}

          <Box sx={{ position: 'relative', width: '100%', maxWidth: 350, borderRadius: '50%', overflow: 'hidden', border: `4px solid ${enrollStatus === 'enrolling' ? '#22c55e' : '#0ea5e9'}`, aspectRatio: '1/1', display: 'flex', justifyContent: 'center', alignItems: 'center', bgcolor: '#0f172a', mb: 3 }}>
            <Webcam
              audio={false}
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              screenshotQuality={1}
              videoConstraints={{ facingMode: "user", width: 1280, height: 720 }}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
            {/* Scanner Overlay */}
            {enrollStatus === 'capturing' && (
              <Box sx={{ position: 'absolute', inset: 0, background: 'linear-gradient(transparent 50%, rgba(14, 165, 233, 0.4) 50%)', backgroundSize: '100% 4px', animation: 'scan 2s linear infinite' }} />
            )}
          </Box>

          <Box sx={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {enrollStatus === 'idle' && (
              <Button onClick={captureImagesForEnrollment} variant="contained" color="primary" size="large" sx={{ borderRadius: 8, px: 4, py: 1.5, fontWeight: 'bold' }}>
                Begin Scan
              </Button>
            )}
            
            {enrollStatus === 'capturing' && (
              <Typography variant="h6" fontWeight="bold" color="primary" sx={{ animation: 'pulse 1.5s infinite' }}>
                {images.length === 0 && "1. Look straight at the camera"}
                {images.length === 1 && "2. Turn your head slightly LEFT"}
                {images.length === 2 && "3. Turn your head slightly RIGHT"}
                {images.length === 3 && "4. Tilt your head slightly UP"}
                {images.length === 4 && "5. Tilt your head slightly DOWN"}
              </Typography>
            )}

            {enrollStatus === 'enrolling' && (
              <Typography color="success.main" variant="h6" fontWeight="bold" display="flex" alignItems="center">
                <CircularProgress size={24} color="success" sx={{ mr: 2 }}/> Processing 128D Vector...
              </Typography>
            )}
          </Box>
        </DialogContent>
      </Dialog>


      <Snackbar open={!!errorMsg} autoHideDuration={6000} onClose={() => setErrorMsg('')}>
        <Alert severity="error" onClose={() => setErrorMsg('')}>{errorMsg}</Alert>
      </Snackbar>
      <Snackbar open={!!successMsg} autoHideDuration={6000} onClose={() => setSuccessMsg('')}>
        <Alert severity="success" onClose={() => setSuccessMsg('')}>{successMsg}</Alert>
      </Snackbar>
    </Box>
  );
}
