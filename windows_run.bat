@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"
set "PYTHONPATH=%ROOT_DIR%src"
set "APP_PATH=%ROOT_DIR%web\tradingview_zy_chart\app.py"
set "EXIT_CODE=0"

where uv >nul 2>nul
if errorlevel 1 (
    echo 未找到 uv。请安装 uv 0.10.0 并加入 PATH。
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
set "UV_ALLOWED="
if /i "!UV_NAME!"=="uv" (
    if "!UV_VERSION:~0,4!"=="0.10" set "UV_ALLOWED=1"
    if "!UV_VERSION:~0,4!"=="0.11" set "UV_ALLOWED=1"
)
if not defined UV_ALLOWED (
    echo uv 版本不受支持：!UV_VERSION_OUTPUT!；要求 uv 0.10 或 0.11。
    echo 请执行：uv self update 0.11
    set "EXIT_CODE=1"
    goto :fail
)
if not exist "%APP_PATH%" (
    echo 未找到 WEB 应用：%APP_PATH%
    set "EXIT_CODE=1"
    goto :fail
)

set "UV_PYTHON_DOWNLOADS=never"
echo 启动 tradingview_zy WEB 服务...
call uv run python "%APP_PATH%"
set "EXIT_CODE=!errorlevel!"
if not "!EXIT_CODE!"=="0" (
    echo.
    echo WEB 服务异常退出，错误码 !EXIT_CODE!，请查看上方报错信息。
    goto :fail
)
exit /b 0

:fail
echo.
if not defined TRADINGVIEW_ZY_NO_PAUSE pause
exit /b !EXIT_CODE!
