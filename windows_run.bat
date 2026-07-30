@echo off
chcp 65001 >nul
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "UV_DIR=%ROOT_DIR%script\bin\uv.exe"
set "PYTHONPATH=%ROOT_DIR%src"
set "APP_PATH=%ROOT_DIR%web\tradingview_zy_chart\app.py"

if not exist "%UV_DIR%" (
    echo 未找到 uv：%UV_DIR%
    pause
    exit /b 1
)

if not exist "%APP_PATH%" (
    echo 未找到 WEB 应用：%APP_PATH%
    pause
    exit /b 1
)

echo 启动 tradingview_zy WEB 服务...
"%UV_DIR%" run "%APP_PATH%"

if errorlevel 1 (
    echo.
    echo WEB 服务异常退出，错误码 %errorlevel%，请查看上方报错信息。
    pause
    exit /b %errorlevel%
)
