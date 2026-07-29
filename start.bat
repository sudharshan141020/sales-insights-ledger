@echo off
setlocal
cd /d "%~dp0"

if not exist venv (
    echo Setting up for the first time - this only happens once...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

python run.py

pause
