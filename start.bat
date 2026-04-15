@echo off
setlocal enabledelayedexpansion

title Lighthouse Agent

echo.
echo  =========================================
echo   Lighthouse Agent - Starting up...
echo  =========================================
echo.

:: ── 1. Check Node.js ──────────────────────────────────────────────────────────
where node >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js is not installed.
    echo.
    echo  Please download and install it from: https://nodejs.org/
    echo  Then re-run this script.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node -v') do set NODE_VER=%%v
echo  [OK] Node.js found: %NODE_VER%

:: ── 2. Check Lighthouse CLI ───────────────────────────────────────────────────
where lighthouse >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [SETUP] Lighthouse CLI not found. Installing now...
    npm install -g lighthouse
    if errorlevel 1 (
        echo  [ERROR] Failed to install Lighthouse. Check your npm/Node setup.
        pause
        exit /b 1
    )
    echo  [OK] Lighthouse installed.
) else (
    for /f "tokens=*" %%v in ('lighthouse --version 2^>nul') do set LH_VER=%%v
    echo  [OK] Lighthouse found: %LH_VER%
)

:: ── 3. Check Python ───────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python is not installed or not on PATH.
    echo  Please install Python 3.10+ from https://python.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do set PY_VER=%%v
echo  [OK] Python found: %PY_VER%

:: ── 4. Create virtual environment if missing ─────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo  [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created.
)

:: ── 5. Activate venv ─────────────────────────────────────────────────────────
call venv\Scripts\activate.bat
echo  [OK] Virtual environment activated.

:: ── 6. Install / sync dependencies ───────────────────────────────────────────
echo.
echo  [SETUP] Installing Python dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] pip install failed. Check requirements.txt.
    pause
    exit /b 1
)
echo  [OK] Dependencies ready.

:: ── 7. Start MCP server in the background ────────────────────────────────────
echo.
echo  [SETUP] Starting MCP server in background...
start /B cmd /c "call venv\Scripts\activate.bat && python app.py > server.log 2>&1"

:: ── 8. Wait for server to boot ───────────────────────────────────────────────
echo  [SETUP] Waiting for server to start...
timeout /t 4 /nobreak >nul

:: ── 9. Verify server actually came up ────────────────────────────────────────
curl -s http://localhost:8000/meta >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Server did not start. Check server.log for details.
    pause
    exit /b 1
)
echo  [OK] MCP server running on http://localhost:8000

:: ── 10. Open VS Code ──────────────────────────────────────────────────────────
echo  [OK] Opening VS Code...
code .

echo.
echo  =========================================
echo   All done! VS Code is opening.
echo   MCP server is running in background.
echo   Server logs: server.log
echo   Close this window to stop the server.
echo  =========================================
echo.
pause