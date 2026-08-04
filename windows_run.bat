@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"
set "PYTHONPATH=%ROOT_DIR%src"
set "APP_PATH=%ROOT_DIR%web\tradingview_zy_chart\app.py"

where uv >nul 2>nul
if errorlevel 1 (
    echo 未找到 uv。请安装 uv 0.10.0 并加入 PATH。
    exit /b 1
)
for /f "delims=" %%V in ('uv --version') do set "UV_VERSION=%%V"
if /i not "!UV_VERSION!"=="uv 0.10.0" (
    echo uv 版本不受支持：!UV_VERSION!；要求 uv 0.10.0。
    exit /b 1
)
if not exist "%APP_PATH%" (
    echo 未找到 WEB 应用：%APP_PATH%
    exit /b 1
)

set "UV_PYTHON_DOWNLOADS=never"
echo 启动 tradingview_zy WEB 服务...
uv run "%APP_PATH%"
exit /b %errorlevel%
