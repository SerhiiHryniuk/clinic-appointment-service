# Clinic Appointment Service

A REST API for managing clinic appointments, doctors, patients, and payments.

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

- **SECRET_KEY** — generate your own at https://djecrety.ir. Doesn't need to match teammates.
- **POSTGRES credentials** — make up any username and password. Docker creates the database using whatever you set here.
- **POSTGRES_HOST** — use `localhost` when running Django locally, use `db` in full Docker mode.
- **POSTGRES_PORT** — `5432` by default.

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

Use this if you don't have Python 3.14 installed, or just want everything running in Docker.

In `.env` set:
```env
POSTGRES_HOST=db
```

Then:
```bash
docker compose up --build
```

Open **http://localhost:8000/**

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