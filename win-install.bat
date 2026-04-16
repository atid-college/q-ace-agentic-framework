@echo off
setlocal

echo Starting Q-ACE Framework Setup...

:: --- 1. Main Application Environment (venv) ---
if exist "venv\Scripts\activate.bat" goto :activate_venv
echo Creating main virtual environment (venv)...
python -m venv venv

:activate_venv
echo Activating main environment...
call venv\Scripts\activate

echo Installing main dependencies...
pip install -r requirements.txt

echo Initializing Authentication Database...
python init_auth_db.py
call venv\Scripts\deactivate

:: --- 2. Browser Agent Environment (.venv) ---
echo Checking for uv (required for Browser Agent)...
uv --version >nul 2>&1
if %ERRORLEVEL% equ 0 goto :uv_exists
echo uv not found. Installing uv...
pip install uv

:uv_exists
if exist ".venv" goto :install_browser_agent
echo Creating specialized Browser Agent environment (.venv)...
uv venv

:install_browser_agent
echo Installing Browser Agent dependencies into .venv...
call .venv\Scripts\activate
uv pip install browser-use
uvx browser-use install
call .venv\Scripts\deactivate

:: --- 3. Success Message & Launch ---
echo Re-activating main environment for server launch...
call venv\Scripts\activate

echo.
echo ###########################################################
echo #                                                         #
echo #           SUCCESS: Q-ACE Setup Completed!               #
echo #                                                         #
echo ###########################################################
echo.
echo  The application is now UP AND RUNNING.
echo.
echo  1. Open your browser at: http://localhost:8090
echo  2. Login with the default credentials:
echo.
echo     Username: admin
echo     Password: admin123
echo.
echo ###########################################################
echo.

:: Launching the server
uvicorn main:app --host 0.0.0.0 --port 8090 --reload

pause