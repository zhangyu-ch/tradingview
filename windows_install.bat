@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"
set "PYTHONPATH=%ROOT_DIR%src"
set "EXIT_CODE=0"

echo 1. Verify uv 0.10.0 from PATH
where uv >nul 2>nul
if errorlevel 1 (
    echo 未找到 uv。请从官方渠道安装 uv 0.10.0 并加入 PATH。
    set "EXIT_CODE=1"
    goto :fail
)
set "UV_NAME="
set "UV_VERSION="
set "UV_VERSION_OUTPUT="
for /f "tokens=1,2,*" %%A in ('uv --version 2^>nul') do (
    set "UV_NAME=%%A"
    set "UV_VERSION=%%B"
    set "UV_VERSION_OUTPUT=%%A %%B %%C"
)
if /i not "!UV_NAME! !UV_VERSION!"=="uv 0.10.0" (
    echo uv 版本不受支持：!UV_VERSION_OUTPUT!；要求 uv 0.10.0。
    echo 请执行：uv self update 0.10.0
    set "EXIT_CODE=1"
    goto :fail
)

echo 2. Install locked Python environment
set "UV_PYTHON_DOWNLOADS=never"
call uv python find 3.11 >nul 2>nul
if errorlevel 1 (
    echo 未找到 Python 3.11。请先安装受信任的 Python 3.11。
    set "EXIT_CODE=1"
    goto :fail
)
set "VENV_PYTHON=%ROOT_DIR%.venv\Scripts\python.exe"
set "CREATE_VENV=0"
set "VENV_OPTIONS="
if not exist "!VENV_PYTHON!" (
    set "CREATE_VENV=1"
) else (
    "!VENV_PYTHON!" -c "import sys; raise SystemExit(not sys.version_info.major == 3 or not sys.version_info.minor == 11)" >nul 2>nul
    if errorlevel 1 (
        echo 现有虚拟环境不是 Python 3.11，将重新创建。
        set "CREATE_VENV=1"
        set "VENV_OPTIONS=--clear"
    ) else (
        echo Reusing existing Python 3.11 virtual environment
    )
)
if "!CREATE_VENV!"=="1" (
    call uv venv !VENV_OPTIONS! --python=3.11 .venv
    if errorlevel 1 (
        set "EXIT_CODE=!errorlevel!"
        echo 创建 Python 虚拟环境失败，错误码 !EXIT_CODE!。
        goto :fail
    )
)
call uv sync --locked
if errorlevel 1 (
    set "EXIT_CODE=!errorlevel!"
    echo 安装锁定依赖失败，错误码 !EXIT_CODE!。
    goto :fail
)

echo 3. Prepare config file
if not exist "%ROOT_DIR%src\tradingview_zy\config.py" (
    copy "%ROOT_DIR%src\tradingview_zy\config.py.demo" "%ROOT_DIR%src\tradingview_zy\config.py" >nul
    if errorlevel 1 (
        set "EXIT_CODE=!errorlevel!"
        echo 创建配置文件失败，错误码 !EXIT_CODE!。
        goto :fail
    )
)

echo 4. Run environment check
call uv run python "%ROOT_DIR%check_env.py"
set "EXIT_CODE=!errorlevel!"
if not "!EXIT_CODE!"=="0" (
    echo 环境检查失败，错误码 !EXIT_CODE!。
    goto :fail
)
exit /b 0

:fail
echo.
if not defined TRADINGVIEW_ZY_NO_PAUSE pause
exit /b !EXIT_CODE!
