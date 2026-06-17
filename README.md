# Clinic Appointment Service

A Django REST Framework API for managing clinic appointments, doctors, patients, and payments — built so a small private clinic can stop running its booking on phone calls and paper notebooks.

---

## Table of Contents

- [Why This Project Exists](#why-this-project-exists)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [App Structure](#app-structure)
- [Data Models](#data-models)
- [Business Rules](#business-rules)
- [API Reference](#api-reference)
  - [Authentication](#authentication)
  - [Specializations](#specializations)
  - [Doctors & Slots](#doctors--slots)
  - [Users](#users)
  - [Appointments](#appointments)
  - [Payments](#payments)
  - [Documentation Endpoints](#documentation-endpoints)
- [Notifications (Telegram)](#notifications-telegram)
- [Scheduled Tasks](#scheduled-tasks)
- [Requirements](#requirements)
- [First Time Setup](#first-time-setup)
- [Full Docker Workflow](#full-docker-workflow)
- [Creating a New App](#creating-a-new-app)
- [Installing Packages](#installing-packages)
- [Common Commands](#common-commands)
- [Testing](#testing)
- [Git Workflow](#git-workflow)
- [Commit Message Format](#commit-message-format)

---

## Why This Project Exists

A small private clinic currently books appointments by phone and writes everything into paper notebooks. That causes real problems:

- Patients forget appointments because nothing reminds them.
- Doctors' schedules overlap because there's no shared source of truth for availability.
- Receptionists can't reliably track payments or apply late-cancellation fees.

This project replaces that process with an **online appointment management system**. Patients can register, browse doctors and their available time slots, book appointments, and cancel visits. Staff are automatically notified in **Telegram** about new bookings, cancellations, no-shows, and successful payments. Payments (consultations, cancellation fees, no-show fees) are processed through **Stripe**.

There is **no front-end** — the entire system is operated through the browsable Django REST Framework API (and is documented via Swagger so any future front-end team can integrate against it).

---

## Key Features

- **Specializations catalog** — admin-managed list of medical specializations (e.g. cardiology, dermatology).
- **Doctor & slot management** — doctors linked to specializations with a price per visit; time slots can be created one at a time or in bulk (e.g. "every 30 minutes from 09:00 to 17:00 on a given date").
- **Patient registration & JWT authentication** — email-based custom user model, with a non-standard `Authorize` header (instead of `Authorization`) to make manual testing easier with the ModHeader browser extension.
- **Appointment booking** — patients book a free slot; the system locks in the doctor's current price at booking time and rejects double-booking.
- **Cancel / Complete / No-Show workflow** — status transitions trigger the correct payment type automatically (consultation fee, cancellation fee, or no-show fee).
- **Automatic no-show detection** — a daily scheduled job marks any `BOOKED` appointment whose slot has already ended as `NO_SHOW`.
- **Stripe payments** — checkout sessions are created automatically for consultations, late-cancellation fees, and no-show fees; a webhook keeps payment status in sync with Stripe.
- **Telegram notifications** — clinic staff get a message for every new appointment, every status change, and every successful payment.
- **Swagger / OpenAPI documentation** — every endpoint is documented and explorable via `drf-spectacular`.
- **Dockerized from day one** — Postgres, Redis, the Django API, Celery worker, Celery Beat scheduler, a Flower dashboard for task monitoring, and the Stripe CLI (for forwarding webhooks locally) all run via `docker compose`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language / Framework | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Auth | JSON Web Tokens (`djangorestframework-simplejwt`) |
| Background jobs / scheduling | Celery + Celery Beat, broker & result backend on Redis |
| Payments | Stripe (`stripe` package, Checkout Sessions, webhooks) |
| Notifications | Telegram Bot API (`pyTelegramBotAPI`) |
| API docs | `drf-spectacular` (OpenAPI schema + Swagger UI) |
| Containerization | Docker / docker-compose |
| Linting / formatting | flake8 |
| Testing | Django `TestCase` / DRF `APITestCase`, target 60%+ coverage of custom code |

---

## App Structure

The project is split into six Django apps, each owning one part of the domain:

| App | Responsibility |
|---|---|
| `specializations` | CRUD for medical specializations |
| `doctors` | Doctor profiles and their `DoctorSlot` availability (kept in the same app to keep related migrations together) |
| `users` | Custom email-based user model, registration, JWT login/refresh, profile |
| `appointment` | Booking, cancelling, completing, and marking appointments as no-show |
| `payments` | Payment records, Stripe checkout session creation, success/cancel pages, and the Stripe webhook |
| `notifications` | No models — just Celery tasks/services for sending Telegram messages and running the daily no-show sweep |

---

## Data Models

**Specialization**
- `name` — string, unique
- `code` — slug, unique (stable identifier, e.g. `cardiology`)
- `description` — text, optional

**Doctor**
- `first_name`, `last_name` — string
- `specializations` — many-to-many to `Specialization`
- `price_per_visit` — decimal (USD)

**DoctorSlot**
- `doctor` — foreign key to `Doctor`
- `start`, `end` — datetime
- Unique constraint on `(doctor, start, end)`; `end` must be after `start`

**User (Patient)**
- `email` — unique, used as the login identifier instead of a username
- `first_name`, `last_name` — string
- `password` — hashed
- `is_staff` — bool (admin/staff flag)

**Appointment**
- `doctor_slot` — foreign key to `DoctorSlot`
- `patient` — foreign key to `User`
- `status` — `BOOKED | COMPLETED | CANCELLED | NO_SHOW`
- `booked_at` — datetime, set automatically
- `completed_at` — datetime, nullable
- `price` — decimal (USD), captured from the doctor's price **at the time of booking**, not looked up later

**Payment**
- `status` — `PENDING | PAID | EXPIRED`
- `type` — `CONSULTATION | CANCELLATION_FEE | NO_SHOW_FEE`
- `appointment` — foreign key to `Appointment`
- `session_url`, `session_id` — Stripe Checkout Session details
- `money_to_pay` — decimal (USD)

---

## Business Rules

- **Booking** — `POST /api/v1/appointments/` fails if the target slot already has a `BOOKED` appointment. The appointment's `price` is copied from `doctor.price_per_visit` at the moment of booking, so later price changes don't affect existing appointments.
- **Cancellation fee** — cancelling counts as a *late cancellation* if it happens less than 24 hours before the slot's start time. A late cancellation creates a `CANCELLATION_FEE` payment for **50%** of the appointment price; cancelling earlier than 24 hours creates no fee.
- **Consultation fee** — marking an appointment `COMPLETED` (staff only) creates a `CONSULTATION` payment for **100%** of the price.
- **No-show fee** — marking an appointment `NO_SHOW` (staff action, or automatically via the daily scheduled job) creates a `NO_SHOW_FEE` payment for **120%** of the price.
- **Status transitions are one-way** — only `BOOKED` appointments can be cancelled, completed, or marked as no-show; once an appointment is in a terminal state, those actions are rejected.
- **Pricing is calculated server-side** using `Decimal` arithmetic with standard rounding, never trusted from client input.
- **Slot deletion** is blocked if the slot already has an appointment attached to it.

---

## API Reference

All endpoints are namespaced under `/api/v1/`. Authentication uses JWT bearer tokens sent in a custom **`Authorize`** header (not the standard `Authorization` header) — see [Authentication](#authentication) below.

### Authentication

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/api/v1/users/` | No | Register a new patient account |
| POST | `/api/v1/users/token/` | No | Obtain a JWT access/refresh token pair |
| POST | `/api/v1/users/token/refresh/` | No | Refresh an expired access token |
| GET | `/api/v1/users/me/` | Yes | Get the logged-in user's profile |
| PUT/PATCH | `/api/v1/users/me/` | Yes | Update the logged-in user's profile |

> **Note:** send the token as `Authorize: Bearer <access_token>` rather than the usual `Authorization` header — this project uses a custom header name for easier manual testing with the ModHeader browser extension.

### Specializations

Public read access; only staff/admin users can create, update, or delete.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/specializations/` | List all specializations |
| POST | `/api/v1/specializations/` | Create a specialization (admin only) |
| GET | `/api/v1/specializations/<code>/` | Get specialization detail (looked up by `code`) |
| PUT/PATCH | `/api/v1/specializations/<code>/` | Update a specialization (admin only) |
| DELETE | `/api/v1/specializations/<code>/` | Delete a specialization (admin only) |

### Doctors & Slots

Public read access; only staff/admin users can create, update, or delete.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/doctors/?specialization=<id_or_code>` | List doctors, optionally filtered by specialization |
| POST | `/api/v1/doctors/` | Create a doctor (admin only) |
| GET | `/api/v1/doctors/<id>/` | Get doctor detail |
| PUT/PATCH | `/api/v1/doctors/<id>/` | Update a doctor (admin only) |
| DELETE | `/api/v1/doctors/<id>/` | Delete a doctor (admin only) |
| POST | `/api/v1/doctors/<doctor_id>/slots/` | Bulk-create slots for a doctor (admin only) — body: `start`, `end`, `interval` in minutes |
| GET | `/api/v1/doctors/<doctor_id>/slots/?from=&to=&available_only=true\|false` | List a doctor's slots, with optional date range and availability filter |
| GET | `/api/v1/slots/` | List all slots (filterable by `from`, `to`, `available_only`) |
| POST | `/api/v1/slots/` | Create a single slot (admin only) |
| GET | `/api/v1/slots/<id>/` | Get slot detail |
| PUT/PATCH | `/api/v1/slots/<id>/` | Update a slot (admin only) |
| DELETE | `/api/v1/slots/<id>/` | Delete a slot — only allowed if it has no appointments (admin only) |

### Appointments

Requires authentication. Patients can only see/act on their own appointments; staff can see and filter all of them.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/appointments/?status=&doctor_id=&patient_id=&from=&to=` | List appointments (own appointments for patients; `patient_id` filter is staff-only) |
| POST | `/api/v1/appointments/` | Book an appointment for a given `doctor_slot` (fails if the slot is already booked) |
| GET | `/api/v1/appointments/<id>/` | Get appointment detail, including its associated payments |
| POST | `/api/v1/appointments/<id>/cancel/` | Cancel a `BOOKED` appointment (creates a cancellation fee payment if cancelled within 24h) |
| POST | `/api/v1/appointments/<id>/complete/` | Mark an appointment `COMPLETED` (staff only — creates a consultation payment) |
| POST | `/api/v1/appointments/<id>/no_show/` | Mark an appointment `NO_SHOW` (staff only — creates a no-show fee payment) |

### Payments

Requires authentication. Patients see only their own payments; staff see all.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/payments/` | List payments (paginated) |
| GET | `/api/v1/payments/<id>/` | Get payment detail |
| GET | `/api/v1/payments/success/?session_id=<id>` | Stripe redirects here after checkout; confirms payment status with Stripe and marks it `PAID` |
| GET | `/api/v1/payments/cancel/?session_id=<id>` | Stripe redirects here if checkout is abandoned; tells the patient the session is still valid for 24h |
| POST | `/api/v1/webhooks/stripe/` | Stripe webhook — keeps `Payment` status in sync (`checkout.session.completed` → `PAID`, `checkout.session.expired` → `EXPIRED`) |

### Documentation Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/schema/` | Raw OpenAPI schema |
| GET | `/api/docs/swagger/` | Interactive Swagger UI |
| — | `/admin/` | Django admin site |

---

## Notifications (Telegram)

Staff are notified in a configured Telegram chat for:

- A new appointment being booked (includes patient, doctor, and time).
- Any appointment status change (cancelled, completed, no-show).
- The result of the daily no-show sweep ("Processed N no-shows" or "No missed appointments today!").
- A successful Stripe payment (via the webhook), including the appointment ID and amount paid.

Messages are sent asynchronously through a Celery task (`notifications.tasks.send_telegram_message_task`) so a slow or failing Telegram API call never blocks the API response. The task automatically retries on failure.

---

## Scheduled Tasks

A Celery Beat schedule runs once per day (`00:00 UTC`):

- **`check_and_mark_noshow_appointments_daily_task`** — finds every appointment still `BOOKED` whose slot has already ended, marks it `NO_SHOW`, and sends a Telegram summary of how many were processed.

---

## Requirements

- **Python 3.14** — download at https://www.python.org/downloads/
- **Docker Desktop** — download at https://www.docker.com/products/docker-desktop/
- **Git**

> **Don't have Python 3.14?** You can work fully inside Docker — skip to the [Full Docker Workflow](#full-docker-workflow) section.

---

## First Time Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_ORG/YOUR_REPO.git
cd YOUR_REPO
git checkout develop
```

### 2. Create your `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

- **SECRET_KEY** — generate your own at https://djecrety.ir. Doesn't need to match teammates'.
- **POSTGRES credentials** — make up any username and password. Docker creates the database using whatever you set here.
- **POSTGRES_HOST** — use `localhost` when running Django locally, use `db` in full Docker mode.
- **POSTGRES_PORT** — `5432` by default.
- **TELEGRAM_TOKEN / TELEGRAM_CHAT_ID** — your bot token and chat ID for notifications (ask the team lead if you need a shared test bot).
- **STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET** — use **test mode** keys from your Stripe dashboard. Never use real/live keys on this project.

> **Windows users:** if you have PostgreSQL installed locally it may conflict on port 5432. Check:
> ```powershell
> Get-Service -Name postgresql*
> ```
> If it shows `Running`, disable it:
> ```powershell
> Set-Service -Name "postgresql-x64-17" -StartupType Disabled
> Stop-Service -Name "postgresql-x64-17"
> ```
> Adjust the version number to match what you see.

### 3. Open Docker Desktop

Make sure it is fully running before continuing.

### 4. Create a virtual environment

```bash
python -m venv venv

# Activate:
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 5. Install and run

```bash
pip install -r requirements.txt

# Terminal 1 — start the database
docker compose up db

# Terminal 2 — run Django
python manage.py migrate
python manage.py runserver
```

Open **http://localhost:8000/**

> Every day after setup: `docker compose up db` in terminal 1, `python manage.py runserver` in terminal 2.

---

## Full Docker Workflow

Use this if you don't have Python 3.14 installed, or just want everything running in Docker — including the API server, Celery worker, Celery Beat scheduler, the Flower task-monitoring dashboard, and the Stripe CLI (which forwards Stripe webhook events to your local server for testing).

In `.env` set:
```env
POSTGRES_HOST=db
```

Then:
```bash
docker compose up --build
```

This brings up:

| Service | Purpose | URL |
|---|---|---|
| `web` | Django API server | http://localhost:8000/ |
| `db` | PostgreSQL database | internal |
| `redis` | Celery broker/result backend | internal |
| `celery` | Celery worker (runs notification & payment tasks) | — |
| `celery-beat` | Celery scheduler (runs the daily no-show job) | — |
| `dashboard` | Flower — monitor Celery tasks | http://localhost:5555/ |
| `stripe-cli` | Forwards Stripe test webhooks to `web` | — |

Django reloads automatically when you save code files (the volume is mounted).
To run management commands, use `docker compose exec`:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py startapp appname
docker compose exec web python manage.py createsuperuser
```

---

## Creating a New App (local mode)

```bash
python manage.py startapp appname
```

Add it to `INSTALLED_APPS` in `config/settings.py`, then write your models, views, and serializers.

---

## Installing Packages

```bash
pip install package-name
pip freeze > requirements.txt
```

Commit both your code and the updated `requirements.txt`.

> ⚠️ After `pip freeze`, check `requirements.txt` contains `psycopg2-binary` and **not** plain `psycopg2`. If you see both, delete the `psycopg2` line and keep only `psycopg2-binary`. Plain `psycopg2` needs to compile from source and breaks the Docker build.

---

## Common Commands

| What | Local mode | Full Docker mode |
|------|-----------|-----------------|
| Run server | `python manage.py runserver` | `docker compose up --build` |
| Migrate | `python manage.py migrate` | `docker compose exec web python manage.py migrate` |
| Make migrations | `python manage.py makemigrations` | `docker compose exec web python manage.py makemigrations` |
| Create app | `python manage.py startapp name` | `docker compose exec web python manage.py startapp name` |
| Create superuser | `python manage.py createsuperuser` | `docker compose exec web python manage.py createsuperuser` |
| Run tests | `python manage.py test` | `docker compose exec web python manage.py test` |
| Start DB only | `docker compose up db` | — |
| Stop Docker | `docker compose down` | `docker compose down` |
| Wipe database | `docker compose down -v` | `docker compose down -v` |

---

## Testing

- All custom functionality must have test coverage of **60%+** (payments and Telegram notifications are mocked, since they're harder to test end-to-end — see `unittest.mock.patch` usage in the existing test files for examples).
- Run the suite with `python manage.py test` (or the Docker equivalent above).
- API documentation is auto-generated by `drf-spectacular` and available at `/api/docs/swagger/` — keep custom actions (`cancel`, `complete`, `no_show`, bulk slot creation, Stripe success/cancel) documented with `@extend_schema` so the Swagger docs stay accurate.

---

## Git Workflow

Every task gets its own branch. Always branch from `develop`, always PR back to `develop`.

```bash
# Start a task
git checkout develop
git pull origin develop
git checkout -b feature/your-task-name

# Finish a task
git add .
git commit -m "feat: what you did"
git push -u origin feature/your-task-name
# open a Pull Request on GitHub → into develop
```

**Branch structure:**
```
main        ← never touch during the sprint
└── develop ← all PRs go here
    ├── feature/users-model
    ├── feature/doctors-slots
    └── feature/appointments-crud
```

**PR rules:** every PR needs 2 approvals before merging.

**If develop moved ahead of your branch:**
```bash
git checkout develop && git pull origin develop
git checkout feature/your-task-name
git rebase develop
git push --force-with-lease origin feature/your-task-name
```

---

## Commit Message Format

```
feat: add Doctor model
fix: slot overlap validation
chore: update requirements.txt
test: add tests for appointments
docs: update README
```