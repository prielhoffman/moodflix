# Windows Setup Guide

This guide provides step-by-step instructions for setting up MoodFlix on Windows using Python 3.12.

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

2. Edit `.env` file and add your configuration:
   - Add your TMDB API key
   - Configure database settings if needed
   - See `.env.example` for all available options

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
