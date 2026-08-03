@echo off
setlocal enabledelayedexpansion

REM Set repository root to this script directory
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ROOT_DIR: %ROOT_DIR%

echo 1. Locate uv
set "UV_DIR=%ROOT_DIR%script\bin\uv.exe"
echo UV_DIR: %UV_DIR%

echo 2. Install Python environment
%UV_DIR% python install 3.11
%UV_DIR% venv --python=3.11 .venv
%UV_DIR% sync

echo 3. Prepare config file
if not exist "%ROOT_DIR%src\tradingview_zy\config.py" (
    echo Copying config template...
    copy "%ROOT_DIR%src\tradingview_zy\config.py.demo" "%ROOT_DIR%src\tradingview_zy\config.py" >nul
)

echo 4. Set PYTHONPATH
set "PYTHONPATH=%ROOT_DIR%src"
echo PYTHONPATH: !PYTHONPATH!

echo 5. Run environment check
if exist "%ROOT_DIR%check_env.py" (
    %UV_DIR% run "%ROOT_DIR%check_env.py"
)

echo Done.
pause
