@echo off
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"
set "PYTHONPATH=%ROOT_DIR%src"

echo 1. Verify uv 0.10.0 from PATH
where uv >nul 2>nul
if errorlevel 1 (
    echo 未找到 uv。请从官方渠道安装 uv 0.10.0 并加入 PATH。
    exit /b 1
)
for /f "delims=" %%V in ('uv --version') do set "UV_VERSION=%%V"
if /i not "!UV_VERSION!"=="uv 0.10.0" (
    echo uv 版本不受支持：!UV_VERSION!；要求 uv 0.10.0。
    exit /b 1
)

echo 2. Install locked Python environment
set "UV_PYTHON_DOWNLOADS=never"
uv python find 3.11 >nul 2>nul
if errorlevel 1 (
    echo 未找到 Python 3.11。请先安装受信任的 Python 3.11。
    exit /b 1
)
uv venv --python=3.11 .venv
if errorlevel 1 exit /b %errorlevel%
uv sync --locked
if errorlevel 1 exit /b %errorlevel%

echo 3. Prepare config file
if not exist "%ROOT_DIR%src\tradingview_zy\config.py" (
    copy "%ROOT_DIR%src\tradingview_zy\config.py.demo" "%ROOT_DIR%src\tradingview_zy\config.py" >nul
)

echo 4. Run environment check
uv run "%ROOT_DIR%check_env.py"
exit /b %errorlevel%
