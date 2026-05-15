@echo off
chcp 65001 >nul 2>&1
title 小学出题工具箱
cd /d "%~dp0"
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序异常退出，请检查 Python 环境是否正常。
    pause
)
