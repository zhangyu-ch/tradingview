@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 获取脚本所在目录作为项目根目录
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM ROOT_DIR 的值
echo ROOT_DIR: %ROOT_DIR%

echo uv 路径
set "UV_DIR=%ROOT_DIR%script\bin\uv.exe"
echo UV_DIR: %UV_DIR%

if not exist "%ROOT_DIR%src\pyarmor_runtime_005445\pyarmor.rkey" (
    echo.
    echo 未找到授权文件：%ROOT_DIR%src\pyarmor_runtime_005445\pyarmor.rkey
    echo 将以降级模式启动，仅提供普通 K 线；缠论核心计算与叠加标记不可用。
    echo.
)

echo 设置 PYTHONPATH
set "PYTHONPATH=%ROOT_DIR%src"
echo 当前 PYTHONPATH: !PYTHONPATH!

echo 启动 WEB 服务
if exist "%ROOT_DIR%web/tradingview_zy_chart/app.py" (
    %UV_DIR% run "%ROOT_DIR%web/tradingview_zy_chart/app.py"
)
