# 🏗️ System Architecture - E-Library SaaS

## نظرة عامة على تدفق البيانات

```mermaid
flowchart TD
    A[المستخدم / Users] -->|HTTPS Request| B[Frontend - Flask Templates]
    B --> C[Flask Backend / Routes]
    C --> D{Authentication Layer<br/>Flask-Login}
    D -->|مصرح| E[Business Logic]
    D -->|غير مصرح| F[Redirect to Login]
    E --> G[(PostgreSQL Database)]
    E --> H[REST API Endpoints]
    H --> I[External Clients / Mobile Apps]
    
    G --> J[Users Table]
    G --> K[Books Table]
    G --> L[BorrowRecord Table]
    G --> M[Subscription Table]
    
    E --> N[Mock Payment Gateway]
    N --> L
    
    C --> O[Logging System]
    O --> P[Application Logs]
    
    Q[GitHub Actions CI/CD] -->|Auto Deploy| R[Render Cloud Platform]
    R --> B
    R --> G
