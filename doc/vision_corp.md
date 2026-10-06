# Corporate Portal — Architecture, Vision & API Handoff

## 1. Product Intent & Architecture

The Corporate Portal is an authenticated business operations workspace designed to model realistic corporate IT usage alongside SOC monitoring. It provides employees and administrators with a dedicated interface for operational metrics, team tasks, system health announcements, and account security.

All security-related telemetry (such as authentication attempts, SQL executions, and diagnostic commands) is recorded and forwarded to the SIEM.

---

## 2. User Experience & Flows

1. **Authentication**: Users sign in via branded login (`POST /api/corporate/auth/login`).
2. **Personal Dashboard**: Displays active business tasks, service statuses (Email, VPN, ERP, Database), and recent security audit notices.
3. **Administrator Operations View**: Displays organizational KPIs, workload distribution, and access review queues (`GET /api/corporate/admin/overview`).

---

## 3. Component Hierarchy

| Area | Key Components | Purpose |
| :--- | :--- | :--- |
| **App Shell** | `PortalLayout`, `TopBar`, `SideNav`, `GlobalToast` | Core layout and responsive navigation. |
| **Authentication** | `LoginPage`, `LoginForm`, `PasswordField` | User session initialization and validation. |
| **Dashboard** | `WelcomeCard`, `SystemStatusGrid`, `MyTasksCard`, `ActivityTimeline` | Operational status and assigned work queues. |
| **Admin Operations**| `OperationsKpis`, `TeamWorkload`, `AccessReviewCard` | Organization-wide administration and governance. |

---

## 4. REST API Contract

| Method | Endpoint | Purpose | Key Fields |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/corporate/auth/login` | Sign in & generate access token | `username`, `password` $\rightarrow$ `access_token`, `user` |
| `POST` | `/api/corporate/auth/logout` | Terminate session | `204 No Content` |
| `GET` | `/api/corporate/me` | Current user profile & permissions | `id`, `name`, `email`, `role`, `department`, `permissions[]` |
| `GET` | `/api/corporate/dashboard` | Consolidated dashboard payload | `system_summary`, `my_tasks`, `announcements`, `activity` |
| `GET` | `/api/corporate/systems` | Service availability statuses | `id`, `name`, `status`, `message` |
| `GET` | `/api/corporate/tasks` | User task list | `items[]` (`title`, `status`, `due_at`, `priority`) |
| `PATCH` | `/api/corporate/tasks/{id}` | Update task status | `status` (`todo`, `in_progress`, `completed`) |
| `GET` | `/api/corporate/admin/overview` | Admin KPI metrics | `kpis`, `team_workload`, `access_review_count` |
