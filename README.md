# Apex Library Management System (LMS)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-green.svg)](https://www.djangoproject.com/)
[![REST Framework](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)](https://getbootstrap.com/)
[![OpenShift](https://img.shields.io/badge/Red%20Hat-OpenShift-EE0000.svg)](https://www.redhat.com/en/technologies/cloud-computing/openshift)

An enterprise, production-ready Library Management System built with Python 3.12, Django 5.1, Django REST Framework, Bootstrap 5, HTMX, and PostgreSQL, containerized with Docker and prepared for Red Hat OpenShift deployment.

---

## Key Features & Functional Modules

1. **Role-Based Access Control (RBAC)**:
   - **Admin**: Full system management, staff accounts, configurations.
   - **Librarian**: Book catalog management, inventory copy tracking, issue and return circulation, fines collection, report generation.
   - **Student**: Catalog discovery, self-service book reservations, active loan tracking with due-date countdowns, borrowing history, fine status.
2. **Catalog & Inventory Management**:
   - Bibliographic metadata (ISBN, Authors, Categories, Publishers, Publication Year, Synopsis, Covers).
   - Physical copy tracking with accession barcodes, rack & shelf locations, condition grades, and availability states.
   - Real-time HTMX search & filter across titles, authors, ISBNs, and categories without page reloads.
3. **Circulation Engine**:
   - Automated checkout and check-in workflows.
   - Automated due-date calculations based on institutional policies.
   - Daily overdue fine accrual calculations.
   - Fine settlement tracking (Cash, Card, Online, Waived).
4. **Reservation Queue Management**:
   - Automated queue numbering and FIFO waitlist progression.
   - Automated copy allocation and pickup notifications when returned books are checked in.
5. **Analytics & Reporting**:
   - Interactive Chart.js visualizations (Category breakdown, 6-month borrowing volume trends).
   - Instant exports: PDF Overdue Loans Report (via ReportLab), CSV Book Catalog, and CSV Circulation Log.
6. **Progressive Web App (PWA)**:
   - Mobile-responsive layout, `manifest.json`, and service worker caching for offline resilience.
7. **REST APIs & OpenAPI 3.0**:
   - Comprehensive DRF endpoints with JWT Bearer authentication.
   - Interactive Swagger UI (`/api/docs/`) and ReDoc (`/api/redoc/`).

---

## Default Demo Accounts

The database comes pre-seeded with ready-to-test role accounts:

| Role | Username | Password | Member ID | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `AdminPass123!` | `ADM-2026-XXXX` | Full system access & admin |
| **Librarian** | `librarian` | `LibPass123!` | `LIB-2026-XXXX` | Circulation & inventory manager |
| **Student** | `student` | `StudentPass123!` | `STU-2026-XXXX` | Regular student borrower |

---

## Local Development Setup

### 1. Prerequisites
- Python 3.12+
- Git

### 2. Virtual Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd library-management-system

# Create and activate virtual environment
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Leave `DATABASE_URL` blank to use local SQLite development fallback, or provide a PostgreSQL connection URL).*

### 4. Database Migrations & Initial Seed Data
```bash
python manage.py migrate
python manage.py seed_data
```

### 5. Run Development Server
```bash
python manage.py runserver 8000
```
Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Running Automated Tests

Run the full automated test suite (Unit, Integration, and DRF API tests):
```bash
# Using Django test runner:
python manage.py test

# Using pytest:
pytest
```

---

## Containerization with Docker

### Run with Docker Compose (PostgreSQL 16 + Web App):
```bash
docker compose up --build -d
```
Access the application at [http://localhost:8000](http://localhost:8000).

---

## Red Hat OpenShift Deployment

The `openshift/` directory contains complete Kubernetes/OpenShift declarative manifests compliant with OpenShift `restricted-v2` Security Context Constraints (runs as non-root UID 1001 in root group 0).

### Deploying using the `oc` CLI:

```bash
# 1. Login to your OpenShift cluster
oc login <cluster-url> --token=<token>

# 2. Create the project/namespace
oc apply -f openshift/01-namespace.yaml
oc project library-system

# 3. Apply ConfigMaps and Secrets
oc apply -f openshift/02-configmap.yaml
oc apply -f openshift/03-secrets.yaml

# 4. Provision Persistent Volume Claims
oc apply -f openshift/04-pvc.yaml

# 5. Deploy PostgreSQL
oc apply -f openshift/05-postgres-deployment.yaml

# 6. Deploy Application & Expose via Route
oc apply -f openshift/06-app-deployment.yaml
oc apply -f openshift/07-service.yaml
oc apply -f openshift/08-route.yaml

# 7. Check Route URL
oc get route lms-route
```

---

## API Endpoints Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/auth/token/` | POST | Obtain JWT access and refresh token pair |
| `/api/v1/auth/token/refresh/` | POST | Refresh JWT access token |
| `/api/v1/auth/me/` | GET | Current authenticated user profile |
| `/api/v1/books/` | GET, POST | Book catalog CRUD |
| `/api/v1/copies/` | GET, POST | Inventory physical copies tracking |
| `/api/v1/circulation/issue/` | POST | Issue book copy to member |
| `/api/v1/circulation/return/` | POST | Return book copy & calculate fines |
| `/api/v1/reservations/reserve/` | POST | Place self-service student reservation |
| `/api/docs/` | GET | Interactive Swagger UI documentation |
| `/api/redoc/` | GET | ReDoc OpenAPI 3.0 specification |
