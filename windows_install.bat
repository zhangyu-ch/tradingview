@echo off
setlocal enabledelayedexpansion

REM ȡűĿ¼ĿĿ¼
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM ROOT_DIR ֵ
echo ROOT_DIR: %ROOT_DIR%

echo 1. uv Ŀ¼
set "UV_DIR=%ROOT_DIR%script\bin\uv.exe"
echo UV_DIR: %UV_DIR%

echo 2. ⻷
%UV_DIR% python install 3.11
%UV_DIR% venv --python=3.11 .venv
%UV_DIR% sync

echo 3. ļ
if not exist "%ROOT_DIR%src	radingview_zy\config.py" (
    echo ļ...
    copy "%ROOT_DIR%src	radingview_zy\config.py.demo" "%ROOT_DIR%src	radingview_zy\config.py" >nul
)

echo 4. û
set "PYTHONPATH=%ROOT_DIR%src"
echo PYTHONPATH: !PYTHONPATH!

echo 5. лű
if exist "%ROOT_DIR%check_env.py" (
    %UV_DIR% run "%ROOT_DIR%check_env.py"
)

echo ɣ
pause
