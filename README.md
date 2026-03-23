# Review API

A Django REST Framework backend that automates document review using LLM providers. It detects text errors and financial discrepancies in uploaded documents, tracks review status.

## Features

- **Document review pipeline** — Upload files, queue review tasks via RabbitMQ, and track status through queued → reviewing → succeeded/failed states
- **Dual error detection** — Identifies text errors (with position data) and financial errors (cross-page, formula validation, period comparison)
- **LLM provider management** — Configure multiple LLM providers and prompts; run and export evaluation tests before promoting a configuration to production
- **Project-based access control** — Organize documents into projects with per-project viewer permissions; superusers see everything
- **JWT authentication** — Email verification code flow for registration; flexible token authentication (Bearer prefix optional)
- **Structured API responses** — All endpoints return a uniform `{ success, code, message, data }` envelope
- **Interactive API docs** — Swagger UI available at `/swagger/`

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5 + Django REST Framework |
| Authentication | `djangorestframework_simplejwt` |
| API Docs | `drf-yasg` (Swagger / ReDoc) |
| Database | PostgreSQL |
| Message Queue | RabbitMQ (via `pika`) |
| Cache | Redis |
| Config | `pydantic-settings` |
| Deployment | uWSGI + Docker |

## Project Structure

```
api/
├── app/
│   ├── base/           # Abstract base model, base view, base serializers
│   ├── doc/            # Document upload, review tasks, download
│   ├── error/          # Text errors and financial errors
│   ├── llm/            # LLM providers, prompts, test history
│   ├── project/        # Projects and viewer permissions
│   └── user/           # Registration, login, user/group management
├── common/
│   ├── http/           # BaseResponse, PaginationHelper, JWT auth
│   ├── server/         # RabbitMQ and Redis clients
│   └── utils/          # Logger, email verification
└── settings/           # Django settings and pydantic-settings config
```

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL
- RabbitMQ
- Redis

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd review_api

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
SECRET_KEY=your-secret-key
DEBUG=True

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=review_api
DB_USER=postgres
DB_PASSWORD=yourpassword

# RabbitMQ
MQ_HOST=localhost
MQ_PORT=5672
MQ_USERNAME=guest
MQ_PASSWORD=guest
MQ_VIRTUAL_HOST=/

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Email (for registration verification codes)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=465
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=yourpassword
```

### Database Setup

```bash
python manage.py migrate
```

### Running the Development Server

```bash
python manage.py runserver
```

API docs are available at `http://127.0.0.1:8000/swagger/`.

### Running Tests

```bash
python manage.py test api.app.user
```

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/user/register` | Register with email verification |
| POST | `/api/user/verify-code` | Send email verification code |
| POST | `/api/user/login` | Log in and receive JWT tokens |
| GET/POST | `/api/project/` | List or create projects |
| GET/DELETE | `/api/project/<id>` | List project documents or delete project |
| POST | `/api/doc/upload` | Upload files (returns UUIDs) |
| POST | `/api/doc/task` | Create a review task |
| POST | `/api/doc/retry` | Retry a failed review |
| GET | `/api/doc/list` | Review history |
| GET | `/api/doc/<id>` | Document detail |
| GET | `/api/doc/download/<id>` | Download original file |
| GET | `/api/error/list` | Text and financial errors for a document |
| GET/POST | `/api/llm/provider` | List or create LLM providers |
| GET/POST | `/api/llm/prompt` | List or create prompts |
| GET/POST | `/api/llm/test` | LLM evaluation history |
| GET | `/api/llm/test/export` | Export evaluation results |

## Key Design Decisions

- **Soft deletion** — All models inherit `BaseModel` with an `is_deleted` flag; records are never physically removed
- **Uniform response envelope** — `BaseResponse` utility class ensures every endpoint returns a consistent JSON structure
- **Centralized exception handling** — `BaseAPIView` catches authentication errors, permission errors, and unhandled exceptions, converting them to appropriate HTTP responses
- **Field-level error messages** — `BaseRequestValidationSerializer` injects field names into DRF error messages automatically, so clients always know which field failed
- **Separated upload and task creation** — File upload and review task creation are intentionally split into two endpoints to allow batch uploads before committing to a review run

## Docker Deployment

```bash
docker compose up --build
```

The application is served by uWSGI behind the Docker entrypoint defined in `entrypoint.sh`.
