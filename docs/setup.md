# Windows Setup Guide

**Local setup and run guide.** Step-by-step instructions for running MoodFlix on Windows: prerequisites, environment variables, and how to run the backend and frontend.

## Why Python 3.12?

Python 3.13 introduced changes that cause compatibility issues with SQLAlchemy 2.0.25. Using Python 3.12 ensures a stable, beginner-friendly development experience.

**Alternative (Advanced):** If you prefer Python 3.13, you can upgrade SQLAlchemy to version 2.0.36+ which includes Python 3.13 compatibility fixes. Update `requirements.txt`:
```
sqlalchemy>=2.0.36
```
Then run `pip install --upgrade -r requirements.txt`. However, **Python 3.12 is recommended for beginners** as it's more stable and widely tested with the current dependency versions.

---

## Step 1: Install Python 3.12

### Option A: Using Python.org Installer

1. Download Python 3.12.x from [python.org/downloads](https://www.python.org/downloads/)
   - Choose the latest 3.12.x version (e.g., 3.12.7)
   - Download the Windows installer (64-bit recommended)

2. Run the installer:
   - ✅ **Important:** Check "Add Python to PATH" during installation
   - Choose "Install Now" or "Customize installation"
   - Complete the installation

3. Verify installation:
   ```powershell
   python --version
   # Should show: Python 3.12.x
   ```

### Option B: Using pyenv-win (Advanced)

If you need to manage multiple Python versions:

```powershell
# Install pyenv-win (see: https://github.com/pyenv-win/pyenv-win)
# Then install Python 3.12:
pyenv install 3.12.7
pyenv local 3.12.7
```

---

## Step 2: Create Virtual Environment

### Windows PowerShell

```powershell
# Navigate to project directory
cd C:\Users\Owner\Desktop\Github-Projects\MoodFlix

# Create virtual environment using Python 3.12
python3.12 -m venv venv

# If python3.12 doesn't work, try:
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again
```

### Windows Git Bash

```bash
# Navigate to project directory
cd /c/Users/Owner/Desktop/Github-Projects/MoodFlix

# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/Scripts/activate
```

### Command Prompt (cmd)

```cmd
# Navigate to project directory
cd C:\Users\Owner\Desktop\Github-Projects\MoodFlix

# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat
```

**Note:** You should see `(venv)` in your terminal prompt when the virtual environment is active.

---

## Step 2.5: Install PostgreSQL on Windows

If `Get-Service *postgres*` returns nothing, PostgreSQL is not installed. Use the steps below so MoodFlix can connect to a local database.

### 1. Download the installer

1. Go to **EnterpriseDB PostgreSQL downloads**: [https://www.enterprisedb.com/downloads/postgres-postgresql-downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. Under **Windows**, select the latest stable version (e.g. **PostgreSQL 16** or **17**).
3. Download the **Windows x86-64** installer.

### 2. Run the installer

1. Run the downloaded `.exe` as Administrator if prompted.
2. **Installation directory:** Keep the default (e.g. `C:\Program Files\PostgreSQL\16`).
3. **Select components:** Keep **PostgreSQL Server**, **pgAdmin 4**, and **Command Line Tools** checked.
4. **Data directory:** Keep the default.
5. **Password:** Set a password for the `postgres` superuser.
   - **Recommended for MoodFlix:** Use `postgres` so it matches `.env.example` and you can copy `.env.example` to `.env` without changing the password.
   - If you use a different password, you must set `POSTGRES_PASSWORD` in your `.env` to that value.
6. **Port:** Keep **5432** (MoodFlix expects this by default).
7. **Locale:** Keep the default.
8. Finish the installer and exit Stack Builder if it opens.

### 3. Create the `moodflix` database

The installer creates only the default `postgres` database. Create the database MoodFlix uses:

**Option A – Command line (recommended)**

Open a new PowerShell or Command Prompt and run (replace `16` with your PostgreSQL version if different):

```powershell
# Add PostgreSQL bin to PATH for this session (adjust version if needed)
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
# Create the database (you'll be prompted for the postgres password)
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE moodflix;"
```

**Option B – SQL file**

From the project root, after adding `C:\Program Files\PostgreSQL\16\bin` to your PATH:

```powershell
psql -U postgres -h 127.0.0.1 -f scripts/create_moodflix_db.sql
```

**Option C – pgAdmin**

1. Open pgAdmin 4, connect to the local server (password = what you set for `postgres`).
2. Right-click **Databases** → **Create** → **Database**.
3. Name: `moodflix`, then Save.

### 4. Verify the service

```powershell
Get-Service *postgres*
# Start if needed (use the exact name shown, e.g. postgresql-x64-16):
Start-Service -Name "postgresql-x64-16"
.\scripts\check_postgres.ps1
```

### 5. Create MoodFlix tables (migrations)

With your virtual environment activated and `.env` configured, run from the project root:

```powershell
alembic upgrade head
```

This creates the `users`, `shows`, `watchlist_items` tables and any other schema the app needs.

---

## Step 3: Install Dependencies

With your virtual environment activated:

```powershell
# Upgrade pip (recommended)
python -m pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

---

## Step 4: Configure Environment Variables

1. Copy the example environment file:
   ```powershell
   # PowerShell
   Copy-Item .env.example .env
   
   # Git Bash / cmd
   copy .env.example .env
   ```

2. Edit `.env` and set values that match your local PostgreSQL installation:

   | Variable | What to set | Notes |
   |----------|-------------|--------|
   | `POSTGRES_USER` | `postgres` | Default superuser from the installer. |
   | `POSTGRES_PASSWORD` | The password you set for `postgres` during installation | If you used `postgres` as recommended in Step 2.5, keep `.env.example` value. |
   | `POSTGRES_DB` | `moodflix` | Must match the database you created in Step 2.5. |
   | `POSTGRES_HOST` | `127.0.0.1` or `localhost` | Local install. |
   | `POSTGRES_PORT` | `5432` | Default; change only if you chose another port. |

   **No change to `app/db.py` is required.** It already reads these variables and defaults to `127.0.0.1:5432` with user `postgres`, database `moodflix` when running locally. If you leave `POSTGRES_*` unset and use a local host, `app/db.py` uses empty password by default; if you set a password during install (recommended), you must set `POSTGRES_PASSWORD` in `.env`.

3. Other options in `.env`:
   - Add your TMDB API key if you use TMDB features.
   - See `.env.example` for all available options.

---

## Step 4.5: Verify PostgreSQL (optional but recommended)

Before starting the backend, ensure PostgreSQL is running so registration and auth work.

**Quick check (PowerShell):**

```powershell
# Option A: Test if port 5432 is open
Test-NetConnection -ComputerName 127.0.0.1 -Port 5432
# TcpTestSucceeded : True  means PostgreSQL is reachable.

# Option B: Run the project script (from repo root)
.\scripts\check_postgres.ps1
```

**If PostgreSQL is not running (Windows):**

- Start the service (service name may be `postgresql-x64-16` or similar):
  ```powershell
  Get-Service -Name "*postgres*"
  Start-Service -Name "postgresql-x64-16"   # use the name from the list
  ```
- Or start it from PostgreSQL’s `bin` folder: `pg_ctl -D "C:\Program Files\PostgreSQL\16\data" start`

---

## Step 5: Start the Application

### Start Backend Server

With virtual environment activated:

```powershell
uvicorn app.api:app --reload
```

The API will be available at:
- **API:** http://127.0.0.1:8000
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

### Start Frontend (Separate Terminal)

Open a new terminal window:

```powershell
cd frontend
npm install  # First time only
npm run dev
```

The frontend will be available at http://localhost:5173

---

## Troubleshooting

### "python3.12: command not found"

- Make sure Python 3.12 is installed and added to PATH
- Try using `python` instead of `python3.12`
- Verify installation: `python --version`

### "Execution Policy" Error in PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Database connection error (psycopg.OperationalError on port 5432)

If registration or login fails with a database connection error:

1. **Check that PostgreSQL is running:** Run `.\scripts\check_postgres.ps1` or `Test-NetConnection -ComputerName 127.0.0.1 -Port 5432`.
2. **Start PostgreSQL** (see [Step 4.5: Verify PostgreSQL](#step-45-verify-postgresql-optional-but-recommended)).
3. **Check `.env`:** Use `DATABASE_URL` or `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. For local dev, host defaults to `127.0.0.1` and port to `5432`.

### SQLAlchemy Import Error

If you see `AssertionError: Class SQLCoreOperations directly inherits TypingOnly...`:

- **Solution 1 (Recommended):** Use Python 3.12.x
- **Solution 2:** Upgrade SQLAlchemy to 2.0.36+:
  ```powershell
  pip install --upgrade "sqlalchemy>=2.0.36"
  ```

### Virtual Environment Not Activating

- Make sure you're in the project root directory
- Check that `venv` folder exists
- Try recreating the virtual environment:
  ```powershell
  Remove-Item -Recurse -Force venv
  python3.12 -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

---

## Quick Reference Commands

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Deactivate virtual environment
deactivate

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn app.api:app --reload

# Run tests
pytest

# Run tests with verbose output
pytest -v
```

---

## Next Steps

- See [README.md](../README.md) for full project documentation
- Check [Environment Configuration](../README.md#environment-configuration) for `.env` setup
- Review [Testing Strategy](../README.md#testing-strategy) for running tests
