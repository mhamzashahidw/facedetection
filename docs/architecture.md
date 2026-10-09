# System Architecture

## Hybrid Architecture Approach

The system employs a **Hybrid Architecture** comprising two primary architectural styles:

1. **Model-View-Controller (MVC)**
2. **Event-Driven Architecture**

```mermaid
graph TD
    %% MVC Layer
    subgraph MVC Architecture
        View[React Frontend - View]
        Controller[FastAPI - Controller]
        Model[SQLAlchemy - Model]
        
        View -- HTTP Requests --> Controller
        Controller -- Data Access --> Model
        Model -- Entities --> Controller
        Controller -- JSON Responses --> View
    end

    %% Event-Driven Layer
    subgraph Event-Driven Architecture
        EventBus((Event Bus))
        AuditHandler[Audit Log Handler]
        AttendanceHandler[Attendance Handler]
        NotificationHandler[Notification Handler]
        
        Controller -- Publish Event --> EventBus
        EventBus -- Dispatch --> AuditHandler
        EventBus -- Dispatch --> AttendanceHandler
        EventBus -- Dispatch --> NotificationHandler
        
        AttendanceHandler -- Async Write --> Model
    end
    
    %% Real-time Link
    NotificationHandler -- WebSocket --> View
```

## How It Works
- **MVC:** Used for standard HTTP requests. For example, when a user wants to view the list of students, the View requests it from the Controller, which reads from the Model and returns the data.
- **Event-Driven:** Used to decouple heavy or side-effect operations. When a face is successfully recognized by the AI engine, the Face Controller does *not* directly write attendance. It publishes a `FaceRecognized` event. The Event Bus then dispatches this to the `AttendanceHandler`, which safely inserts the record into the database, handling duplicate checks asynchronously.
