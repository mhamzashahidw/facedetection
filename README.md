# FaceAttend AI

## Advanced AI Face Recognition Attendance Management System

**FaceAttend AI** is a professional, hybrid architecture (MVC + Event-Driven) Face Recognition Attendance System built for our Software Architecture and DSA academic project.

### Features
* **Hybrid Architecture:** Explicit separation of MVC components with Event-Driven background processing for notifications and data synchronization.
* **Modern Dashboard:** Built with React, Tailwind CSS, Recharts, and Lucide Icons.
* **Live Face Scanner:** Simulates and performs real-time face tracking.
* **DSA Integrated:** Employs Vector Searching, Hash Tables (in-memory caching), and Sorting for scalable face recognition operations.
* **Demo Mode:** Fully functional presentation mode allowing teachers to evaluate UI/UX flows without needing a webcam.
* **Role-Based Authentication:** JWT secured API.

### Technology Stack
* **Frontend:** React, TypeScript, Vite, Tailwind CSS, Recharts
* **Backend:** Python, FastAPI, SQLAlchemy
* **AI Engine:** DeepFace (OpenCV, NumPy)
* **Database:** SQLite

### Quick Start
**1. Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**2. Frontend**
```bash
cd frontend
npm install
npm run dev
```

### Academic Integrity
This project implements the requested Architectural styles clearly. The Event Bus is implemented in `backend/events/event_bus.py`, acting as a bridge between the FastAPI Controllers (MVC) and asynchronous database handlers.

*Demo Mode is available in the Live Scanner component for presentation.*
