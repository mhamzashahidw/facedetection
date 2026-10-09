import React, { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import { Box, Typography, Paper, Grid, Button, CircularProgress, Chip, Divider, Fade, Snackbar, Alert } from '@mui/material';
import { CameraAlt, CheckCircle, Cancel, FiberManualRecord, PersonSearch, DocumentScanner } from '@mui/icons-material';

// Session ID to group real-time scans
const SESSION_ID = "SESSION_" + Math.floor(Math.random() * 1000000);

export default function LiveScanner() {
  const webcamRef = useRef<Webcam>(null);
  const [status, setStatus] = useState<'idle' | 'scanning' | 'verified' | 'unknown'>('idle');
  const [scanResult, setScanResult] = useState<any>(null);
  const [isLive, setIsLive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // Timer for continuous scanning
  const scanInterval = useRef<NodeJS.Timeout | null>(null);

  const captureAndSend = useCallback(async () => {
    if (!webcamRef.current) return;
    
    // Capture base64 string
    const imageSrc = webcamRef.current.getScreenshot();
    if (!imageSrc) return;

    // Strip the "data:image/jpeg;base64," prefix for the backend
    const base64Data = imageSrc.split(',')[1];

    try {
      setStatus('scanning');
      const response = await axios.post('http://localhost:8000/api/face/recognize', {
        image_base64: base64Data,
        session_id: SESSION_ID
      });

      if (response.data.status === 'SUCCESS') {
        setStatus('verified');
        setScanResult(response.data);
        stopScanning(); // Pause scanning after a success to show result
        setTimeout(() => setStatus('idle'), 5000); // Reset UI after 5s
      } else {
        setStatus('unknown');
      }
    } catch (error: any) {
      console.error(error);
      // If it's just "Face could not be detected", we just go back to idle to scan again
      if (error.response?.data?.detail) {
          if (error.response.data.detail.includes("Face could not be detected")) {
              setStatus('idle');
              return;
          }
          setErrorMsg(error.response.data.detail);
      }
      setStatus('unknown');
    }
  }, [webcamRef]);

  const startScanning = () => {
    setIsLive(true);
    setStatus('idle');
    // Capture a frame every 2 seconds
    scanInterval.current = setInterval(captureAndSend, 2000);
  };

  const stopScanning = () => {
    setIsLive(false);
    if (scanInterval.current) {
      clearInterval(scanInterval.current);
    }
    setStatus('idle');
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold" sx={{ background: 'linear-gradient(45deg, #0ea5e9, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Enterprise Vision Scanner
          </Typography>
          <Typography variant="body2" color="text.secondary">Real-time biometrics connected to main server.</Typography>
        </Box>
        <Chip 
          icon={<FiberManualRecord sx={{ color: isLive ? '#4ade80' : '#f87171', fontSize: '14px !important' }} />} 
          label={isLive ? "LIVE STREAM ACTIVE" : "CAMERA PAUSED"} 
          variant="outlined"
          sx={{ borderColor: isLive ? '#4ade80' : '#f87171', color: isLive ? '#4ade80' : '#f87171', fontWeight: 'bold' }} 
        />
      </Box>

      <Grid container spacing={4}>
        {/* Main Camera View */}
        <Grid item xs={12} lg={8}>
          <Paper 
            elevation={24} 
            sx={{ 
              position: 'relative', 
              width: '100%', 
              aspectRatio: '16/9', 
              bgcolor: '#0f172a', 
              borderRadius: 4, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              border: isLive ? '4px solid #0ea5e9' : '4px solid #334155',
              overflow: 'hidden',
              boxShadow: isLive ? '0 0 40px rgba(14, 165, 233, 0.2)' : 'none',
              transition: 'all 0.3s ease'
            }}
          >
            {isLive ? (
              <>
                <Webcam
                  audio={false}
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  screenshotQuality={1}
                  videoConstraints={{ facingMode: "user", width: 1280, height: 720 }}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: status === 'scanning' ? 0.7 : 1 }}
                />
                
                {/* Real-world Scanning HUD Overlay */}
                <Box sx={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
                  <Box sx={{ position: 'absolute', top: '10%', left: '10%', width: 40, height: 40, borderTop: '3px solid #0ea5e9', borderLeft: '3px solid #0ea5e9' }} />
                  <Box sx={{ position: 'absolute', top: '10%', right: '10%', width: 40, height: 40, borderTop: '3px solid #0ea5e9', borderRight: '3px solid #0ea5e9' }} />
                  <Box sx={{ position: 'absolute', bottom: '10%', left: '10%', width: 40, height: 40, borderBottom: '3px solid #0ea5e9', borderLeft: '3px solid #0ea5e9' }} />
                  <Box sx={{ position: 'absolute', bottom: '10%', right: '10%', width: 40, height: 40, borderBottom: '3px solid #0ea5e9', borderRight: '3px solid #0ea5e9' }} />
                </Box>
                
                {status === 'scanning' && (
                  <Box sx={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', bgcolor: 'rgba(15, 23, 42, 0.6)' }}>
                    <DocumentScanner sx={{ color: '#0ea5e9', fontSize: 64, mb: 2, animation: 'pulse 1.5s infinite' }} />
                    <Typography variant="h6" color="white" fontWeight="bold">EXTRACTING EMBEDDINGS...</Typography>
                  </Box>
                )}
              </>
            ) : (
              <Box sx={{ textAlign: 'center', color: '#64748b' }}>
                <CameraAlt sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
                <Typography variant="h6">Camera Offline</Typography>
                <Typography variant="body2">Click 'Initialize Engine' to start scanning.</Typography>
              </Box>
            )}
          </Paper>

          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            {!isLive ? (
              <Button 
                variant="contained" 
                size="large"
                startIcon={<PersonSearch />}
                onClick={startScanning} 
                sx={{ flex: 1, py: 2, borderRadius: 2, background: 'linear-gradient(to right, #0ea5e9, #2563eb)' }}
              >
                Initialize AI Engine & Camera
              </Button>
            ) : (
              <Button 
                variant="outlined" 
                color="error" 
                size="large"
                onClick={stopScanning} 
                sx={{ flex: 1, py: 2, borderRadius: 2, borderWidth: 2 }}
              >
                Terminate Feed
              </Button>
            )}
          </Box>
        </Grid>

        {/* Real-time Diagnostics & Results */}
        <Grid item xs={12} lg={4}>
          <Paper elevation={0} sx={{ p: 3, borderRadius: 3, border: '1px solid #e2e8f0', mb: 3, bgcolor: '#ffffff' }}>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom color="text.secondary">Diagnostic Telemetry</Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Typography color="text.secondary" variant="body2">Model Backend</Typography>
              <Typography fontWeight="bold" variant="body2" color="primary">DeepFace Vector Search</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Typography color="text.secondary" variant="body2">Threshold (Cosine)</Typography>
              <Typography fontWeight="bold" variant="body2">0.60</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography color="text.secondary" variant="body2">Queue Status</Typography>
              <Typography fontWeight="bold" variant="body2" color="text.secondary">
                {status === 'scanning' ? 'PROCESSING' : 'IDLE'}
              </Typography>
            </Box>
          </Paper>

          <Fade in={true}>
            <Paper 
              elevation={status === 'verified' ? 10 : 0} 
              sx={{ 
                p: 4, borderRadius: 3, height: 320, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                bgcolor: status === 'verified' ? '#f0fdf4' : status === 'unknown' ? '#fef2f2' : '#f8fafc',
                border: '2px solid', borderColor: status === 'verified' ? '#86efac' : status === 'unknown' ? '#fecaca' : '#e2e8f0',
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
              }}
            >
              {status === 'idle' || status === 'scanning' ? (
                 <Box textAlign="center" color="text.disabled">
                   <Box sx={{ width: 80, height: 80, border: '2px dashed #cbd5e1', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', mx: 'auto', mb: 2 }}>
                     <PersonSearch sx={{ fontSize: 32 }} />
                   </Box>
                   <Typography fontWeight="medium">Awaiting Facial Data...</Typography>
                 </Box>
              ) : status === 'verified' ? (
                <Box textAlign="center" width="100%">
                  <CheckCircle sx={{ fontSize: 72, color: '#22c55e', mb: 2 }} />
                  <Typography variant="h5" fontWeight="900" color="#166534" mb={3} letterSpacing={1}>ACCESS GRANTED</Typography>
                  <Paper elevation={0} sx={{ p: 2, textAlign: 'left', borderRadius: 2, bgcolor: 'white', border: '1px solid #dcfce7' }}>
                    <Typography variant="caption" color="text.secondary" textTransform="uppercase" fontWeight="bold">Identified Subject</Typography>
                    <Typography variant="h6" fontWeight="bold" color="#1e293b">Student ID: {scanResult?.student_id || 'Matched'}</Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, pt: 2, borderTop: '1px dashed #e2e8f0' }}>
                      <Typography variant="caption" color="text.secondary">Confidence Match</Typography>
                      <Chip label={`${((scanResult?.similarity || 0) * 100).toFixed(1)}%`} color="success" size="small" sx={{ fontWeight: 'bold' }} />
                    </Box>
                  </Paper>
                </Box>
              ) : (
                <Box textAlign="center">
                  <Cancel sx={{ fontSize: 72, color: '#ef4444', mb: 2 }} />
                  <Typography variant="h5" fontWeight="900" color="#991b1b" mb={1}>UNKNOWN ENTITY</Typography>
                  <Typography variant="body2" color="text.secondary" mb={3}>No matching vectors found in database.</Typography>
                  <Chip label="ATTENDANCE DENIED" color="error" sx={{ fontWeight: 'bold', px: 2 }} />
                </Box>
              )}
            </Paper>
          </Fade>
        </Grid>
      </Grid>
      
      <Snackbar open={!!errorMsg} autoHideDuration={6000} onClose={() => setErrorMsg(null)}>
        <Alert severity="error" onClose={() => setErrorMsg(null)}>{errorMsg}</Alert>
      </Snackbar>
    </Box>
  );
}
